# Integrated LambdaMART 2K / New100K — DeepSeek v4 Pro final-test plan

## Status

This directory records the second, data-compatible attempt after merging the
dynamic retrieval pipeline from `origin/testing` into the experiment branch.
The run stopped after split construction and before candidate collection or
model fitting. No model bundle and no official-test result were produced.

The first attempt is recorded separately in the parent experiment history: it
used the old `synthetic_scenarios_2000.jsonl`, whose targets were not contained
in the New100K catalog, and was rejected by the catalog-integrity guard.

## Code and branch

- Branch: `experiment/final-rawmetadata500k-2k-20260831`
- Integrated code commit: `4a4f092` (`merge: integrate testing dynamic retrieval pipeline`)
- Training script: `scripts/experiment_lambdamart.py`
- Runtime: Python 3.12.13, LightGBM 4.7.0, NumPy 2.5.2, scikit-learn 1.9.0
- Dense retrieval backend: local

## Product catalog

Training and validation use `data/metadata_derived/raw_metadata_new100k_agent_catalog.jsonl`.
It is the agent-normalized catalog derived from the RawMetadata-New100K sample,
which was selected from the 500K Clothing, Shoes & Jewelry metadata source by
joint-stratified sampling (price band, log rating-count quantile, and feature
count). The catalog contains 100,000 products and excludes all official public
200 target ASINs.

The final official test uses the isolated official catalog
`data/catalog.jsonl` (the official 50K catalog). It is loaded only after the
LambdaMART model and training IDF are frozen.

## Session construction

Training sessions use
`data/metadata_derived/raw_metadata_clothing_500k_sessions_2000.jsonl`:
2,000 non-official sessions constructed by repeating the official 200-session
scenario distribution and matching target-product rating-count statistics,
with price and feature-count tie-breaks and a diversity cap. The 2,000 rows
contain 1,536 unique targets, preserve the Buying/Browsing/Intent Override/
Boundary distribution, and have zero overlap with official public targets.
They are simulator-generated structured sessions, not LLM-generated dialogue.

## Planned training and evaluation protocol

1. Group the 2,000 sessions by target and split into 1,621 training sessions
   and 379 validation sessions (`seed=20260830`, validation fraction 0.2).
2. Collect PreciseReranker trajectories on the training catalog and fit the
   13-feature LambdaMART ranker. Early stopping selects validation NDCG@1
   first and NDCG@10 second; the official 200 is never used for selection.
3. Freeze the model, IDF, and feature configuration.
4. Load the official 50K catalog and evaluate the official 200 sessions with
   the same frozen ranker and comparison rankers.
5. For the final online pass, set `SHOPPING_AGENT_ENABLE_LLM=true`,
   `DEEPSEEK_MODEL=deepseek-v4-pro`, and use the configured
   `DEEPSEEK_API_KEY` only in the runtime environment. The key must not be
   committed or written to logs. The online report must record per-turn Agent
   and user-generation latency, API calls, reported tokens, retries/errors,
   and cost status.

Training is explicitly offline (`llm_calls=0`, `llm_tokens=0`, `llm_cost=0`).
The online DeepSeek v4 Pro calls are restricted to the final official-200
evaluation and must be reported separately from training metrics.

## Parameters

See `run_parameters.json` for the exact reproducibility configuration and
`config.json` / `split_manifest.json` for the parameters captured before the
run stopped.

## Observed verification

After the code merge, the relevant unit-test set passed: **15 passed**.
`git diff --check` reported no whitespace errors. This is a code verification
result, not a completed LambdaMART or official-test result.
