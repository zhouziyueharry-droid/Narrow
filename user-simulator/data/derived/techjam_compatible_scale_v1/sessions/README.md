# TechJam-compatible Scale Sessions v1

These sessions are catalog-derived, non-official evaluation inputs for comparing
the same target tasks across rebuilt Amazon 50k, 200k, and 500k product catalogs.

这些会话由重新抽样的 Amazon Reviews 2023 商品元数据构建，用于在嵌套的
50k、200k、500k 商品库上运行相同目标任务。这里的 50K 是本项目重构的
Amazon Clothing 50K，不是 Participant Kit 的官方原始 50K。它们不是官方会话，也不能产生
官方成绩。

## Naming and source boundary

| Artifact | Size | Source | Official? |
|---|---:|---|---|
| `techjam-conversational-search/data/catalog.jsonl` | 50,000 products | TechJam Participant Kit | Yes |
| `techjam-conversational-search/data/public_set.jsonl` | 200 sessions | TechJam Participant Kit | Yes |
| `catalogs/rebuilt_amazon_clothing_50k.jsonl` | 50,000 products | Our Amazon Reviews 2023 Clothing reconstruction | No |
| `catalogs/rebuilt_amazon_clothing_200k.jsonl` | 200,000 products | Our Amazon Reviews 2023 Clothing reconstruction | No |
| `catalogs/rebuilt_amazon_broad_500k.jsonl` | 500,000 products | Our cross-category Amazon Reviews 2023 reconstruction | No |

Prefixes are contractual: `official_participant_*` means an official Participant
Kit artifact; `rebuilt_amazon_*` means a catalog reconstructed by this project;
`official_style_*` means only that the scenario distribution follows the public
format and never means an official benchmark set.

## Files

- `official_style_smoke_20_rebuilt_amazon_clothing_50k.jsonl`: derived from the official-style development set; 8 Buying, 8 Browsing,
  3 Intent Override, and 1 Boundary session.
- `official_style_dev_200_rebuilt_amazon_clothing_50k.jsonl`: an independent official-style development set
  with 80 Easy Buying, 80 Medium Browsing, 30 Hard Intent Override, and 10
  Medium Boundary sessions. Use it for development and pilot runs, not the
  headline score.
- `official_style_core_1000_rebuilt_amazon_clothing_50k.jsonl`: the official-style headline evaluation set. It is an
  exact 5x scaling of the public-set distribution: 400 Easy Buying, 400 Medium
  Browsing, 150 Hard Intent Override, and 50 Medium Boundary sessions. These
  rows omit custom hidden intent/behavior fields so the participant-compatible
  deterministic materializer constructs them at runtime.
- `custom_challenge_200_rebuilt_amazon_clothing_50k.jsonl`: 100 Intent Override and 100 Boundary sessions;
  these are the 200 custom sessions and must be reported separately from the
  core score.
- `official_style_core_1000_rebuilt_amazon_broad_500k.jsonl`: an additional official-style Core sampled
  from the full nested 500k catalog. It intentionally allows overlap with the
  existing 1,400 generated sessions and broadens target-category coverage. It
  is a 500k-specific distribution test, not part of the nested-catalog headline
  comparison. See `core_1000_500k_manifest.json` for category counts and hashes.
- `official_style_core_1000_rebuilt_amazon_clothing_200k.jsonl`: an official-style Core sampled from
  the full same-source 200k catalog built from Clothing, Shoes & Jewelry
  metadata. It allows overlap with the other generated suites and is intended
  to measure the target distribution available at the 200k same-category
  scale. See `core_1000_200k_manifest.json`.
- `session_index.csv`: searchable index for all 1,400 unique sessions.
- `manifest.json`: source hash, generation seed, distributions, and file hashes.

`official_style_smoke_20_rebuilt_amazon_clothing_50k.jsonl` reuses 20 development targets by design. The development,
core, and challenge targets are otherwise mutually exclusive. All 200 official
targets were excluded before sampling.

## Interaction contract

- maximum 10 turns;
- Top-10 recommendations;
- exact `parent_asin` target matching;
- miss value 11 for MTTC;
- deterministic template user policy;
- `official_metric_contract=false`.

Each JSONL record is an interactive goal card, not a fixed transcript. Core and
development rows store the official-style public fields and generation provenance;
the participant materializer derives their hidden intent card and behavior. Custom rows may also
store explicit intent cards and extended override or boundary behavior. The
simulator responds dynamically to the Agent's questions.

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
