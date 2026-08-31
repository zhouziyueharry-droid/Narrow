"""Generate additional training scenarios in the same shape as
data/public_set.jsonl, drawn from the full 50k-product catalog instead of
the 200 official samples.

Why this exists: PreciseReranker's weights are fitted from evaluator
sessions (see fit_precise_reranker_weights.py), and the official public set
only has 200 labeled scenarios (100 of which are held out as a clean
validation set -- see docs/precise_reranker_change_report.md section 9).
evaluator/local_evaluator.py's own scenario machinery
(intent_card()/behavior_for()/materialize_hidden_fields()) needs almost
nothing to synthesize a new, fully valid scenario: just a target
parent_asin, a scenario_type, a sample_id, and a user_profile dict -- the
intent card and behavior are then derived deterministically from the target
product's own text. So in principle the entire 50k-product catalog can be
turned into more (target, scenario_type, profile) training scenarios with no
format-adaptation work at all.

The catch (found the hard way -- see docs/precise_reranker_change_report.md
section "V4/合成数据"): picking targets uniformly at random from the catalog
does NOT reproduce the official set's distribution and made the fitted
weights *worse*, not better. The official 200 targets are a heavily
filtered slice of the catalog:

  - 89.0% have a price (vs 21.1% catalog-wide)
  - features count median 8 (vs 5 catalog-wide)
  - rating_number median 6846 (vs 12 catalog-wide -- i.e. official targets
    are roughly the top 1-2% most-reviewed products, not random ones)
  - price range roughly $5-90 (median ~$24.5)

This script reproduces that filter (tunable via CLI flags) before sampling,
which is what made the second attempt actually improve the fitted weights
(see the change report for the before/after numbers).

Usage (from techjam-conversational-search/):

    PYTHONPATH=".:src" python3 scripts/generate_synthetic_scenarios.py \
        --catalog data/catalog.jsonl --dataset data/public_set.jsonl \
        --count 500 --seed 20260829 \
        --output data/synthetic_scenarios_500.jsonl

Then feed the output into fit_precise_reranker_weights.py's --extra-dataset
flag to fit on official + synthetic scenarios together.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from evaluator.local_evaluator import catalog_index, load_jsonl  # noqa: E402

# Official scenario_type ratio, from data/public_set.jsonl (80/80/30/10 out of 200).
OFFICIAL_SCENARIO_WEIGHTS = {
    "buying": 40,
    "browsing": 40,
    "intent_override": 15,
    "boundary": 5,
}


def _price(product: dict) -> float | None:
    value = product.get("price")
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value


def qualifying_products(
    products: dict[str, dict],
    *,
    min_features: int,
    min_rating_number: int,
    price_min: float,
    price_max: float,
) -> list[str]:
    result = []
    for asin, product in products.items():
        price = _price(product)
        if price is None or not (price_min <= price <= price_max):
            continue
        if len(product.get("features") or []) < min_features:
            continue
        if (product.get("rating_number") or 0) < min_rating_number:
            continue
        result.append(asin)
    return result


def generate(
    *,
    catalog_path: str,
    dataset_path: str,
    count: int,
    seed: int,
    min_features: int,
    min_rating_number: int,
    price_min: float,
    price_max: float,
    exclude_official_targets: bool = True,
    sample_prefix: str = "synth",
) -> list[dict]:
    _catalog_ids, _categories, products = catalog_index(catalog_path)
    official = load_jsonl(dataset_path)
    profile_pool = [sample["user_profile"] for sample in official]

    pool = qualifying_products(
        products,
        min_features=min_features,
        min_rating_number=min_rating_number,
        price_min=price_min,
        price_max=price_max,
    )
    official_targets = {
        sample["ground_truth"]["parent_asin"]
        for sample in official
    }
    if exclude_official_targets:
        pool = [asin for asin in pool if asin not in official_targets]
    if not pool:
        raise SystemExit("no products satisfy the filter -- loosen --min-features/--min-rating-number/--price-*")
    print(
        f"eligible target pool: {len(pool)} / {len(products)} catalog products "
        f"(official targets excluded={exclude_official_targets})",
        file=sys.stderr,
    )

    rng = random.Random(seed)
    # Cover every eligible target once before repeating any target. This keeps
    # larger datasets from collapsing onto a small random subset of products.
    target_schedule = []
    while len(target_schedule) < count:
        cycle = list(pool)
        rng.shuffle(cycle)
        target_schedule.extend(cycle)
    target_schedule = target_schedule[:count]

    # Largest-remainder allocation preserves the official distribution for
    # arbitrary counts and is exact whenever count is divisible by 100.
    raw_counts = {
        scenario: count * weight / 100
        for scenario, weight in OFFICIAL_SCENARIO_WEIGHTS.items()
    }
    scenario_counts = {scenario: int(value) for scenario, value in raw_counts.items()}
    remainder = count - sum(scenario_counts.values())
    for scenario in sorted(
        raw_counts,
        key=lambda item: (-(raw_counts[item] - scenario_counts[item]), item),
    )[:remainder]:
        scenario_counts[scenario] += 1
    scenario_schedule = [
        scenario
        for scenario, scenario_count in scenario_counts.items()
        for _ in range(scenario_count)
    ]
    rng.shuffle(scenario_schedule)

    samples = []
    for i, (target, scenario_type) in enumerate(
        zip(target_schedule, scenario_schedule, strict=True),
        1,
    ):
        samples.append({
            "sample_id": f"{sample_prefix}_{i:05d}",
            "scenario_type": scenario_type,
            "user_profile": rng.choice(profile_pool),
            "ground_truth": {"parent_asin": target},
            "category_bucket": "clothing",
            "difficulty_bucket": "synthetic",
        })
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl", help="source of the user_profile pool and scenario_type ratio")
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--min-features", type=int, default=6)
    parser.add_argument("--min-rating-number", type=int, default=1000)
    parser.add_argument("--price-min", type=float, default=5.0)
    parser.add_argument("--price-max", type=float, default=90.0)
    parser.add_argument("--sample-prefix", default="synth")
    parser.add_argument(
        "--allow-official-targets",
        action="store_true",
        help="allow targets from the official public set (disabled by default to prevent leakage)",
    )
    parser.add_argument("--output", default="data/synthetic_scenarios.jsonl")
    args = parser.parse_args()

    samples = generate(
        catalog_path=args.catalog, dataset_path=args.dataset, count=args.count, seed=args.seed,
        min_features=args.min_features, min_rating_number=args.min_rating_number,
        price_min=args.price_min, price_max=args.price_max,
        exclude_official_targets=not args.allow_official_targets,
        sample_prefix=args.sample_prefix,
    )
    with open(args.output, "w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample) + "\n")
    print(f"scenario_type distribution: {Counter(s['scenario_type'] for s in samples)}", file=sys.stderr)
    print(f"unique targets used: {len(set(s['ground_truth']['parent_asin'] for s in samples))}", file=sys.stderr)
    print(f"wrote {len(samples)} samples to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
