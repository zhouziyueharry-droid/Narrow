# Competition Data

## `public_set.jsonl`

Contains 200 labeled development sessions: 80 Buying, 80 Browsing, 30 Intent Override, and 10 Boundary sessions.

Each session contains a safe aggregate `user_profile` and public labels for local development. Direct user identifiers, timestamps, free-text reviews, raw purchase history, hidden intent cards, and simulator-policy internals are not shipped in this participant file.

## `catalog.jsonl`

Download `catalog.jsonl.gz` from the GitHub Release and decompress it as `catalog.jsonl` in this directory. Expected row count: 50,000.

Never place API keys, private evaluation data, or participant outputs in this directory.

## Local metadata-derived scale artifacts

`data/metadata_derived/` is Git-ignored. It is for reproducible local or
Release artifacts, never for an official TechJam submission. The intended pair
is a 500K catalog sampled directly from Amazon Reviews 2023
`Clothing_Shoes_and_Jewelry` metadata and 2K non-official training sessions.

```text
python scripts/build_metadata_stratified_catalog.py --source-metadata <meta_Clothing_Shoes_and_Jewelry.jsonl> --reference-catalog data/catalog.jsonl --official-sessions data/public_set.jsonl --output data/metadata_derived/raw_metadata_clothing_500k.jsonl --manifest data/metadata_derived/raw_metadata_clothing_500k_manifest.json --target-count 500000
python scripts/generate_metadata_matched_scenarios.py --catalog data/metadata_derived/raw_metadata_clothing_500k.jsonl --reference-catalog data/catalog.jsonl --public-sessions data/public_set.jsonl --output data/metadata_derived/raw_metadata_clothing_500k_sessions_2000.jsonl --manifest data/metadata_derived/raw_metadata_clothing_500k_sessions_2000_manifest.json --count 2000
```

The catalog is sampled to reproduce the official 50K product distribution at
10x scale; the sessions reproduce the public-200 target and scenario
distribution. `public_set.jsonl` remains fixed and test-only. Running public
sessions against the 500K catalog is an expanded-catalog stress test, not an
official TechJam score.
