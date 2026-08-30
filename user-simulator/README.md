# Conversational Shopping User Simulator

A reproducible shopping-user simulator for conversational shopping agents.

The core design separates **behavior** from **language generation**:

```text
User goal + persona + policy -> structured dialogue act -> verbalizer -> natural user utterance
```

The LLM is used only as an optional verbalizer. It does not decide goals, state transitions, acceptance, overrides, or constraint relaxation.

## v0.3 features

- `TargetProductGoal` and `NeedBasedGoal`
- Persona templates
- Deterministic user policy with seeded randomness
- Structured dialogue acts
- Template verbalizer for reproducible benchmarks
- OpenAI-compatible verbalizer with template fallback
- Python agent adapter compatible with the TechJam `reset/respond` contract
- TechJam catalog/session adapter
- Amazon Reviews 2023 metadata adapter
- Amazon Shopping Queries / ESCI adapter
- Exact-target and need-based acceptance checkers
- Scheduled and persona-driven override
- Constraint relaxation primitives
- CLI and pytest test suite
- One-command `techjam` and `realistic` presets
- TechJam scenario/profile preservation and official-style scoring
- Catalog-only realistic need-goal generation with no additional dataset required
- Unified evaluation reports with `evaluation`, `turn_metrics`, `latency`,
  `model_usage`, and `mode_specific_metrics` sections

Full specification: [`docs/TECHNICAL_SPEC_v0.1.md`](docs/TECHNICAL_SPEC_v0.1.md)

## Shared uv environment

The repository keeps the Agent environment as the single working environment.
From the repository root, uv installs this simulator as an editable package into
that environment. It therefore does not create a second `user-simulator/.venv`:

```powershell
uv run --project techjam-conversational-search `
  --with-editable user-simulator --group dev `
  pytest user-simulator/tests -q
```

uv also reuses its global package cache, so recreating an environment normally
does not download unchanged packages again.

## Isolated evaluation modes

The same Agent can be evaluated under isolated protocols:

| Preset | Sessions | User policy | Acceptance | Metrics |
|---|---|---|---|---|
| `techjam` | Official public/private session records | Buying, Browsing, Intent Override, Boundary | Exact `parent_asin`, with override gating | Hit Rate@10, MRR, MTTC, Efficiency, technical score, per-scenario metrics |
| `techjam_compatible_*` | Catalog-derived non-official session cards | Buying, Browsing, Intent Override, Boundary | Exact `parent_asin`, with override gating | Official-style formulas with `official_metric_contract=false` |
| `realistic` | Deterministic goals generated from catalog metadata | Persona-driven disclosure, clarification, and override | All hard constraints plus configured soft matches | Need-based success, MRR, turns, hard/soft satisfaction |

Switch modes with one flag. Both presets use the same catalog by default, so
realistic mode does not require an extra dataset:

```bash
user-simulator run --preset techjam
user-simulator run --preset realistic
user-simulator run --preset techjam_compatible_resampled_50k
user-simulator run --preset techjam_compatible_scale_200k
user-simulator run --preset techjam_compatible_scale_500k
```

The three compatible scale presets use the same reconstructed core set of 1,000
sessions across nested catalogs. They never reuse the official 200 conversations
or official targets. Development, challenge, smoke, index, and provenance files
are under `data/derived/techjam_compatible_scale_v1/sessions/`.

Without `--output`, results are kept separately as `runs/techjam.json` and
`runs/realistic.json`.

The built-in paths are `data/raw/techjam/catalog.jsonl` and
`data/raw/techjam/public_set.jsonl`. They can be overridden without editing a
configuration file:

```bash
user-simulator run \
  --preset techjam \
  --catalog-path /path/to/catalog.jsonl \
  --sessions-path /path/to/public_set.jsonl \
  --agent-class shopping_agent.agent:ShoppingAgent \
  --output runs/techjam.json \
  --report-output runs/techjam.md

user-simulator run \
  --preset realistic \
  --catalog-path /path/to/catalog.jsonl \
  --agent-class shopping_agent.agent:ShoppingAgent \
  --output runs/realistic.json \
  --report-output runs/realistic.md
```

