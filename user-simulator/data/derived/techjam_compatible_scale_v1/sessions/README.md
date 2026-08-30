# TechJam-compatible Scale Sessions v1

These sessions are catalog-derived, non-official evaluation inputs for comparing
the same target tasks across nested 50k, 200k, and 500k product catalogs.

这些会话由重新抽样的 Amazon Reviews 2023 商品元数据构建，用于在嵌套的
50k、200k、500k 商品库上运行相同目标任务。它们不是官方会话，也不能产生
官方成绩。

## Files

- `smoke_20.jsonl`: derived from the development set; 8 Buying, 8 Browsing,
  3 Intent Override, and 1 Boundary session.
- `dev_200.jsonl`: 80 Buying, 80 Browsing, 30 Intent Override, and 10 Boundary
  sessions for development and pilot runs.
- `eval_core_1000.jsonl`: the fixed headline evaluation set with 400 Buying,
  400 Browsing, 150 Intent Override, and 50 Boundary sessions.
- `eval_challenge_200.jsonl`: 100 Intent Override and 100 Boundary sessions;
  report these separately from the core score.
- `session_index.csv`: searchable index for all 1,400 unique sessions.
- `manifest.json`: source hash, generation seed, distributions, and file hashes.

`smoke_20.jsonl` reuses 20 development targets by design. The development,
core, and challenge targets are otherwise mutually exclusive. All 200 official
targets were excluded before sampling.

## Interaction contract

- maximum 10 turns;
- Top-10 recommendations;
- exact `parent_asin` target matching;
- miss value 11 for MTTC;
- deterministic template user policy;
- `official_metric_contract=false`.

Each JSONL record is an interactive goal card, not a fixed transcript. It stores
the hidden target, intent card, user profile, initial disclosure, override or
boundary behavior, and generation provenance. The simulator responds dynamically
to the Agent's questions.

## Rebuild

From the repository root, use an existing repository Python environment:

```powershell
& user-simulator\.venv\Scripts\python.exe scripts\generate_techjam_compatible_sessions.py `
  --catalog integration_runs\realistic_broad_amazon2023_20260829\broad_catalog.jsonl `
  --exclude-sessions techjam-conversational-search\data\public_set.jsonl `
  --output-dir user-simulator\data\derived\techjam_compatible_scale_v1\sessions
```

The source target pool currently contains 49,999 resampled rows. The final 50k
catalog builder must retain all of those rows and add one unique product; the
session targets therefore remain valid after the base catalog is completed to
exactly 50,000 products.

Build the exact nested catalogs separately; the generated JSONL files are
ignored by Git and should be distributed as checksummed Release assets:

```powershell
& user-simulator\.venv\Scripts\python.exe scripts\build_nested_techjam_compatible_catalogs.py `
  --resampled-source integration_runs\realistic_broad_amazon2023_20260829\broad_catalog.jsonl `
  --scale-source integration_runs\realistic_scale_200k_20260829\scale_200k_catalog.jsonl `
  --cross-category-source integration_runs\realistic_cross_category_500k_20260829\cross_category_500k_catalog.jsonl `
  --output-dir user-simulator\data\derived\techjam_compatible_scale_v1\catalogs
```
