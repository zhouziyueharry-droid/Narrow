# Conversational Shopping User Simulator — Technical Specification v0.1

Status: Draft for implementation

Repository: `8309/user-simulator`

Language: English only in v0.1

Primary goals:

1. Produce a reproducible benchmark for conversational shopping agents.
2. Be more realistic than the TechJam public evaluator while remaining controllable and testable.
3. Remain compatible with TechJam Track 4 through adapters rather than coupling the simulator core to the competition code.
4. Support both target-product evaluation and need-based shopping goals.
5. Keep LLMs out of behavioral control: the LLM only verbalizes a structured user action into natural English.

---

## 1. Scope

### 1.1 In scope for v0.1

- Conversational shopping user simulation.
- `TargetProductGoal` and `NeedBasedGoal`.
- Structured user policy with reproducible randomness.
- Persona templates.
- English-only user utterances.
- Template verbalization for deterministic benchmark runs.
- OpenAI-compatible LLM verbalization for realistic-language runs.
- Python shopping-agent adapter, including TechJam compatibility.
- TechJam dataset adapter.
- Amazon Reviews 2023 dataset adapter.
- Amazon Shopping Queries / ESCI dataset adapter.
- Scheduled and persona-driven intent override.
- Constraint relaxation.
- Alternatives as acceptable field-level substitutes, not as a second full goal.
- Session traces and benchmark metrics.
- Python library API and CLI.

### 1.2 Explicitly out of scope for v0.1

- Multilingual simulation.
- HTTP agent adapter.
- `GIVE_UP` behavior.
- Early termination caused by impatience.
- LLM-controlled planning, preference generation, goal mutation, acceptance decisions, or dialogue-act selection.
- Recommendation-content-aware behavioral reasoning beyond the acceptance checker.
- Complex utility models, purchase-probability models, or learned user policies.
- Multimodal product understanding.
- Production-scale data serving infrastructure.

---

## 2. Compatibility target: TechJam Track 4

The simulator is not a clone of the TechJam evaluator. TechJam is treated as the first compatibility target.

The TechJam-compatible mode must support:

- Max 10 turns by default.
- `session_id`, `user_message`, `turn`, and `top_k` agent inputs.
- Agent outputs containing `message`, `ask_attribute`, `recommendations`, and optional `usage`.
- TechJam `ask_attribute` values:
  - `category`
  - `material`
  - `color`
  - `size`
  - `style`
  - `brand`
  - `budget`
  - `feature`
  - `use_case`
  - `other`
  - `null`
- Exact `parent_asin` acceptance for TechJam-style `TargetProductGoal` runs.
- Scenario behavior compatible with buying, browsing, override, and boundary-like interactions.

The simulator must not depend directly on TechJam's concrete `Agent` implementation. Compatibility is provided through `PythonAgentAdapter` and `TechJamDatasetAdapter`.

---

## 3. Design principles

### 3.1 Policy owns behavior

The user policy decides what the simulated shopper does next.

The LLM does not decide:

- the next dialogue act;
- whether a recommendation is accepted;
- whether to override a preference;
- whether to relax a constraint;
- what hidden preferences exist;
- what the target product is.

### 3.2 LLM only performs verbalization

The core transformation is:

```text
structured dialogue act
        ->
allowed facts for this turn
        ->
LLM / template verbalizer
        ->
natural English user utterance
```

### 3.3 Hidden-state isolation

The verbalizer must never receive:

- target ASIN / target product ID;
- full hidden goal;
- undisclosed constraints;
- hidden ground-truth labels;
- hidden acceptable-product set.

It may receive only facts explicitly allowed to be expressed on the current turn.

### 3.4 Reproducibility before linguistic variety

Behavior must be reproducible under a fixed seed.

Two execution modes are required:

- `benchmark`: deterministic template verbalization or cached utterances.
- `realistic`: OpenAI-compatible LLM verbalization.

The structured trajectory must remain independently reproducible even if the final LLM wording is not bit-for-bit deterministic.

### 3.5 Backend- and dataset-independent core

Core models and policy logic operate on normalized shopping objects. Dataset-specific parsing belongs in adapters.

---

## 4. High-level architecture

