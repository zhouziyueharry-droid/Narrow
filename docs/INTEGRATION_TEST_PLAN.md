# Integration and evaluation plan

## Integration target

The integration branch uses `origin/main` as the architecture baseline, merges
the dual-mode simulator from `origin/testing`, and ports the behavior of
`origin/yxh` into the corresponding modules of the layered architecture.
Source branches remain unchanged.

The integrated behavior from `yxh` is:

- compound and bounded negation extraction;
- budget-range extraction without double counting;
- implicit same-field intent override in deterministic fallback;
- one DeepSeek retry and separate invalid-response/outage reasons.

## Evidence contract

Every run uses a new `integration_runs/<run_id>/` directory. A completed run
must contain:

- `00_manifest.json`: run ID, integration commit, source branch SHAs, runtime,
  API-enabled booleans (never keys), and dataset hashes;
- `stages.json`: exact command, working directory, start/end timestamps,
  elapsed time, exit code, and log path for every stage;
- `logs/*.log`: complete stdout/stderr for each stage;
- `logs/<mode>.events.jsonl`: append-only session started/completed/failed events;
- `results/techjam.{json,md}` and `results/realistic.{json,md}`;
- `results/<mode>.sessions.jsonl`: one flushed record after every completed session;
- `comparisons/session_findings.jsonl`: deterministic flags across all sessions;
- `checksums.sha256`: hashes for every final evidence artifact;
- `final_report.md`: pass/fail gates, metric comparison, failures and fallbacks.

TechJam and realistic results are always separate. Each aggregate JSON keeps:

```text
evaluation
turn_metrics
latency
model_usage
mode_specific_metrics
sessions
```

## Per-turn and per-layer evidence

Each `sessions[].conversation[]` record keeps user text, Agent response,
recommendations, dialogue act, latency, reported token usage, and
`agent_layer_trace`. The trace records the node name and compact state update
for every available Agent layer, including:

1. intent understanding and the produced `StatePatch`;
2. active and superseded constraints;
3. lexical, dense and attribute retrieval candidate counts and top candidates;
4. fused and filtered candidates;
5. ranking scores, explanations and top results;
6. question/dialogue decisions and the final response.

If trace capture fails or the Agent does not support it, `agent_trace_error`
records the exact failure. A missing trace is never treated as a successful
empty layer.

## Test gates

### Gate 0: frozen inputs

- clean integration worktree;
- exact `origin/main`, `origin/testing`, `origin/yxh`, and integration SHAs;
- Python, uv and dependency versions;
- catalog and TechJam public-session SHA-256 values;
- LLM enablement/provider/model without secret values.

### Gate 1: static and unit tests

- Agent unit, regression and integration tests;
- simulator unit tests;
- Ruff and `git diff --check`.

### Gate 2: migrated behavior

- compound and overlong negation cases;
- `between` and dash budget ranges;
- preferred versus maximum budgets without duplicates;
- implicit override without marker words;
- transient provider retry;
- invalid provider JSON and persistent outage classification.

### Gate 3: contract and trace

- `reset` and `respond` contract;
- valid `message`, `ask_attribute`, recommendations and usage;
- no target-product leakage;
- non-empty per-layer trace for the integrated Agent;
- explicit error for unavailable or failed trace capture.

### Gate 4: traditional one-session smoke

Set `SHOPPING_AGENT_ENABLE_LLM=false` and use the template verbalizer. Run one
TechJam and one realistic session. Verify separate reports, all required
sections, per-turn traces, live latency and zero API use.

### Gate 5: traditional full evaluation

- TechJam: all 200 official sessions, exact target semantics, ten-turn cap and
  miss value 11 for MTTC;
- realistic: 100 catalog-derived need-based sessions, never labelled as an
  official TechJam score.

Compare TechJam headline metrics and changed sessions against the previous
baseline. The current legacy baselines contain aggregate Markdown only, so
sample-level regression claims require regenerating the old commit with full
session JSON; until then comparison is explicitly aggregate-only. Any
unexplained aggregate drift blocks completion.

### Gate 6: DeepSeek matrix

Run one to five sessions for each independently controlled configuration:

| Agent LLM | User verbalizer | Purpose |
| --- | --- | --- |
| off | template | traditional control |
| on | template | Agent-only effect |
| off | DeepSeek | user-language effect |
| on | DeepSeek | full realistic path |

Record provider, model, calls, reported tokens, retry/fallback errors and cost
status. A full paid batch starts only after smoke results and expected usage are
reviewed.

## Completion rule

Integration is complete only when all applicable gates pass, both result JSON
files validate against the simulator report schema, trace coverage is reported,
all artifacts are checksummed, and every regression or metric change has a
session-level explanation.

## Completed reports

- [Traditional dual-mode full evaluation — 2026-08-29](integration_reports/traditional_full_20260829_0005/README.md)
