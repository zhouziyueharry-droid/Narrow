# TechJam Conversational E-Commerce Search Challenge

Build an AI shopping agent that asks useful follow-up questions and recommends the customer's hidden target product within at most 10 turns.

## What You Receive

- A frozen catalog of 50,000 products from the `Clothing_Shoes_and_Jewelry` category of Amazon Reviews 2023.
- 200 labeled public sessions for local development.
- A weak BM25 starter agent and deterministic local evaluator.
- The Agent API contract and scoring rules.

The organizer keeps 800 additional sessions private for final evaluation.

## Task

For each session, your agent receives an anonymized preference profile and a short customer message. Raw user IDs, review text, timestamps, and purchase history are never disclosed. On every turn the agent may:

- ask a natural clarification question in `message` and identify one requested field in `ask_attribute`;
- return a ranked list of up to 10 catalog `parent_asin` values;
- do both in the same response.

The session ends when the target product appears in the scored Top 10 or after turn 10. Sessions cover Buying, Browsing, Intent Override, and Boundary behavior.

## Download the Catalog

Download `catalog.jsonl.gz` from the GitHub Release attached to this repository, then run:

```bash
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

Verify the downloaded file using the published `SHA256SUMS` file.

## Run the Starter

Python 3.10 or later is recommended. The starter uses only the Python standard library.

```bash
python3 -m evaluator.local_evaluator
```

Edit `starter/agent.py` to implement your system. Do not edit the evaluator or public labels when reporting your local score.
The command writes per-session results and aggregate metrics to `results.json`.

The included weak BM25 starter scores Hit Rate@10 `0.125`, MRR `0.068034`, and
MTTC `9.81` on the released public set. See `docs/baseline_results.json`.

## Agent Interface

```python
class Agent:
    def reset(self, session_id: str, user_profile: dict) -> None:
        ...

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        return {
            "message": "Do you have a material preference?",
            "ask_attribute": "material",
            "recommendations": [
                {"parent_asin": "B000..."},
                {"parent_asin": "B001..."}
            ],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30}
        }
```

`ask_attribute` is one of `category`, `material`, `color`, `size`, `style`, `brand`, `budget`, `feature`, `use_case`, `other`, or `null`. See `docs/agent_api_contract.json`.

## Technical Metrics

- **Hit Rate@10:** fraction of sessions that find the target within 10 turns.
- **MRR:** mean reciprocal rank of the target; a miss contributes zero.
- **MTTC:** mean first-hit turn; a miss is assigned turn 11.
- **Reported token usage:** prompt and completion tokens returned by the team's model client.

```text
TechnicalScore = 0.50 × HitRate@10 + 0.30 × MRR + 0.20 × Efficiency
Efficiency = clip((11 - MTTC) / 10, 0, 1)
```

Only exact `parent_asin` equality produces a hit. Core metrics are also reported by scenario.

## Model Choice and Cost

Teams may use any legally accessible LLM API or local model. Teams manage their own credentials and must never commit API keys. Model choice, estimated cost, token usage, and latency must be disclosed. Token usage is a feasibility metric, not part of the core technical score. The organizer does not provide or reimburse model API credits; teams are responsible for any costs incurred through optional external services.

## LangGraph Shopping Agent

The product core accepts normal user messages through `start_session/chat`; the
official `reset/respond` interface is a thin competition adapter. Every turn
produces both structured intent state for filtering and a compact
`semantic_query` for vector retrieval, then runs lexical, semantic, and
attribute routes in parallel. Reciprocal-rank fusion, hard-constraint filtering,
relaxed-query backfill, local feature reranking, candidate-driven clarification,
and output validation complete the online path.

When DeepSeek is enabled it is the primary intent interpreter on every turn,
including negation, references, conditional budgets, and intent replacement.
The local parser remains a reliability fallback when the provider is disabled
or unavailable. Clarification questions are selected from the attribute
distribution of the current candidates rather than fixed evaluator turns.

```bash
uv sync --group dev
```

To install the optional DeepSeek/OpenAI-compatible client later:

```bash
uv sync --extra deepseek --group dev
```

Then fill `DEEPSEEK_API_KEY` in `.env` and set
`SHOPPING_AGENT_ENABLE_LLM=true`. The default model is
`deepseek-v4-flash`; API failures retain the local semantic fallback.

Provider smoke test and a full API-enabled public evaluation are available as:

```bash
uv run python scripts/smoke_deepseek.py
uv run python scripts/evaluate_with_deepseek.py --output results.json
```

Neither script prints or stores the API key.

To preserve complete conversations and compact node-by-node checkpoint diffs:

```bash
uv run python scripts/evaluate_with_traces.py --llm --candidate-limit 20
```

Each run is stored under `evaluation_runs/<timestamp>/` with configuration,
summary, session metadata, every conversation turn, node traces, and a readable
Markdown report. `evaluation_runs/LATEST.txt` points to the newest run.

For the team-standard parallel official evaluation, exact target-loss replay,
and trace-visualizer workflow, follow
[`../docs/TEST_TRACE_VISUALIZATION_RUNBOOK.md`](../docs/TEST_TRACE_VISUALIZATION_RUNBOOK.md).

Run the tests and public evaluator with:

```bash
uv run pytest
uv run python -m evaluator.local_evaluator
```

To inspect and run the graph in LangSmith Studio:

```bash
uv run langgraph dev
```

On Windows PowerShell, enable UTF-8 before starting the CLI:

```powershell
$env:PYTHONUTF8 = "1"
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv run langgraph dev
```

The local API starts on `http://127.0.0.1:2024`; the command prints and opens
the matching Studio URL. Set `LANGSMITH_API_KEY` in your environment when Studio
prompts for LangSmith authentication.

The implementation is divided by team-owned capability under
`src/shopping_agent/`: application, orchestration, domain, understanding,
retrieval, ranking, dialogue, infrastructure, and observability. Legacy
top-level imports remain as compatibility facades. See
`docs/architecture/module_boundaries.md` for ownership and dependency rules.

## Files

```text
data/public_set.jsonl             200 labeled development sessions
docs/agent_architecture.md        runtime architecture
docs/architecture/                module ownership and dependency rules
docs/contracts/                   stable component interfaces
docs/experiments/                 compact experiment decisions
docs/competition_specification.md participant rules and evaluation protocol
docs/agent_api_contract.json      machine-readable Agent contract
docs/evaluation_config.json       scoring configuration
docs/baseline_results.json        reproducible weak-starter reference score
starter/agent.py                  editable weak starter
evaluator/local_evaluator.py      public-set simulator and scorer
evaluation_runs/                  timestamped conversations and node traces
```

## Judging and Submission Policy

- Participant submission requirements: `docs/submission_rules.md`
- Participant release checklist: `docs/participant_release_checklist.md`
- Organizer-only final judging controls: `organizer/JUDGING_RUNBOOK.md`
- Organizer private release checklist: `organizer/private_release_checklist.md`
- Judging day operations SOP: `organizer/JUDGING_DAY_SOP.md`

## Data Source

The catalog and sessions are derived from Amazon Reviews 2023 by McAuley Lab, UCSD. See `DATA_ATTRIBUTION.md` before using or redistributing the data.
Sessions are sampled deterministically from the official Clothing 5-core leave-last-out split and joined to the frozen catalog.