```text
TechJam / Amazon Reviews 2023 / Amazon ESCI
                    |
                    v
             Dataset Adapters
                    |
                    v
         Normalized Product Catalog
                    |
                    v
                Goal Builder
          /                       \
 TargetProductGoal          NeedBasedGoal
          \                       /
                    v
              Persona Template
                    |
                    v
              Scenario Builder
                    |
                    v
                 UserState
                    |
                    v
                UserPolicy
                    |
                    v
           Structured DialogueAct
                    |
          +---------+---------+
          |                   |
 TemplateVerbalizer    LLMVerbalizer
          |                   |
          +---------+---------+
                    |
                    v
            Natural User Message
                    |
                    v
           PythonAgentAdapter
                    |
                    v
              Shopping Agent
                    |
                    v
              AgentResponse
                    |
          +---------+---------+
          |                   |
 AcceptanceChecker       UserPolicy
          |                   |
          +---------+---------+
                    |
                    v
           ACCEPT or next turn
                    |
                    v
                MAX_TURNS
```

---

## 5. Core domain model

### 5.1 Product

All dataset adapters must normalize products into a common representation.

```python
Product(
    product_id: str,
    title: str,
    categories: list[str],
    brand: str | None,
    price: float | None,
    features: list[str],
    description: str | None,
    attributes: dict[str, list[str]],
    raw: dict,
)
```

`raw` preserves source-specific fields for debugging but must not be required by core policy logic.

### 5.2 Constraint

A constraint represents one user requirement or preference.

```python
Constraint(
    attribute: str,
    values: list[str],
    strength: Literal["hard", "soft"],
    disclosed: bool = False,
    active: bool = True,
    source: str | None = None,
)
```

Examples:

```text
attribute=budget_max, values=["100"], strength=hard
attribute=color, values=["black"], strength=soft
attribute=brand, values=["Nike"], strength=soft
```

### 5.3 Alternatives

Alternatives are acceptable substitute values for a field. They are not another complete shopping goal.

Example:

```json
{
  "brand": ["Adidas", "Asics"],
  "color": ["gray"]
}
```

Meaning:

- Nike may be preferred.
- Adidas or Asics may still be acceptable for the same goal.
- Gray may be acceptable instead of black.
- These alternatives do not define another independent product target or second session objective.

---

## 6. Shopping goals

```text
ShoppingGoal
|- TargetProductGoal
`- NeedBasedGoal
```

### 6.1 TargetProductGoal

Use cases:

- TechJam benchmark compatibility.
- Exact-target retrieval evaluation.
- Amazon Reviews 2023 purchase-derived sessions.
- Reproducible hit/MRR/turn benchmarks.

Schema:

```python
TargetProductGoal(
    goal_id: str,
    target_product_id: str,
    constraints: list[Constraint],
    category: str | None,
    source_dataset: str,
)
```

Acceptance rule:

```text
if target_product_id is present in the normalized recommendation list within top_k:
    ACCEPT
else:
    continue
```

For TechJam-compatible runs, product identity is `parent_asin` and acceptance is exact ID equality.

The target product ID must never be exposed to the verbalizer.

### 6.2 NeedBasedGoal

Use cases:

- More realistic product-search simulation.
- Evaluating whether an agent can satisfy a shopping need without guessing one exact ASIN.
- Using ESCI substitutes as field-level acceptable alternatives where appropriate.

Schema:

```python
NeedBasedGoal(
    goal_id: str,
    category: str | None,
    hard_constraints: list[Constraint],
    soft_preferences: list[Constraint],
    alternatives: dict[str, list[str]],
    min_soft_matches: int = 1,
    source_dataset: str | None = None,
)
```

Example:

```json
{
  "goal_type": "need_based",
  "category": "running shoes",
  "hard_constraints": {
    "size": ["US 9"],
    "budget_max": ["100"]
  },
  "soft_preferences": {
    "brand": ["Nike"],
    "color": ["black"]
  },
  "alternatives": {
    "brand": ["Adidas", "Asics"],
    "color": ["gray"]
  },
  "min_soft_matches": 1
}
```

Acceptance rule for v0.1:

```text
A recommendation is acceptable if:

1. all hard constraints are explicitly satisfied; and
2. no explicit hard conflict exists; and
3. at least min_soft_matches soft preferences are satisfied.

