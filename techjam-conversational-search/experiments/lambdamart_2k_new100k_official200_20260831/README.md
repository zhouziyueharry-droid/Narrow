# New100K / 2K LambdaMART experiment (2026-08-31)

This directory contains the small, reviewable artifacts from the isolated
LambdaMART experiment. Large candidate matrices, full collection traces, and
local catalogs remain outside Git.

## Isolation and data

- Training catalog: `RawMetadata-New100K` Agent view, 100,000 products,
  SHA-256 `51d12c525b5d90f22709d58d847db65d1f0290a96cc8af3a60329050cb1508e3`.
- Synthetic sessions: 2,000 sessions, SHA-256
  `a3563cb7f78d9b8ea7b4ac41d7219db77c637d3e72b5b8f47b7778cadfeaf35f`.
- Split: 1,570 training sessions and 430 target-disjoint validation sessions.
- Official targets present in the training catalog: **0**.
- The model and training IDF were frozen before the official 50K catalog was
  loaded. The full official public 200 was used only for the final offline A/B.
- Agent LLM and user-verbalizer LLM were not used. API calls, tokens, and cost
  are all zero.

## Official public-200 A/B

| Ranker | Hit@10 | MRR | MTTC | Technical Score | Median rerank latency |
|---|---:|---:|---:|---:|---:|
| Precise | 0.875 | 0.411885 | 3.695 | 0.707166 | 26.12 ms |
| Old LambdaMART | 0.920 | 0.478147 | 2.875 | 0.765944 | 30.31 ms |
| Same-data linear | 0.900 | 0.421125 | 3.515 | 0.726037 | 26.48 ms |
| New LambdaMART | 0.920 | 0.533018 | 2.855 | 0.782805 | 28.37 ms |

Against the old LambdaMART, the new model changes MRR by `+0.054871`,
Hit@10 by `0.000`, and Technical Score by `+0.0168613`. It therefore passes
all proposed acceptance gates and the experiment recommends merging the model
subject to code review. The paired Technical Score difference has a 95% local
bootstrap interval of `[-0.00294, 0.03664]`, so the average improvement is not
statistically decisive on only 200 public sessions.

## Artifacts

- `model/`: model, frozen training IDF, and metadata.
- `config.json`: input hashes, runtime, zero-LLM declaration, and selection rule.
- `summary.json`: headline metrics, paired comparisons, latency, and acceptance.
- `validation_frozen.json`: synthetic held-out frozen-candidate metrics.
- `test_frozen_metrics.json`: public-200 frozen-candidate diagnostics.
- `feature_importance.json`: LightGBM gain importance.
- `report.md` / `report_en.md`: Chinese and English reports.

These JSON files use the LambdaMART experiment schema, not the unified
shopping-simulator report schema. They must not be claimed as passing the
shopping-simulator schema validator. The full raw run is retained locally at
`D:\projects\tiktok26\rawmetadata100k-runs\lambdamart_2k_20260831\full_new100k_2k_official200`.