Equivalent editable YAML configurations are provided in
`configs/techjam_benchmark.yaml` and `configs/realistic.yaml`.

### Optional DeepSeek verbalizer

TechJam mode always keeps deterministic user wording. Realistic mode can use
DeepSeek only for surface-language generation while the structured goal,
dialogue act, state transition, and acceptance decision remain deterministic:

```powershell
$env:DEEPSEEK_API_KEY = "<set locally; do not commit>"
$env:DEEPSEEK_BASE_URL = "https://api.deepseek.com"
$env:DEEPSEEK_MODEL = "deepseek-v4-flash"

user-simulator run --preset realistic --verbalizer deepseek --limit 1
```

The DeepSeek adapter uses `/chat/completions`, disables thinking for this short
wording task, caps output at 120 tokens, records token usage and fallback counts,
and falls back to the deterministic template on provider errors. The same values
may be supplied through the generic `LLM_API_KEY`, `LLM_BASE_URL`, and
`LLM_MODEL` aliases.

TechJam hidden targets, intent cards, and undisclosed constraints remain inside
the simulator. Only the allowed aggregate profile, visible user utterance, turn,
and `top_k` are passed to the Agent. Results from the two protocols are labeled
with their mode and are never aggregated together.

## TechJam data setup

Place the TechJam participant data locally:

```text
data/raw/techjam/catalog.jsonl
data/raw/techjam/public_set.jsonl
```

The large/raw datasets are intentionally excluded from Git.

If the shopping Agent package is importable as
`shopping_agent.agent:ShoppingAgent`:

```bash
user-simulator validate --preset techjam
user-simulator run --preset techjam --limit 10
```

## Library example

```python
from user_simulator import (
    Constraint,
    Product,
    PythonAgentAdapter,
    ScenarioSpec,
    Simulator,
    TargetProductGoal,
)

catalog = {
    "A": Product("A", "Black Running Shoe", attributes={"color": ["black"]})
}

goal = TargetProductGoal(
    goal_id="example",
    target_product_id="A",
    category="running shoes",
    constraints=[Constraint("color", ["black"], "soft")],
)

scenario = ScenarioSpec(
    scenario_id="example",
    goal=goal,
    persona_template="decisive_buyer",
    seed=42,
)

simulator = Simulator(catalog, PythonAgentAdapter(my_agent))
result = simulator.run_scenario(scenario)
```

## Data policy

Adapters expect locally downloaded/prepared source files. Large Amazon/TechJam raw data is not committed to this repository. See the technical specification for dataset responsibilities and semantics.

## Unified report schema

Every aggregate JSON output uses the same top-level structure:

```text
schema_version
mode
evaluation
turn_metrics
latency
model_usage
mode_specific_metrics
sessions
```

`evaluation` contains the applicable headline metrics. In TechJam mode these
are the official Hit Rate@10, MRR, MTTC, Efficiency, and recommended technical
score. `turn_metrics` separates actual executed turns from MTTC's official
miss-at-turn-11 convention. `latency` reports Agent, user-generation, and
session-wall distributions. `model_usage` records provider/model status,
reported tokens, API-call availability, fallbacks/errors, and cost status.
Unknown prices or unreported API calls remain explicit `null` values rather
than estimates. Mode-only metrics live under `mode_specific_metrics`.

Pass `--report-output` to create a Markdown report with the same five sections.

## Current implementation status

v0.3 implements the dual-mode runtime, deterministic TechJam compatibility
policy, official-style TechJam metrics, catalog-only realistic scenario builder,
mode-specific results, CLI presets, and regression tests. Richer realistic goal
calibration, separate private/public trace files, and optional external-dataset
preparation remain follow-up work.