A configured alternative value counts as satisfying the corresponding field.
```

Rules for missing metadata:

- Missing value for a hard constraint -> hard constraint is not satisfied.
- Missing value for a soft preference -> no soft match, but not an explicit conflict.
- Alternative values are evaluated only for the same attribute.

v0.1 intentionally does not use a weighted utility score or probabilistic purchase model.

---

## 7. Persona model

Persona is represented by a named template plus normalized values in `[0.0, 1.0]`.

Required dimensions:

```text
verbosity
patience
decisiveness
price_sensitivity
brand_loyalty
shopping_expertise
willingness_to_clarify
openness_to_alternatives
comparison_tendency
preference_stability
```

### 7.1 Persona templates

Initial built-in templates:

```text
decisive_buyer
casual_browser
bargain_hunter
brand_loyalist
picky_shopper
novice_shopper
expert_shopper
indecisive_shopper
```

Example:

```json
{
  "name": "bargain_hunter",
  "verbosity": 0.35,
  "patience": 0.55,
  "decisiveness": 0.65,
  "price_sensitivity": 0.95,
  "brand_loyalty": 0.20,
  "shopping_expertise": 0.55,
  "willingness_to_clarify": 0.75,
  "openness_to_alternatives": 0.80,
  "comparison_tendency": 0.70,
  "preference_stability": 0.75
}
```

### 7.2 Persona responsibilities

Persona may influence:

- utterance length and directness;
- probability of answering a clarification fully vs partially;
- probability of `NO_PREFERENCE` when a preference is weak or undefined;
- scheduled policy choices among valid non-terminal acts;
- probability of persona-driven override;
- likelihood of relaxing a non-essential constraint;
- likelihood of requesting comparison or more options when no direct question is asked.

Persona must not:

- change a hard constraint into an arbitrary unrelated value;
- leak hidden values;
- cause early session termination;
- override deterministic benchmark fixtures unless explicitly enabled in the scenario configuration.

### 7.3 Patience semantics

`patience` affects tone and response style only in v0.1.

It does not cause `GIVE_UP` and cannot terminate a session.

---

## 8. Dialogue acts

v0.1 schema supports exactly the following user acts:

```text
INITIAL_REQUEST
INFORM
ANSWER_ATTRIBUTE
NO_PREFERENCE
REJECT
ACCEPT
OVERRIDE
RELAX_CONSTRAINT
REQUEST_COMPARISON
REQUEST_MORE_OPTIONS
ASK_PRODUCT_QUESTION
```

`GIVE_UP` is not part of v0.1.

### 8.1 DialogueAct payload

```python
DialogueAct(
    type: DialogueActType,
    attribute: str | None = None,
    values: list[str] = [],
    reason_code: str | None = None,
    references: list[str] = [],
    allowed_facts: list[Fact] = [],
)
```

`allowed_facts` is the only hidden-goal-derived information that may be passed to a verbalizer.

### 8.2 Semantics

#### INITIAL_REQUEST

Starts the session with an intentionally partial expression of the goal.

The amount of disclosed information depends on scenario type and persona.

#### INFORM

Provides a relevant shopping fact without directly answering an attribute question.

v0.1 uses this mainly for deterministic scenario scripts and coarse follow-up behavior.

#### ANSWER_ATTRIBUTE

Answers the agent's requested attribute when an active, undisclosed matching constraint exists.

Example:

```text
ask_attribute=color
hidden active preference=color:black
-> ANSWER_ATTRIBUTE(color, black)
```

#### NO_PREFERENCE

Used when the agent asks about an attribute for which the user has no active preference or no additional fact to disclose.

#### REJECT

Indicates that the current recommendations are not accepted.

v0.1 may emit a generic rejection based on acceptance failure, but does not semantically inspect why each product failed beyond the acceptance checker.

#### ACCEPT

Terminal act generated only by the acceptance checker.

#### OVERRIDE

Replaces or removes a previously active preference/constraint according to a scheduled event or persona-driven policy event.

#### RELAX_CONSTRAINT

Weakens or removes a configured relaxable constraint.

The policy may only relax constraints explicitly marked relaxable by the scenario/goal builder.

#### REQUEST_COMPARISON

Requests comparison of recommended items.

In v0.1 this may be selected from coarse response shape and persona tendency; no deep product-level comparison reasoning is required.

#### REQUEST_MORE_OPTIONS

Requests additional recommendations after non-acceptance.

#### ASK_PRODUCT_QUESTION

Asks a product-related question about current options. v0.1 does not require product-content reasoning by the user policy; this act is primarily for conversational coverage.

---

## 9. User state

```python
UserState(
    session_id: str,
    turn: int,
    goal: ShoppingGoal,
    persona: Persona,
    disclosed_constraints: set[str],
    active_constraints: dict[str, Constraint],
    removed_constraints: dict[str, Constraint],
    override_history: list[OverrideEvent],
    relaxation_history: list[RelaxationEvent],
    conversation_history: list[ConversationTurn],
    last_dialogue_act: DialogueAct | None,
    accepted_product_id: str | None,
    terminated: bool,
    termination_reason: Literal["accept", "max_turns"] | None,
    rng_state: object,
)
```

The state is authoritative. The LLM verbalizer never owns or mutates it.

---

## 10. User policy

### 10.1 v0.1 behavior boundary

The user policy is primarily driven by:

- the agent's `ask_attribute`;
- whether recommendations are present;
- whether the acceptance checker found an acceptable result;
- current turn;
- scheduled scenario events;
- persona values;
- seeded random choices.

The user policy must not perform deep semantic reasoning over individual recommendation content in v0.1.

Recommendation content is inspected by the acceptance checker only.

### 10.2 Decision precedence

For each turn after receiving the agent response:

```text
1. Normalize AgentResponse.
2. Run AcceptanceChecker.
3. If accepted -> ACCEPT and terminate.
4. If this turn triggers scheduled OVERRIDE -> OVERRIDE.
5. Else if persona-driven override triggers -> OVERRIDE.
6. Else if a scheduled relaxation triggers -> RELAX_CONSTRAINT.
7. Else if ask_attribute is present:
      a. if matching undisclosed active fact exists -> ANSWER_ATTRIBUTE
      b. otherwise -> NO_PREFERENCE
