from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from user_simulator.cli import PRESETS
from user_simulator.datasets import TechJamDatasetAdapter, build_realistic_scenarios


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_path", type=Path)
    parser.add_argument("index_output", type=Path)
    parser.add_argument("summary_output", type=Path)
    parser.add_argument("--preset", default="realistic_broad", choices=PRESETS)
    args = parser.parse_args()

    config = PRESETS[args.preset]
    if config["mode"] != "realistic":
        raise ValueError("scenario export only supports realistic presets")
    difficulty = config["difficulty"]
    dataset = config["dataset"]
    products = list(TechJamDatasetAdapter(args.catalog_path).load_products())
    scenarios = build_realistic_scenarios(
        products,
        count=int(dataset["scenario_count"]),
        seed=int(config["seed"]),
        max_turns=int(config["max_turns"]),
        persona_templates=config["persona"]["templates"],
        persona_driven_override_enabled=bool(
            config["override"]["persona_driven_enabled"]
        ),
        difficulty_profile=str(difficulty["profile"]),
        budget_multiplier=float(difficulty["budget_multiplier"]),
        min_soft_preferences=int(difficulty["min_soft_preferences"]),
        min_soft_matches=int(difficulty["min_soft_matches"]),
        initial_disclosure_policy=str(difficulty["initial_disclosure_policy"]),
        min_turns_before_acceptance=int(
            difficulty["min_turns_before_acceptance"]
        ),
        require_no_pending_question=bool(
            difficulty["require_no_pending_question"]
        ),
        scheduled_variants=bool(difficulty["scheduled_variants"]),
        sampling_strategy=str(dataset["sampling_strategy"]),
        source_dataset=str(dataset["source_dataset"]),
    )

    args.index_output.parent.mkdir(parents=True, exist_ok=True)
    with args.index_output.open("w", encoding="utf-8", newline="\n") as handle:
        for scenario in scenarios:
            handle.write(
                json.dumps(
                    {
                        "scenario_id": scenario.scenario_id,
                        "scenario_type": scenario.scenario_type,
                        "difficulty_profile": scenario.difficulty_profile,
                        "seed": scenario.seed,
                        "seed_product_id": scenario.metadata["seed_product_id"],
                        "coverage": scenario.metadata["coverage"],
                        "persona": scenario.persona_template,
                        "user_profile": scenario.user_profile,
                        "max_turns": scenario.max_turns,
                        "initial_disclosure_policy": (
                            scenario.initial_disclosure_policy
                        ),
                        "min_turns_before_acceptance": (
                            scenario.min_turns_before_acceptance
                        ),
                        "require_no_pending_question": (
                            scenario.require_no_pending_question
                        ),
                        "goal": asdict(scenario.goal),
                        "scheduled_overrides": [
                            asdict(event) for event in scenario.scheduled_overrides
                        ],
                        "scheduled_relaxations": [
                            asdict(event) for event in scenario.scheduled_relaxations
                        ],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )

    categories = Counter(
        str(scenario.metadata["coverage"]["category"]) for scenario in scenarios
    )
    price_bands = Counter(
        str(scenario.metadata["coverage"]["price_band"]) for scenario in scenarios
    )
    signatures = Counter(
        str(scenario.metadata["coverage"]["soft_signature"])
        for scenario in scenarios
    )
    personas = Counter(scenario.persona_template for scenario in scenarios)
    variants = Counter(scenario.scenario_type for scenario in scenarios)
    summary = {
        "schema_version": "1.0",
        "preset": args.preset,
        "source_dataset": dataset["source_dataset"],
        "catalog_path": str(args.catalog_path.resolve()),
        "catalog_products": len(products),
        "scenario_count": len(scenarios),
        "coverage": {
            "unique_categories": len(categories),
            "category_distribution": dict(sorted(categories.items())),
            "price_band_distribution": dict(sorted(price_bands.items())),
            "soft_signature_distribution": dict(sorted(signatures.items())),
            "persona_distribution": dict(sorted(personas.items())),
            "variant_distribution": dict(sorted(variants.items())),
        },
        "official_metric_contract": False,
        "review_data_used": False,
    }
    args.summary_output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
