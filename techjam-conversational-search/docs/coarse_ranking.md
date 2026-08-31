# Integrated Multi-Route Coarse-Ranking Pipeline

`shopping_agent.retrieval.coarse.CoarseRanker` is both independently evaluable
and wired into the production LangGraph between the three parallel retrieval
nodes and `PreciseReranker`. Existing graph node names remain unchanged so old
trace/report tooling continues to work.

## Pipeline

1. Field-weighted SQLite FTS5 retrieval.
2. Replaceable semantic retrieval (`LocalDenseIndex` or
   `SentenceTransformerDenseIndex`).
3. Structured attribute retrieval.
4. Intent-dependent weighted reciprocal-rank fusion.
5. Three-state constraint evaluation: `match`, `violate`, `unknown`.
6. Reliable hard-constraint filtering and soft-preference boosting.
7. Optional light category-aware diversification for browsing requests only.

Missing catalog metadata is `unknown`, not a violation. A candidate is removed
only when reliable evidence contradicts a hard constraint.

Browsing diversification is implemented but disabled by default at the coarse
Top-100 boundary. On the 200-session public trace it preserved Recall@100 but
reduced Hit@10 from 0.450 to 0.415 and MRR@100 from 0.255 to 0.250. It is more
appropriate for a final display list or clarification UI than for the candidate
pool handed to a precise ranker.

## Install the real embedding backend

```bash
uv sync --extra retrieval
```

The default model is `BAAI/bge-small-en-v1.5`. Embeddings are normalized and
cached under `.cache/coarse_retrieval`. Exact NumPy dot product is the default
for the 50k catalog; pass `--faiss` to the evaluation script to use FAISS
`IndexFlatIP`. Both are exact and therefore have identical recall. Product encoding is capped at 192
tokens so long catalog descriptions do not dominate startup cost or truncate
the title/category/brand prefix.

Enable it in the full application with:

```bash
SHOPPING_DENSE_BACKEND=bge uv run python scripts/evaluate_with_traces.py --no-llm
```

`SHOPPING_DENSE_BACKEND=local` remains the dependency-light default. The BGE
backend and its cache/model/use-FAISS options are documented in `.env.example`.

## Evaluate

The evaluator consumes existing `turns.jsonl` traces, letting it measure the
coarse candidate rank against the exact target ASIN without invoking an LLM:

```bash
uv run python scripts/evaluate_coarse_ranker.py \
  --turns evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/turns.jsonl \
  --backend local \
  --output evaluation_runs/coarse_local.json
```

For BGE + FAISS:

```bash
uv run --extra retrieval python scripts/evaluate_coarse_ranker.py \
  --turns evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/turns.jsonl \
  --backend sentence-transformer \
  --output evaluation_runs/coarse_bge_small.json
```

The report includes lexical-only, fixed hybrid, dynamic hybrid without
diversification, full dynamic policy, and no-constraint ablations. Internal
Recall@50/100 is the primary coarse-ranking metric; official Hit@10 and MRR are
still determined by the downstream precise ranker and final recommendations.

## Measured public-trace results

The figures below describe historical traces retained in Git history at `0635afa`.
The commands above now use the retained LambdaMART Pro trace and will not reproduce
these historical scores.

First-turn requests from the existing 200-session traced evaluator run were
replayed without calling an LLM. Exact target ASIN rank was measured inside the
coarse Top-100 pool.

| Configuration | Hit@10 | Recall@50 | Recall@100 | MRR@100 |
|---|---:|---:|---:|---:|
| Lexical only | 0.225 | 0.440 | 0.585 | 0.142 |
| Fixed hybrid, BGE | 0.415 | 0.715 | **0.860** | 0.223 |
| Dynamic routes, BGE | **0.450** | **0.750** | 0.840 | **0.255** |
| Dynamic + browsing diversity | 0.415 | 0.695 | 0.840 | 0.250 |

The dynamic policy prioritizes useful early ranking and improves Hit@10 by 3.5
points over fixed hybrid. Fixed hybrid retains a 2-point Recall@100 advantage;
that trade-off should be revisited with private-like or cross-validation traces
before changing the route weights further.

## Full end-to-end result

The integrated graph was run locally over all 200 public sessions with BGE,
deterministic understanding/dialogue fallback, and full node checkpoint traces.
It executed 893 conversational turns with zero runtime errors.

| Metric | Result |
|---|---:|
| Hit Rate@10 | 0.785 |
| MRR | 0.328532 |
| MTTC | 4.68 |
| Efficiency | 0.632 |
| TechnicalScore | 0.61746 |
| Mean turn latency | 108 ms |
| P95 turn latency | 305 ms |

The historical run was
`evaluation_runs/integrated_bge_200/20260829_223143_+0800/`; its artifacts have
been removed from final and can be consulted in Git history at `0635afa`. These numbers do
not include LLM calls; they isolate the integrated retrieval/ranking/dialogue
code path and should not be compared as a controlled before/after result to an
LLM-enabled run.