8. Else if recommendations are present but not accepted:
      choose among REJECT / REQUEST_MORE_OPTIONS /
      REQUEST_COMPARISON / ASK_PRODUCT_QUESTION using persona + seed.
9. Else -> INFORM or REJECT using deterministic fallback policy.
10. Verbalize selected structured act.
11. If max_turns is reached without ACCEPT -> terminate with MAX_TURNS.
```

### 10.3 Reproducible randomness

All policy randomness must come from a per-session seeded PRNG.

Recommended seed derivation:

```text
hash(global_seed, session_id or sample_id, scenario_id, persona_name)
```

No policy decision may use global process randomness directly.

---

## 11. Override behavior

v0.1 supports two sources.

### 11.1 Scheduled override

Used for deterministic benchmark fixtures.

Example:

```json
{
  "turn": 4,
  "attribute": "color",
  "old_values": ["red"],
  "new_values": ["black"]
}
```

Behavior:

- previous value becomes inactive;
- new value becomes active;
- state records the override event;
- verbalizer receives only the information needed to express the change.

### 11.2 Persona-driven override

Enabled by configuration.

Probability is a deterministic function of:

- `preference_stability`;
- eligible turn range;
- seeded random number.

Lower `preference_stability` means higher override probability.

The new value must come from a pre-generated, valid alternate preference in the scenario. The policy must never invent a new hidden preference at runtime.

---

## 12. Constraint relaxation

Relaxation is allowed only for constraints marked `relaxable` during goal/scenario construction.

Examples:

```text
budget_max: 100 -> 120
brand: Nike -> any of [Nike, Adidas, Asics]
color: black -> [black, gray]
```

A relaxation must be represented as an explicit state transition and included in traces.

The LLM may verbalize the event but cannot determine the relaxed value.

---

## 13. Verbalization

### 13.1 Verbalizer interface

```python
class Verbalizer(Protocol):
    def verbalize(self, request: VerbalizationRequest) -> str:
        ...
