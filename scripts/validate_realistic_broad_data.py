from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

EXPECTED_PRICE_BANDS = {"under_15", "15_30", "30_60", "60_120", "120_plus"}
EXPECTED_VARIANT_SUFFIXES = {
    "hidden_preferences",
    "preference_override",
    "budget_relaxation",
    "override_and_relaxation",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("scenario_index", type=Path)
    parser.add_argument("coverage_summary", type=Path)
    parser.add_argument("--expected-catalog-products", type=int, default=49_999)
    parser.add_argument("--expected-scenarios", type=int, default=96)
    parser.add_argument("--minimum-categories", type=int, default=90)
    parser.add_argument(
        "--expected-source-dataset",
        default="amazon_reviews_2023_metadata_broad_v1",
    )
    args = parser.parse_args()

    catalog_ids: set[str] = set()
    with args.catalog.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            parent_asin = str(row.get("parent_asin", "")).strip()
            require(bool(parent_asin), f"catalog line {line_number}: missing parent_asin")
            require(parent_asin not in catalog_ids, f"duplicate catalog id: {parent_asin}")
            catalog_ids.add(parent_asin)
    require(
        len(catalog_ids) == args.expected_catalog_products,
        "catalog product count mismatch",
    )

    scenarios = [
        json.loads(line)
        for line in args.scenario_index.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require(
        len(scenarios) == args.expected_scenarios,
        "scenario index count mismatch",
    )
    scenario_ids = {scenario["scenario_id"] for scenario in scenarios}
    seed_ids = {scenario["seed_product_id"] for scenario in scenarios}
    require(len(scenario_ids) == len(scenarios), "scenario ids must be unique")
    require(len(seed_ids) == len(scenarios), "seed product ids must be unique")
    require(seed_ids <= catalog_ids, "every seed product must be present in the catalog")

    categories = Counter(str(item["coverage"]["category"]) for item in scenarios)
    price_bands = Counter(str(item["coverage"]["price_band"]) for item in scenarios)
    signatures = Counter(
        str(item["coverage"]["soft_signature"]) for item in scenarios
    )
    personas = Counter(str(item["persona"]) for item in scenarios)
    variants = Counter(str(item["scenario_type"]) for item in scenarios)
    require(
        len(categories) >= args.minimum_categories,
        "scenario set does not meet the minimum category coverage",
    )
    require(set(price_bands) == EXPECTED_PRICE_BANDS, "all price bands are required")
    require(max(price_bands.values()) - min(price_bands.values()) <= 1, "price bands are imbalanced")
    require(len(signatures) >= 10, "at least 10 soft-preference shapes are required")
    variant_bases = {name.rsplit(":", 1)[0] for name in variants}
    variant_suffixes = {name.rsplit(":", 1)[-1] for name in variants}
    require(len(variant_bases) == 1, "scenario variants must share one mode prefix")
    require(
        variant_suffixes == EXPECTED_VARIANT_SUFFIXES,
        "all four pressure variants are required",
    )
    require(
        set(variants.values()) == {len(scenarios) // 4},
        "pressure variants must be evenly distributed",
    )
    require(len(personas) == 8, "all eight personas are required")
    require(
        set(personas.values()) == {len(scenarios) // 8},
        "personas must be evenly distributed",
    )
    require(
        all(
            item["goal"]["source_dataset"]
            == args.expected_source_dataset
            for item in scenarios
        ),
        "scenario source_dataset is incorrect",
    )

    summary = json.loads(args.coverage_summary.read_text(encoding="utf-8"))
    require(summary["scenario_count"] == len(scenarios), "summary count mismatch")
    require(summary["official_metric_contract"] is False, "summary must be non-official")
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
        "source_dataset": args.expected_source_dataset,
        "official_metric_contract": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
