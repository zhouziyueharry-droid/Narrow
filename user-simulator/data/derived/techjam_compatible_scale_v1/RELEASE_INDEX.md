# Rebuilt Amazon evaluation datasets v2

This bundle contains non-official catalogs reconstructed by this project from
Amazon Reviews 2023 and the corresponding TechJam-compatible session cards.
It does **not** contain the official TechJam Participant Kit catalog or its
official 200-session public set.

## Catalogs

| File | Rows | Meaning |
|---|---:|---|
| `catalogs/rebuilt_amazon_clothing_50k.jsonl` | 50,000 | Project-rebuilt Clothing catalog; not the official Participant Kit 50K |
| `catalogs/rebuilt_amazon_clothing_200k.jsonl` | 200,000 | Project-rebuilt, same-category Clothing scale catalog |
| `catalogs/rebuilt_amazon_broad_500k.jsonl` | 500,000 | Project-rebuilt, broader cross-category catalog |

Exact byte counts, SHA-256 hashes, source composition, and subset invariants are
recorded in `catalogs/catalog_manifest.json`.

## Sessions

| File | Rows | Use |
|---|---:|---|
| `sessions/official_style_smoke_20_rebuilt_amazon_clothing_50k.jsonl` | 20 | Smoke test |
| `sessions/official_style_dev_200_rebuilt_amazon_clothing_50k.jsonl` | 200 | Development and regression |
| `sessions/official_style_core_1000_rebuilt_amazon_clothing_50k.jsonl` | 1,000 | Fixed core targets from rebuilt Clothing 50K |
| `sessions/custom_challenge_200_rebuilt_amazon_clothing_50k.jsonl` | 200 | Custom override and boundary challenge |
| `sessions/official_style_core_1000_rebuilt_amazon_clothing_200k.jsonl` | 1,000 | Targets sampled from rebuilt Clothing 200K |
| `sessions/official_style_core_1000_rebuilt_amazon_broad_500k.jsonl` | 1,000 | Targets sampled from rebuilt broad 500K |

`official_style` means the public scenario/difficulty distribution is followed;
it does not make a session set official. All rebuilt sets use
`official_metric_contract=false`.

## Presets

```text
techjam_rebuilt_amazon_clothing_50k
techjam_rebuilt_amazon_clothing_200k
techjam_rebuilt_amazon_broad_500k
```

The official Participant Kit remains available through the separate `techjam`
preset. Session provenance, file hashes, and the searchable row index are under
`sessions/`.

## Removed legacy names

The bundle intentionally excludes `resampled_50k.jsonl`, `nested_200k.jsonl`,
`nested_500k.jsonl`, `dev_200.jsonl`, `eval_core_1000.jsonl`,
`eval_challenge_200.jsonl`, and `smoke_20.jsonl`. Their replacements encode the
catalog source directly in the filename.