```

### 13.2 VerbalizationRequest

```python
VerbalizationRequest(
    language: Literal["en"],
    persona_public_view: PersonaPublicView,
    dialogue_act: DialogueAct,
    allowed_facts: list[Fact],
    conversation_history: list[PublicConversationTurn],
    style_hint: str | None,
)
```

The request must not contain target product ID, full goal, undisclosed constraints, or acceptance labels.

### 13.3 TemplateVerbalizer

Required for benchmark mode.

Properties:

- deterministic;
- no external API;
- English only;
- templates keyed by dialogue act;
- stable under fixed simulator version.

Example:

```text
ANSWER_ATTRIBUTE(color=black)
-> "I'd prefer black."
```

Template selection may use the seeded PRNG only if the selected template index is also traceable and reproducible.

### 13.4 LLMVerbalizer

Required for realistic mode.

Provider contract: OpenAI-compatible chat/completions or responses-style endpoint through one adapter abstraction.

Minimum configuration:

```yaml
provider: openai_compatible
base_url: ${LLM_BASE_URL}
api_key: ${LLM_API_KEY}
model: ${LLM_MODEL}
temperature: 0.2
```

The prompt must instruct the model to:

- speak only as the shopper;
- express only the supplied allowed facts;
- preserve the supplied dialogue act;
- avoid mentioning hidden goals, IDs, or evaluation;
- stay consistent with persona tone;
- output only the user utterance.

### 13.5 LLM output validation

The simulator must reject or sanitize output that:

- contains target product IDs;
- mentions benchmark/evaluator/internal-state language;
- introduces factual values not present in `allowed_facts` when the act is fact-bearing;
- is empty.

On validation failure, fall back to `TemplateVerbalizer` and record the event.

---

## 14. Agent adapter

### 14.1 Core protocol

```python
class ShoppingAgentAdapter(Protocol):
    def reset(self, session_id: str, user_profile: dict) -> None:
        ...

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> AgentResponse:
        ...
```

### 14.2 PythonAgentAdapter

v0.1 implements Python integration only.

Responsibilities:

- wrap a Python shopping agent object;
- normalize return values;
- isolate simulator code from agent-specific classes;
- support TechJam's `reset` / `respond` interface;
- convert invalid responses into a normalized empty response while recording an adapter error.

### 14.3 AgentResponse

```python
AgentResponse(
    message: str,
    ask_attribute: str | None,
    recommendations: list[Recommendation],
    usage: Usage | None,
    raw: object | None,
    error: str | None,
)
```

### 14.4 Recommendation

```python
Recommendation(
    product_id: str,
    score: float | None = None,
    raw: object | None = None,
)
```

For TechJam, `product_id` maps to `parent_asin`.

---

## 15. Dataset adapters

### 15.1 DatasetAdapter protocol

```python
class DatasetAdapter(Protocol):
    def load_products(self) -> Iterable[Product]:
        ...

    def build_sessions(self, config: DatasetConfig) -> Iterable[SessionSpec]:
        ...
```

Adapters may also expose dataset-specific preparation utilities.

### 15.2 TechJamDatasetAdapter

Purpose:

- load the frozen TechJam catalog;
- load public sample sessions;
- map `parent_asin` to normalized `product_id`;
- preserve scenario type and profile;
- create TechJam-compatible `TargetProductGoal` sessions;
- optionally derive normalized constraints from product metadata without copying evaluator wording.

### 15.3 AmazonReviews2023Adapter

Purpose:

- expand product coverage beyond the 50k TechJam catalog;
- use public Amazon Reviews 2023 product metadata;
- use purchase/review relationships to derive target-product sessions where licensing/data availability allows;
- create normalized product records and goal-building inputs.

Data is not committed directly to the repository.

The adapter must support preparation from user-supplied/downloaded source files and create local normalized artifacts under ignored data directories.

### 15.4 AmazonESCIAdapter

Purpose:

- use query-product relevance judgments from Amazon Shopping Queries / ESCI;
- preserve ESCI labels:
  - `Exact`
  - `Substitute`
  - `Complement`
  - `Irrelevant`
- generate search-oriented session seeds;
- provide substitute evidence for alternatives in need-based goals.

v0.1 interpretation:

```text
Exact      -> strong target/relevance evidence
Substitute -> acceptable field-level alternative evidence when mapping is valid
Complement -> not a replacement target
Irrelevant -> negative relevance evidence
```

The adapter must not blindly convert every substitute product into a second full shopping goal.

### 15.5 Data storage policy

The repository contains:

- adapters;
- preparation scripts;
- schemas;
- manifests;
- tiny test fixtures;
- source/license notes.

The repository does not contain large raw external datasets.

Recommended local layout:

```text
data/
  raw/
  prepared/
  cache/
