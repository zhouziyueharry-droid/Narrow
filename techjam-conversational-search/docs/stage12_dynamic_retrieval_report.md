# Stage 1–2 Dynamic Retrieval Evaluation

This report compares the merged `final` implementation at commit
`2d309d07c6b9fce7a18345304cb175c31a58461b` with the stage 1–2 retrieval and
state changes in the working tree. Both runs use the same 200 public samples,
catalog, local semantic backend, frozen LambdaMART bundle and candidate trace
limit. LLM calls are disabled, so this is a deterministic controlled A/B of the
retrieval, state, dialogue-facet and ranking pipeline.

## Result

| Metric | `final` baseline | Stage 1–2 | Absolute change |
|---|---:|---:|---:|
| Hit@10 | 0.920000 | **0.990000** | **+0.070000** |
| MRR | 0.478147 | **0.539127** | **+0.060980** |
| MTTC (lower is better) | 2.875000 | **2.220000** | **-0.655000** |
| Efficiency | 0.812500 | **0.878000** | **+0.065500** |
| Technical score | 0.765944 | **0.832338** | **+0.066394** |

Technical score improved by 8.67% relative. Buying, browsing and
intent-override scenarios each reached 1.0 Hit@10. The two remaining misses are
boundary samples `public_0180` and `public_0187`; neither is a new regression.

| Scenario | Hit@10 baseline | Hit@10 Stage 1–2 | MRR baseline | MRR Stage 1–2 | MTTC baseline | MTTC Stage 1–2 |
|---|---:|---:|---:|---:|---:|---:|
| boundary | 0.8000 | 0.8000 | 0.547619 | 0.545833 | 3.8000 | 3.6000 |
| browsing | 0.9000 | **1.0000** | 0.436458 | **0.519395** | 3.0125 | **2.1125** |
| buying | 0.9625 | **1.0000** | 0.484172 | **0.546394** | 2.0125 | **1.5500** |
| intent override | 0.9000 | **1.0000** | 0.550093 | **0.570132** | 4.5000 | **3.8333** |

## Implemented architecture

1. **Canonical conversational state.** A DeepSeek semantic rewrite remains the
   fluent query, while missing active category/constraint values are appended
   deterministically. Explicit `reset_scope=all|soft|none` distinguishes a full
   restart, preference retirement and same-field correction.
2. **Closed question-to-retrieval loop.** Long protocol answers such as
   `For that, what matters is: ...` are bound to the pending facet instead of
   being discarded. Care instructions such as `no bleach` are not misread as
   hard product exclusions.
3. **Expanded structured facets.** The attribute route and information-gain
   policy now cover controlled closure, pattern, property, fit, occasion and
   size values through the allowed `feature`/`size` schema.
4. **Dynamic per-turn policy.** Buying, browsing and uncertain turns receive
   different route budgets. Constraint reliability and structured specificity
   can increase attribute weight. Candidate depth expands from a fixed 500 to
   625/650 when recall matters, while the frozen LambdaMART model still owns
   final precision.
5. **Observable funnel.** Every fusion trace records per-route counts, union,
   multi-route agreement, pairwise Jaccard overlap and fused count. Decisions
   are target-independent and reproducible in production.

## Reproduce

```bash
uv sync --extra ltr --group dev
uv run pytest -q
uv run python scripts/evaluate_with_traces.py \
  --no-llm \
  --ltr-model-dir models/lambdamart_synthetic_2000 \
  --ltr-ranker lambdamart \
  --candidate-limit 20 \
  --output-root evaluation_runs/stage12_dynamic_retrieval_offline_200
```

The retained run is
`evaluation_runs/stage12_dynamic_retrieval_offline_200/20260831_183529_+0800`.
Its `summary.json`, `sessions.jsonl`, `turns.jsonl`, `node_traces.jsonl`, ranking
audit and HTML-compatible `trace.json` are the source of the figures above.
Local full traces are intentionally ignored by Git because this run is about
110 MB; this report is the tracked summary.

## Online validation

This A/B proves the non-LLM pipeline improvement without provider variance or
hidden target access. The subsequent 200-sample DeepSeek Pro run also improved
the archived online technical score from 0.812505 to 0.833289. See
`docs/stage12_dynamic_online_pro_report.md` for online metrics, token accounting,
provider-response integrity and nondeterminism limitations.
