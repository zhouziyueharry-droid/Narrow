# LambdaMART 5K / Official-200 Experiment

This folder is the compact, auditable package for SLURM job `32991`. The job completed successfully on CCDS TC2 with `State=COMPLETED`, `ExitCode=0`, and a wall time of `01:18:55`. It trained on 4,003 synthetic sessions, selected the iteration count on 997 synthetic validation sessions, and evaluated once on the official 200-session TechJam public set.

The new 5K LambdaMART model improves over the current Precise baseline on the official-200 test, but it does **not** improve over the earlier leakage-safe 2K LambdaMART experiment. The repository default remains unchanged (`default_changed=false`).

## Official-200 results

| Reranker | Hit@10 | MRR | MTTC | Technical Score | Median rank latency | P95 rank latency |
|---|---:|---:|---:|---:|---:|---:|
| Precise | 0.875 | 0.4119 | 3.695 | 0.7072 | 40.68 ms | 65.28 ms |
| Same-data linear | 0.910 | 0.4319 | 3.450 | 0.7356 | 40.76 ms | 64.97 ms |
| LambdaMART 5K | 0.900 | 0.4629 | 3.030 | 0.7483 | 42.74 ms | 66.74 ms |

Against Precise, LambdaMART 5K gains `+0.04112` in the paired per-session Technical Score estimate; the 95% bootstrap interval is `[0.01173, 0.07085]`. Against the same-data linear control, the gain is `+0.01271`, but the interval `[-0.01479, 0.03993]` includes zero.

## 2K versus 5K

| LambdaMART experiment | Training / validation sessions | Hit@10 | MRR | MTTC | Technical Score | Frozen NDCG@10 | Best iteration | Median rank latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Earlier 2K source experiment | 1,291 / 291 | 0.920 | 0.4781 | 2.875 | 0.7659 | 0.4911 | 167 | 18.13 ms |
| This 5K experiment | 4,003 / 997 | 0.900 | 0.4629 | 3.030 | 0.7483 | 0.4851 | 85 | 42.74 ms |
| 5K minus 2K | +2,712 / +706 | -0.020 | -0.0152 | +0.155 | -0.0176 | -0.0060 | -82 | +24.61 ms |

The latency values were collected in different runs and environments, so the cross-run latency delta is descriptive, not a controlled speed regression. Within job `32991`, LambdaMART adds about `2.06 ms` to the median rank call relative to Precise.

The larger session count did not improve the official-200 score. The 5K set repeatedly samples a fixed pool of 482 eligible target products, so it adds trajectory volume more than target-product diversity. Synthetic weak labels also identify only the simulator target as positive and are not graded semantic-relevance judgments. These results do not justify replacing the earlier model or changing the default without further analysis.

## Frozen-candidate diagnostics

These metrics keep the candidate lists and dialogue states fixed and only replace the reranker score. They are per-turn diagnostics, not session-level Hit@10.

| Split / reranker | Frozen Hit@10 | Reciprocal rank | NDCG@10 |
|---|---:|---:|---:|
| Validation / Precise | 0.6631 | 0.3454 | 0.4106 |
| Validation / same-data linear | 0.6699 | 0.3546 | 0.4193 |
| Validation / LambdaMART 5K | 0.8406 | 0.5520 | 0.6176 |
| Official-200 / Precise | 0.6011 | 0.3091 | 0.3674 |
| Official-200 / same-data linear | 0.6252 | 0.3188 | 0.3815 |
| Official-200 / LambdaMART 5K | 0.6940 | 0.4305 | 0.4851 |

## Data isolation and reproducibility

- Catalog: 50,000 products, SHA256 `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`.
- Synthetic source: 5,000 sessions, 482 unique eligible targets, SHA256 `25d8d48411a08dee2f35295498a84e6b5edde1fef116db1e89bfe43a1dfd8973`.
- Official public set: 200 sessions / 200 targets, SHA256 `571359a8a69014c43fc30d39c996c4a28e875dccc249dffc707358757beb16c0`.
- Synthetic rows overlapping official targets: `0`.
- Training: 4,003 sessions / 386 unique targets / 11,625 groups / 5,676,583 candidate rows.
- Validation: 997 sessions / 96 unique targets / 2,431 groups / 1,193,734 candidate rows.
- Train-validation target overlap: `0`; both sets exclude every official target.
- Model SHA256: `28e34799afe98b5894ea432beb5e8c3af8cff62a49b3ea2e86ad4135c91f254f`.

The model used 13 existing reranker features. The five largest gain importances were `term_coverage`, `quality`, `rrf_raw`, `category_match`, and `attribute_raw`.

## Runtime and model usage

- Node: `TC2N01`; CPU-only job; 6 CPUs; 24 GiB requested; peak RSS approximately 2.93 GiB.
- Python: 3.12.14; LightGBM: 4.7.0; best iteration: 85.
- Agent LLM: disabled (`SHOPPING_AGENT_ENABLE_LLM=false`).
- User verbalizer: deterministic offline simulator wording; no LLM.
- Dense backend: local (`SHOPPING_DENSE_BACKEND=local`).
- LangSmith and LangChain tracing: disabled.
- API calls: 0; prompt tokens: 0; completion tokens: 0; estimated cost: 0; cost status: `not_applicable_no_api_usage`.
- The experiment aborts if any prompt or completion token usage is observed.

The only stderr entry is a LightGBM 4.7.0 deprecation warning for `eval_set`. It did not affect completion or output integrity; future maintenance should migrate to `eval_X` and `eval_y`.

## Artifact map

- `summary.json`: headline official-200 metrics, split counts, latency, paired comparisons, and model hash.
- `report.md`: raw report generated on TC2.
- `comparison_2k_vs_5k.json`: machine-readable comparison assembled from committed 2K evidence and this run.
- `model/`: deployable LightGBM model, frozen IDF, and metadata.
- `test_frozen_metrics.json`, `validation_frozen.json`: frozen-candidate per-turn diagnostics.
- `*_sessions.json`: compact session outcomes for Precise, same-data linear, and LambdaMART.
- `training_collection_sessions.json`, `validation_collection_sessions.json`: compact collection summaries; large candidate matrices are intentionally excluded.
- `split_manifest.json`: exact session and target split audit.
- `logs/`: complete SLURM stdout and stderr.
- `SHA256SUMS`: checksums for every committed experiment artifact except the checksum file itself.

## Validation contract

These JSON files use the offline LTR experiment schema emitted by `scripts/experiment_lambdamart.py`; they are **not** aggregate simulator reports with the unified top-level sections `evaluation`, `turn_metrics`, `latency`, `model_usage`, `mode_specific_metrics`, and `sessions`. Therefore the `shopping-simulator-evaluation` report validator is intentionally not claimed for these raw files. JSON parsing, session counts, hashes, unit tests, and Git whitespace checks are validated separately.

This is an offline local-simulator result, not a private leaderboard score or evidence of realistic-user performance.
