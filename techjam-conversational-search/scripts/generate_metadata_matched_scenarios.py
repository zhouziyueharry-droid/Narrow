"""Generate non-official 2K sessions from a metadata-derived expanded catalog.

The public 200 sessions are used only as a distribution template. Their target
ASINs remain excluded from synthetic targets and are reserved for the fixed
official evaluation set.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _price(value: object) -> float | None:
    value = _number(value)
    return value if value is not None and value >= 0 else None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "available": len(values),
        "mean": round(sum(values) / len(values), 6) if values else None,
        "p10": round(_quantile(values, .1), 6) if values else None,
        "median": round(_quantile(values, .5), 6) if values else None,
        "p90": round(_quantile(values, .9), 6) if values else None,
    }


def _metadata_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prices = [value for row in rows if (value := _price(row.get("price"))) is not None]
    ratings = [value for row in rows if (value := _number(row.get("rating_number"))) is not None]
    features = [float(row["feature_count"]) if "feature_count" in row else float(len(row.get("features") or [])) for row in rows]
    return {
        "n": len(rows),
        "price": {**_summary(prices), "missing": len(rows) - len(prices)},
        "rating_number": _summary(ratings),
        "feature_count": _summary(features),
    }


def _catalog_candidates(catalog: Path, excluded: set[str]) -> list[dict[str, Any]]:
    candidates = []
    with catalog.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            identifier = str(row.get("parent_asin") or "").strip()
            rating = _number(row.get("rating_number"))
            if not identifier or identifier in excluded or rating is None or rating < 0:
                continue
            candidates.append({
                "parent_asin": identifier,
                "rating_number": rating,
                "price": _price(row.get("price")),
                "feature_count": len(row.get("features") or []),
            })
    return sorted(candidates, key=lambda row: (row["rating_number"], row["parent_asin"]))


def _price_distance(actual: float | None, desired: float | None) -> float:
    if actual is None or desired is None:
        return 0.0 if actual is desired else 2.0
    return min(abs(actual - desired) / 30, 4.0)


def select_targets(
    candidates: list[dict[str, Any]], reference_targets: list[dict[str, Any]], *, seed: int,
) -> tuple[list[str], dict[str, Any]]:
    """Distribution-match rating_number first, then price/features with diversity."""
    rng = random.Random(seed)
    assignments = list(reference_targets)
    rng.shuffle(assignments)
    ratings = [row["rating_number"] for row in candidates]
    usage: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    for reference in assignments:
        desired_rating = reference["rating_number"]
        index = bisect.bisect_left(ratings, desired_rating)
        nearby = candidates[max(0, index - 60):min(len(candidates), index + 60)]
        # Price availability is a distributional property of the official-200
        # targets, so preserve it exactly before using price as a tie-break.
        availability_matched = [
            row for row in nearby
            if (row["price"] is None) == (reference["price"] is None)
        ]
        if availability_matched:
            nearby = availability_matched
        fewest = min(usage[row["parent_asin"]] for row in nearby)
        options = [row for row in nearby if usage[row["parent_asin"]] == fewest]
        selected_row = min(
            options,
            key=lambda row: (
                abs(math.log1p(row["rating_number"]) - math.log1p(desired_rating)),
                _price_distance(row["price"], reference["price"]),
                abs(row["feature_count"] - reference["feature_count"]) / 5,
                row["parent_asin"],
            ),
        )
        selected.append(selected_row)
        usage[selected_row["parent_asin"]] += 1

    # Exact mean calibration needs a few high-rating repeats because the raw
    # catalog is finite. Change only the upper half so the matched median stays
    # stable, and cap individual repeats to retain useful target diversity.
    desired_total = round(sum(row["rating_number"] for row in assignments))
    remaining = desired_total - round(sum(row["rating_number"] for row in selected))
    maximum_occurrences = max(1, len(assignments) // 33)
    high_candidates = candidates[-200:]
    ranked = sorted(range(len(selected)), key=lambda index: selected[index]["rating_number"])
    for index in reversed(ranked[len(selected) // 2 + 1:]):
        if remaining <= 0:
            break
        old = selected[index]
        choices = [
            candidate for candidate in high_candidates
            if 0 < candidate["rating_number"] - old["rating_number"] <= remaining
            and usage[candidate["parent_asin"]] < maximum_occurrences
        ]
        if not choices:
            continue
        replacement = max(choices, key=lambda candidate: candidate["rating_number"] - old["rating_number"])
        usage[old["parent_asin"]] -= 1
        usage[replacement["parent_asin"]] += 1
        selected[index] = replacement
        remaining -= round(replacement["rating_number"] - old["rating_number"])

    target_ids = [row["parent_asin"] for row in selected]
    values = [row["rating_number"] for row in selected]
    reference_values = [row["rating_number"] for row in assignments]
    return target_ids, {
        "rating_number": {
            "reference": _summary(reference_values),
            "selected": _summary(values),
            "mean_total_residual": remaining,
        },
        "unique_targets": sum(value > 0 for value in usage.values()),
        "max_target_occurrences": max(usage.values()),
    }


def generate(*, catalog: Path, reference_catalog: Path, public_sessions: Path, output: Path,
             manifest: Path, count: int, seed: int, sample_prefix: str) -> dict[str, Any]:
    if output.exists() or manifest.exists():
        raise FileExistsError("output and manifest must not already exist")
    public = _load_jsonl(public_sessions)
    reference_products = {str(row["parent_asin"]): row for row in _load_jsonl(reference_catalog)}
    public_targets = [str(row["ground_truth"]["parent_asin"]) for row in public]
    if count % len(public):
        raise ValueError("count must be an integer multiple of public session count")
    reference_pairs = []
    for repeat in range(count // len(public)):
        for sample in public:
            identifier = str(sample["ground_truth"]["parent_asin"])
            product = reference_products[identifier]
            reference_pairs.append({
                "sample": sample,
                "rating_number": _number(product.get("rating_number")),
                "price": _price(product.get("price")),
                "feature_count": len(product.get("features") or []),
            })
    candidates = _catalog_candidates(catalog, set(public_targets))
    target_ids, selection = select_targets(candidates, reference_pairs, seed=seed)
    rng = random.Random(seed)
    paired = list(zip(reference_pairs, target_ids))
    rng.shuffle(paired)
    rows = []
    for ordinal, (reference, identifier) in enumerate(paired, start=1):
        sample = reference["sample"]
        rows.append({
            "sample_id": f"{sample_prefix}_{ordinal:05d}",
            "scenario_type": sample["scenario_type"],
            "user_profile": sample["user_profile"],
            "ground_truth": {"parent_asin": identifier},
            "category_bucket": sample.get("category_bucket", "clothing"),
            "difficulty_bucket": sample.get("difficulty_bucket", "synthetic"),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    selected_products = {row["parent_asin"]: row for row in candidates}
    target_product_rows = [selected_products[row["ground_truth"]["parent_asin"]] for row in rows]
    reference_product_rows = [reference_products[identifier] for identifier in public_targets]
    occurrences = Counter(row["ground_truth"]["parent_asin"] for row in rows)
    result = {
        "schema_version": "1.0",
        "official_metric_contract": False,
        "purpose": "Non-official training sessions sampled from raw-metadata-derived 500K catalog; official public-200 remains test-only.",
        "source_catalog": {"path": str(catalog), "sha256": _sha256(catalog)},
        "reference": {"official_public_sessions": str(public_sessions), "sessions_sha256": _sha256(public_sessions),
                      "official_catalog": str(reference_catalog), "catalog_sha256": _sha256(reference_catalog),
                      "target_product_stats": _metadata_stats(reference_product_rows)},
        "selection": {"seed": seed, "count": count, "strategy": "rating-number matched with price/features tie-break and diversity cap", **selection},
        "output": {"path": str(output), "sha256": _sha256(output), "bytes": output.stat().st_size,
                   "scenario_distribution": dict(sorted(Counter(row["scenario_type"] for row in rows).items())),
                   "difficulty_distribution": dict(sorted(Counter(row["difficulty_bucket"] for row in rows).items())),
                   "unique_user_profiles": len({json.dumps(row["user_profile"], sort_keys=True) for row in rows}),
                   "target_product_stats": _metadata_stats(target_product_rows),
                   "unique_targets": len(occurrences), "target_occurrence_min": min(occurrences.values()),
                   "target_occurrence_max": max(occurrences.values()),
                   "official_target_overlap_rows": sum(identifier in set(public_targets) for identifier in occurrences)},
        "model_usage": {"agent_llm": "not_used_for_data_generation", "user_llm": "not_used_for_data_generation",
                        "api_calls": 0, "tokens": 0, "cost": 0},
    }
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--reference-catalog", type=Path, required=True)
    parser.add_argument("--public-sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--sample-prefix", default="rawmeta500k_2k")
    args = parser.parse_args()
    result = generate(catalog=args.catalog.resolve(), reference_catalog=args.reference_catalog.resolve(),
                      public_sessions=args.public_sessions.resolve(), output=args.output.resolve(),
                      manifest=args.manifest.resolve(), count=args.count, seed=args.seed,
                      sample_prefix=args.sample_prefix)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