```

All large/local files are ignored by Git.

---

## 16. Goal construction

### 16.1 Target-product goal builder

Inputs may include:

- a TechJam ground-truth product;
- an Amazon Reviews 2023 purchase/review-linked product;
- an ESCI Exact product-query pair.

The builder derives a controlled set of candidate constraints from normalized metadata.

Constraint derivation must be versioned and deterministic.

The goal builder may use rules and deterministic extraction. An LLM is not required for v0.1 goal construction.

### 16.2 Need-based goal builder

The builder creates:

- category;
- hard constraints;
- soft preferences;
- relaxable flags;
- valid alternative values;
- `min_soft_matches`.

Need-based goals may be derived from a target-like product seed, but acceptance is based on need satisfaction rather than exact target ID.

The builder must ensure that at least one product in the prepared catalog can satisfy the goal; otherwise the session must be rejected during validation.

---

## 17. Scenario model

```python
ScenarioSpec(
    scenario_id: str,
    goal: ShoppingGoal,
    persona_template: str,
    max_turns: int = 10,
    initial_disclosure_policy: str,
    scheduled_overrides: list[OverrideEvent] = [],
    scheduled_relaxations: list[RelaxationEvent] = [],
    persona_driven_override_enabled: bool = False,
    seed: int,
)
```

### 17.1 Initial disclosure

The simulator must not reveal the full goal on the first turn by default.

Initial disclosure may include:

- category;
- one hard constraint;
- one soft preference;
- vague browsing intent.

Exact disclosure is scenario-configurable and deterministic under a fixed seed.

---

## 18. Acceptance checker

### 18.1 Target mode

```text
accepted_product = exact target product ID in top_k recommendations
```

Record:

- accepted product ID;
- rank;
- acceptance turn.

### 18.2 Need-based mode

For each recommended product in order:

1. evaluate hard constraints;
2. evaluate explicit conflicts;
3. evaluate soft preference matches;
4. count same-field alternatives as matches;
5. accept the first product satisfying the configured rule.

Record detailed match evidence privately in the trace.

### 18.3 Acceptance does not depend on LLM output

Acceptance is a pure deterministic function of:

- goal;
- normalized catalog product;
- recommendation list;
- acceptance configuration.

---

## 19. Session lifecycle

Only two terminal outcomes exist in v0.1:

```text
ACCEPT
MAX_TURNS
```

No `GIVE_UP` state exists.

Agent exceptions, invalid responses, empty recommendations, or verbalizer failures do not create additional terminal states. They are recorded and the session continues until `ACCEPT` or `MAX_TURNS`.

Default `max_turns` for TechJam-compatible configuration is 10.

---

## 20. Trace model

Two trace views are required.

### 20.1 Private debug trace

May contain:

- full goal;
- target product ID;
- full persona;
- state before/after each turn;
- active/disclosed/removed constraints;
- policy RNG decisions;
- dialogue act;
- verbalizer input;
- user utterance;
- agent response;
- recommendations;
- acceptance evidence;
- override/relaxation events;
- token usage;
- latency;
- errors/fallbacks;
- termination reason.

### 20.2 Public conversation trace

Must exclude:

- target product ID before acceptance disclosure policy permits it;
- hidden goal;
- undisclosed constraints;
- internal acceptance evidence;
- policy random values.

Contains only the externally visible conversation and safe metadata.

---

## 21. Evaluation

### 21.1 Agent metrics — TargetProductGoal

Required:

- Success Rate / Hit Rate@K.
- MRR.
- Mean Turns to Acceptance / MTTC-compatible metric.
- Rank at acceptance.
- Per-scenario metrics.

TechJam-compatible configuration may compute the official-style technical score separately.

### 21.2 Agent metrics — NeedBasedGoal

Required:

- Need-based success rate.
- Mean turns to acceptance.
- Hard-constraint satisfaction rate at acceptance.
- Mean soft preference matches at acceptance.
- Alternative-use rate.
- Acceptance rank.

### 21.3 Simulator quality diagnostics

Required diagnostics:

- structured trajectory reproducibility under fixed seed;
- target leakage count;
- invalid LLM output fallback count;
- persona-template distribution;
- dialogue-act distribution;
- override rate;
- relaxation rate;
- no-preference rate;
- act coverage across a benchmark suite.

Optional realistic-mode diagnostics:

- utterance lexical diversity;
- average utterance length by persona;
- LLM token usage and latency.

The simulator must distinguish agent-quality metrics from simulator-quality diagnostics.

---

## 22. Benchmark vs realistic mode

### 22.1 Benchmark mode

```yaml
mode: benchmark
verbalizer: template
seed: 42
```

Requirements:

- no external LLM dependency;
- deterministic policy;
- deterministic wording or deterministic cached wording;
- reproducible results from the same data/config/version.

### 22.2 Realistic mode

```yaml
mode: realistic
verbalizer: openai_compatible
seed: 42
```

Requirements:

- same structured policy semantics;
- natural English realization;
- hidden-state isolation;
- LLM validation and template fallback;
- record model/provider configuration and token usage.

Realistic mode may vary wording across executions, but it must not change the authoritative structured state trajectory because of free-form model reasoning.

---

## 23. Configuration

Illustrative configuration:

```yaml
version: "0.1"
language: en
mode: benchmark
seed: 42
max_turns: 10
top_k: 10

