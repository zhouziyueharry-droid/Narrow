# Realistic Hard DeepSeek Full Evaluation

## Run identity

- Run: `realistic_hard_deepseek_full_20260829`
- Source branch: `test/realistic-hard-20260829`
- Evaluation commit: `06795c29b36af012995217d35a4c562ae6891d88`
- Pulled `origin/main`: `8f4f392407c47c46be5c528069f088218ffbea97`
- Model: `deepseek-v4-flash` for both the Shopping Agent and user verbalizer
- Runtime: 2026-08-29 17:15:40 to 17:22:18 Asia/Singapore (398.5 seconds)
- This is a realistic need-based evaluation. `official_metric_contract=false`; it is not an official TechJam score.

## Model usage and non-LLM boundaries

This run was not fully LLM-driven. DeepSeek was used for two language tasks only; retrieval and scoring remained deterministic.

| Component | Uses an LLM? | Model or implementation in this run | Responsibility |
| --- | --- | --- | --- |
| Shopping Agent `understand_user` | Yes | `deepseek-v4-flash` | Parses natural-language user messages into a structured `StatePatch`, including intent, category, constraints, removals, and overrides |
| Simulator user verbalizer | Yes | `deepseek-v4-flash` | Converts a simulator-selected structured dialogue act into natural language; it does not choose the user goal or acceptance decision |
| Agent local rule parsing and failure fallback | No | Deterministic Python rules | Supplies rule signals and produces a local parse when the LLM is unavailable or invalid |
| Catalog retrieval, candidate fusion, and constraint filtering | No | Deterministic local retrieval code | Retrieves, combines, and filters candidates from the 50,000-product catalog |
| Fallback reranking, question policy, and response templates | No | Deterministic local code | Ranks candidates, chooses a clarification attribute, and builds the Agent response frame |
| Simulator goals, personas, overrides, and budget relaxations | No | Seeded scenario rules | Defines the simulated user's actual needs and scheduled changes over turns |
| Acceptance checker | No | Hard-constraint and soft-preference rules | Requires every hard constraint and at least two soft preferences to match |
| Evaluator metric calculation | No | Deterministic Python formulas | Computes success rate, MRR, turns, latency, token usage, and mode-specific metrics |

The Agent's DeepSeek path performs semantic understanding only; it does not directly select products from the catalog or participate in final scoring. All 151 Agent responses reported model-token usage, totaling 128,583 tokens. The Agent contract does not report a separate API-call count, so that field remains `null` and must not be inferred as 151. The user verbalizer explicitly made 151 DeepSeek API calls, used 33,823 tokens, and had zero fallbacks. The evaluator's scoring process made no LLM calls.

For contrast, official TechJam mode uses deterministic template-generated user messages, so the simulated-user side does not use an LLM; the official evaluator is also non-LLM. In TechJam mode, only the participant Shopping Agent may use DeepSeek when its LLM configuration is enabled.

## Difficulty design

The `realistic_hard` preset uses 24 deterministic catalog-derived sessions, eight personas, eight turns maximum, at least three soft preferences, two required soft matches, a budget only 2% above the seed product, and category-only initial disclosure. A product is not accepted while the Agent is still asking a clarification question.

Four pressure variants are balanced at six sessions each:

1. `hidden_preferences`: the user gradually reveals preferences.
2. `preference_override`: the user changes or removes an earlier preference.
3. `budget_relaxation`: an initially tight budget is relaxed after turn four.
4. `override_and_relaxation`: preference change and budget relaxation occur together.

## Results

- Sessions: 24; successful: 19; unsuccessful: 5; success rate: **79.17%**.
- Executed turns: 151; mean 6.29; median 6.5; failed sessions all reached the eight-turn limit.
- Need-based MRR: 0.7167. Hard constraints at acceptance: 100%. Mean soft matches at acceptance: 2.42.
- Candidate recommendations were deliberately prevented from premature acceptance 74 times.
- Accepted while Agent was still asking: 0.
- Preference overrides: 12; budget relaxations: 12.
- Agent latency: mean 1,289 ms, p95 1,747 ms, maximum 2,748 ms.
- User verbalizer latency: mean 683 ms, p95 1,003 ms, maximum 1,756 ms.
- Agent: 151 responses, 151 usage records, 128,583 reported tokens, 0 errors.
- User verbalizer: 151 API calls, 33,823 tokens, 0 fallbacks.
- Combined reported tokens: 162,406. Cost is intentionally `null` because no pricing source was supplied.

### By pressure type

| Type | Success | Rate | Mean turns |
| --- | ---: | ---: | ---: |
| Hidden preferences | 4/6 | 66.7% | 6.50 |
| Preference override | 6/6 | 100.0% | 5.83 |
| Budget relaxation | 4/6 | 66.7% | 6.50 |
| Override + relaxation | 5/6 | 83.3% | 6.33 |

### By persona

The weakest small-sample groups were `bargain_hunter` (1/3) and `decisive_buyer` (1/3). `brand_loyalist`, `casual_browser`, `expert_shopper`, `novice_shopper`, and `picky_shopper` were 3/3. These are diagnostic slices with only three sessions each, not stable population estimates.

## Concrete failure example

Session `realistic_0001_B0949GR8H9` asked for a Jewelry Box with budget 8.15, LETURE brand, white color, and leather-related material. It failed after eight turns even though the target product appeared at rank 3 on turn 2.

Observed sequence and layer-level cause:

1. The Agent asked for brand; the user replied only `LETURE.`
2. `understand_user` returned `action=no_preference` with `no_structured_signal`, so the pending brand answer was not attached to the Agent's previous question.
3. The Agent asked for style; the user said no preference. On the next turn, `understand_user` removed `color` instead of marking `style` as no preference.
4. The Agent asked for budget; the user replied only `8.15.` The parser again returned `no_structured_signal`, so the budget constraint was lost.
5. After the Agent stopped asking, the target no longer appeared in the top five and the simulator correctly rejected the recommendations.

This is primarily a **contextual answer-resolution defect**, not a catalog absence or simulator acceptance bug. Bare answers such as a brand name, a number, or “no preference” need to be resolved against the Agent's stored pending question before semantic parsing/state update. The same trace also shows why per-layer recording matters: looking only at final success would incorrectly blame retrieval.

## Recommended Agent changes

1. Pass `pending_question.attribute` into `understand_user`, or deterministically bind short answers to the last asked attribute before the LLM parser.
2. Interpret a numeric-only answer to a budget question as `budget_max` with currency inherited from the catalog/session.
3. Scope “no preference” to the pending attribute; never guess a previously supplied field such as color.
4. Add regression tests for `LETURE.`, `8.15.`, and `I don't have a preference.` after brand, budget, and style questions.
5. Add a retrieval recovery policy after explicit rejection; repeating a generic closest-match response without updating state does not create new evidence.

## Validation and evidence

- Hard-mode validator: passed all 24 sessions, all four scenario types, all personas, all 13 required Agent nodes, API-use checks, and acceptance-gate checks.
- Unified report-schema validator: passed.
- Simulator tests: 21 passed.
- Agent tests: 35 passed.
- Complete results and per-turn traces are in `realistic.json`.
- Crash-resilient session records are in `realistic.sessions.jsonl`; progress events are in `realistic.events.jsonl`.
- Human-readable generated metrics are in `realistic.md`; logs are under `logs/`.
- `00_manifest.json` fixes the exact commit, catalog hash, model configuration, and runtime without exposing the API key.

