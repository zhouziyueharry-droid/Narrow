from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

EXPECTED_PRICE_BANDS = {"under_15", "15_30", "30_60", "60_120", "120_plus"}
EXPECTED_VARIANTS = {
    "realistic_broad:hidden_preferences",
    "realistic_broad:preference_override",
    "realistic_broad:budget_relaxation",
    "realistic_broad:override_and_relaxation",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("scenario_index", type=Path)
    parser.add_argument("coverage_summary", type=Path)
    args = parser.parse_args()

    catalog_ids: set[str] = set()
    with args.catalog.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            parent_asin = str(row.get("parent_asin", "")).strip()
            require(bool(parent_asin), f"catalog line {line_number}: missing parent_asin")
            require(parent_asin not in catalog_ids, f"duplicate catalog id: {parent_asin}")
            catalog_ids.add(parent_asin)

    scenarios = [
        json.loads(line)
        for line in args.scenario_index.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require(len(scenarios) == 96, "scenario index must contain 96 scenarios")
    scenario_ids = {scenario["scenario_id"] for scenario in scenarios}
    seed_ids = {scenario["seed_product_id"] for scenario in scenarios}
    require(len(scenario_ids) == 96, "scenario ids must be unique")
    require(len(seed_ids) == 96, "seed product ids must be unique")
    require(seed_ids <= catalog_ids, "every seed product must be present in the catalog")

    categories = Counter(str(item["coverage"]["category"]) for item in scenarios)
    price_bands = Counter(str(item["coverage"]["price_band"]) for item in scenarios)
    signatures = Counter(
        str(item["coverage"]["soft_signature"]) for item in scenarios
    )
    personas = Counter(str(item["persona"]) for item in scenarios)
    variants = Counter(str(item["scenario_type"]) for item in scenarios)
    require(len(categories) >= 90, "broad set must cover at least 90 categories")
    require(set(price_bands) == EXPECTED_PRICE_BANDS, "all price bands are required")
    require(max(price_bands.values()) - min(price_bands.values()) <= 1, "price bands are imbalanced")
    require(len(signatures) >= 10, "at least 10 soft-preference shapes are required")
    require(set(variants) == EXPECTED_VARIANTS, "all broad pressure variants are required")
    require(set(variants.values()) == {24}, "each pressure variant must have 24 sessions")
    require(len(personas) == 8, "all eight personas are required")
    require(set(personas.values()) == {12}, "each persona must have 12 sessions")
    require(
        all(
            item["goal"]["source_dataset"]
            == "amazon_reviews_2023_metadata_broad_v1"
            for item in scenarios
        ),
        "scenario source_dataset is incorrect",
    )

    summary = json.loads(args.coverage_summary.read_text(encoding="utf-8"))
    require(summary["scenario_count"] == len(scenarios), "summary count mismatch")
    require(
        summary["coverage"]["price_band_distribution"]
        == dict(sorted(price_bands.items())),
        "summary price distribution mismatch",
    )
    result = {
        "valid": True,
        "catalog_products": len(catalog_ids),
        "scenarios": len(scenarios),
        "unique_categories": len(categories),
        "price_band_distribution": dict(sorted(price_bands.items())),
        "soft_signature_count": len(signatures),
        "persona_distribution": dict(sorted(personas.items())),
        "variant_distribution": dict(sorted(variants.items())),
        "source_dataset": "amazon_reviews_2023_metadata_broad_v1",
        "official_metric_contract": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
