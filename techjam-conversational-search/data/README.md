# Competition Data

## `public_set.jsonl`

Contains 200 labeled development sessions: 80 Buying, 80 Browsing, 30 Intent Override, and 10 Boundary sessions.

Each session contains a safe aggregate `user_profile` and public labels for local development. Direct user identifiers, timestamps, free-text reviews, raw purchase history, hidden intent cards, and simulator-policy internals are not shipped in this participant file.

## `catalog.jsonl`

Download `catalog.jsonl.gz` from the GitHub Release and decompress it as `catalog.jsonl` in this directory. Expected row count: 50,000.

Never place API keys, private evaluation data, or participant outputs in this directory.

## Local metadata-derived scale artifacts

`data/metadata_derived/` is Git-ignored. It is for reproducible local or
Release artifacts, never for an official TechJam submission. The 500K catalog
is sampled directly from Amazon Reviews 2023 `Clothing_Shoes_and_Jewelry`
metadata. `RawMetadata-New100K` is a smaller training view sampled from that
500K mother catalog while retaining all targets used by the 2K non-official
training sessions and the public 200 compatibility set.

```text
python scripts/build_metadata_stratified_catalog.py --source-metadata <meta_Clothing_Shoes_and_Jewelry.jsonl> --reference-catalog data/catalog.jsonl --official-sessions data/public_set.jsonl --output data/metadata_derived/raw_metadata_clothing_500k.jsonl --manifest data/metadata_derived/raw_metadata_clothing_500k_manifest.json --target-count 500000
python scripts/generate_metadata_matched_scenarios.py --catalog data/metadata_derived/raw_metadata_clothing_500k.jsonl --reference-catalog data/catalog.jsonl --public-sessions data/public_set.jsonl --output data/metadata_derived/raw_metadata_clothing_500k_sessions_2000.jsonl --manifest data/metadata_derived/raw_metadata_clothing_500k_sessions_2000_manifest.json --count 2000
python scripts/build_metadata_stratified_catalog.py --source-metadata data/metadata_derived/raw_metadata_clothing_500k.jsonl --reference-catalog data/catalog.jsonl --official-sessions data/public_set.jsonl --additional-mandatory-sessions data/metadata_derived/raw_metadata_clothing_500k_sessions_2000.jsonl --exclude-official-targets --output data/metadata_derived/raw_metadata_new100k.jsonl --manifest data/metadata_derived/raw_metadata_new100k_manifest.json --target-count 100000
python scripts/normalize_metadata_catalog_for_agent.py --source data/metadata_derived/raw_metadata_new100k.jsonl --output data/metadata_derived/raw_metadata_new100k_agent_catalog.jsonl --manifest data/metadata_derived/raw_metadata_new100k_agent_catalog_manifest.json
```

The 500K and 100K catalogs reproduce the official 50K product distribution at
10x and 2x scale respectively; the sessions reproduce the public-200 target and
scenario distribution. The 100K training view excludes all public-200 target
ASINs to keep catalog/IDF construction isolated from the final test.
`public_set.jsonl` remains fixed and test-only. Running
public sessions against either derived catalog is an expanded-catalog stress
test, not an official TechJam score.