dataset:
  name: techjam
  catalog_path: data/raw/techjam/catalog.jsonl
  sessions_path: data/raw/techjam/public_set.jsonl

goals:
  mode: mixed
  target_product_ratio: 0.7
  need_based_ratio: 0.3

need_based_acceptance:
  require_all_hard_constraints: true
  min_soft_matches: 1
  alternatives_count_as_match: true

persona:
  templates:
    - decisive_buyer
    - casual_browser
    - bargain_hunter
    - brand_loyalist
    - picky_shopper
    - novice_shopper
    - expert_shopper
    - indecisive_shopper

override:
  scheduled_enabled: true
  persona_driven_enabled: true

verbalizer:
  type: template

agent:
  adapter: python
  techjam_compatible: true

trace:
  private_output: runs/private.jsonl
  public_output: runs/public.jsonl
```

Realistic-mode verbalizer configuration:

```yaml
verbalizer:
  type: openai_compatible
  base_url_env: LLM_BASE_URL
  api_key_env: LLM_API_KEY
  model_env: LLM_MODEL
  temperature: 0.2
  fallback: template
```

---

## 24. Python library API

Target public API shape:

```python
from user_simulator import Simulator, SimulatorConfig
from user_simulator.adapters import PythonAgentAdapter

config = SimulatorConfig.from_yaml("config.yaml")
agent = PythonAgentAdapter(my_agent)
simulator = Simulator(config=config, agent=agent)

result = simulator.run()
```

Per-session API:

```python
session = simulator.create_session(session_spec)
result = session.run()
```

The exact package names may change during implementation, but the separation of core simulator, adapters, policy, verbalizers, and evaluation is normative.

---

## 25. CLI

v0.1 must provide a CLI.

Proposed commands:

```bash
# Run a benchmark
user-simulator run --config configs/techjam_benchmark.yaml

# Run realistic-language simulation
user-simulator run --config configs/techjam_realistic.yaml

# Prepare external data
user-simulator data prepare amazon-reviews-2023 --input <path>
user-simulator data prepare amazon-esci --input <path>

# Validate data/config/session feasibility
user-simulator validate --config configs/techjam_benchmark.yaml

# Summarize a run
user-simulator report runs/private.jsonl
```

Commands must be non-interactive by default so they can run in CI.

---

## 26. Proposed package layout

```text
user-simulator/
├── docs/
│   └── TECHNICAL_SPEC_v0.1.md
├── src/
│   └── user_simulator/
│       ├── __init__.py
│       ├── models/
│       │   ├── product.py
│       │   ├── goal.py
│       │   ├── persona.py
│       │   ├── dialogue.py
│       │   └── state.py
│       ├── policy/
│       │   ├── user_policy.py
│       │   ├── override.py
│       │   └── relaxation.py
│       ├── acceptance/
│       │   └── checker.py
│       ├── verbalizers/
│       │   ├── base.py
│       │   ├── template.py
│       │   └── openai_compatible.py
│       ├── adapters/
│       │   ├── agents/
│       │   │   ├── base.py
│       │   │   └── python.py
│       │   └── datasets/
│       │       ├── base.py
│       │       ├── techjam.py
│       │       ├── amazon_reviews_2023.py
│       │       └── amazon_esci.py
│       ├── goals/
│       │   └── builder.py
│       ├── evaluation/
│       │   ├── metrics.py
│       │   └── report.py
│       ├── tracing/
│       │   └── trace.py
│       ├── simulator.py
│       └── cli.py
├── configs/
│   ├── techjam_benchmark.yaml
│   └── techjam_realistic.yaml
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── pyproject.toml
```

---

## 27. Validation rules

Before a session can run, validation must ensure:

- product IDs are unique in the normalized catalog;
- target-product goals reference an existing product;
- need-based goals have at least one satisfying catalog product;
- hard and soft constraints use supported normalized attributes;
- alternatives refer to the same field they substitute;
- scheduled override turns are within `[2, max_turns]`;
- override source values are active before replacement;
- override destination values are pre-generated and valid;
- relaxations reference relaxable constraints;
- persona dimensions are in `[0, 1]`;
- language is `en`;
- benchmark mode does not require an external LLM;
- all seeds are explicit or derived deterministically.

Invalid sessions are rejected before benchmark execution rather than silently repaired at runtime.

---

## 28. Error handling

### 28.1 Agent failures

If the Python agent raises an exception or returns an invalid payload:

- record the error;
- normalize to an empty `AgentResponse`;
- continue the session;
- do not introduce a new terminal state.

### 28.2 LLM failures

If the LLM request fails or output validation fails:

- record the error;
- use `TemplateVerbalizer` for that turn;
- preserve the already-selected structured dialogue act.

### 28.3 Dataset failures

Dataset parsing/preparation errors are fail-fast for the affected preparation job. Prepared dataset artifacts must include schema/version metadata.

---

## 29. Testing requirements

### 29.1 Unit tests

Required coverage:

- TargetProductGoal acceptance.
- NeedBasedGoal acceptance.
- Alternative-value matching.
- Missing-metadata behavior.
- Dialogue-act selection for agent questions.
- `NO_PREFERENCE` behavior.
- Scheduled override.
- Persona-driven override reproducibility.
- Constraint relaxation.
- Template verbalization.
- hidden-state isolation.
- PythonAgentAdapter normalization.
- max-turn termination.

### 29.2 Integration tests

Required:

- deterministic full session with mock Python agent;
- TechJam-compatible mock session;
- realistic verbalizer with mocked OpenAI-compatible endpoint;
- dataset adapter fixtures for TechJam, Amazon Reviews 2023, and ESCI;
- benchmark repeatability: same seed/config -> same structured trajectory and metrics.

### 29.3 Leakage tests

The test suite must assert that verbalization requests never contain:

- target product ID;
- undisclosed constraint values;
- full hidden goal serialization.

---

## 30. v0.1 success criteria

Implementation is considered v0.1-complete when all of the following are true:

1. A TechJam-compatible Python agent can be evaluated end-to-end for up to 10 turns.
2. Both `TargetProductGoal` and `NeedBasedGoal` sessions run.
3. All listed dialogue acts exist in the schema and have valid policy/verbalization paths.
4. `GIVE_UP` does not exist.
5. Benchmark mode is deterministic without an LLM.
6. Realistic mode can use any configured OpenAI-compatible endpoint and safely falls back to templates.
7. Persona templates influence behavior/style without taking control away from the policy.
8. Scheduled and persona-driven override work and are reproducible.
9. Amazon Reviews 2023 and Amazon ESCI can be prepared through adapters without committing large raw datasets.
10. PythonAgentAdapter supports TechJam's interface.
11. Hidden target/undisclosed constraints are never exposed to the verbalizer.
12. CLI can run, validate, prepare data, and report benchmark results.
13. Tests cover acceptance, state transitions, reproducibility, adapter behavior, and leakage prevention.

---

## 31. Deferred work after v0.1

Potential later extensions, not part of this specification:

- recommendation-content-aware simulated user reactions;
- learned behavior-policy calibration from real dialogue datasets;
- HTTP agent adapter;
- multilingual verbalization;
- richer product-question behavior;
- explicit product comparison reasoning;
- probabilistic purchase/utility model;
- session abandonment / `GIVE_UP`;
- long-term user memory across shopping sessions;
- user-profile generation from interaction history;
- richer substitutes/complements modeling from ESCI;
- realistic noisy inputs, typos, ASR errors, and code-switching.

---

## 32. Reference compatibility sources

The v0.1 compatibility requirements are based on the public TikTok TechJam 2026 Track 4 participant materials and repository:

- TechJam Track 4 participant repository: `https://github.com/TechJam2026/techjam-conversational-search`
- TechJam public evaluator: `evaluator/local_evaluator.py`
- TechJam starter agent: `starter/agent.py`
- Amazon Reviews 2023: `https://amazon-reviews-2023.github.io/`
- Amazon Shopping Queries / ESCI: Amazon Science public Shopping Queries Dataset

The simulator intentionally extends beyond the official evaluator by adding explicit personas, need-based goals, alternatives, deterministic behavior policies, controlled overrides/relaxations, and a strict separation between behavior and language generation.
