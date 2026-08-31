"""Build a local metadata-derived expanded catalog that mirrors a reference catalog.

The source is streamed twice: first for deterministic stratified reservoir
sampling, then to materialize only selected records. Large source and output
catalogs remain local/release artifacts; this script and its manifest make the
selection reproducible.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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


def _product_id(row: dict[str, Any]) -> str:
    return str(row.get("parent_asin") or "").strip()


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _rating_edges(reference: list[dict[str, Any]]) -> list[float]:
    values = [math.log1p(value) for row in reference if (value := _number(row.get("rating_number"))) is not None and value >= 0]
    if not values:
        raise ValueError("reference catalog has no numeric rating_number")
    return [_quantile(values, fraction) for fraction in (.2, .4, .6, .8)]


def _price_band(value: object) -> str:
    price = _number(value)
    if price is None or price < 0:
        return "missing"
    if price < 15:
        return "under_15"
    if price < 30:
        return "15_30"
    if price < 60:
        return "30_60"
    if price < 120:
        return "60_120"
    return "120_plus"


def _rating_band(value: object, edges: list[float]) -> str:
    rating = _number(value)
    if rating is None or rating < 0:
        return "missing"
    score = math.log1p(rating)
    return f"q{sum(score > edge for edge in edges) + 1}"


def _feature_band(row: dict[str, Any]) -> str:
    count = len(row.get("features") or [])
    if count == 0:
        return "0"
    if count <= 4:
        return "1_4"
    if count <= 7:
        return "5_7"
    if count <= 10:
        return "8_10"
    return "11_plus"


def _description_band(row: dict[str, Any]) -> str:
    count = sum(len(str(value)) for value in (row.get("description") or []))
    if count == 0:
        return "0"
    if count <= 200:
        return "1_200"
    if count <= 800:
        return "201_800"
    return "801_plus"


def _depth_band(row: dict[str, Any]) -> str:
    count = len(row.get("categories") or [])
    return "0_3" if count <= 3 else "4" if count == 4 else "5" if count == 5 else "6_plus"


def _stratum(row: dict[str, Any], rating_edges: list[float]) -> tuple[str, str, str]:
    """Compact joint stratum; other catalog marginals are audited separately."""
    return (_price_band(row.get("price")), _rating_band(row.get("rating_number"), rating_edges), _feature_band(row))


def _stable_rng(seed: int, key: tuple[str, ...]) -> random.Random:
    digest = hashlib.sha256((str(seed) + "\0" + "\0".join(key)).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _distribution(rows: list[dict[str, Any]], rating_edges: list[float]) -> dict[str, dict[str, int]]:
    return {
        "price_band": dict(sorted(Counter(_price_band(row.get("price")) for row in rows).items())),
        "log_rating_number_band": dict(sorted(Counter(_rating_band(row.get("rating_number"), rating_edges) for row in rows).items())),
        "feature_band": dict(sorted(Counter(_feature_band(row) for row in rows).items())),
        "description_band": dict(sorted(Counter(_description_band(row) for row in rows).items())),
        "category_depth_band": dict(sorted(Counter(_depth_band(row) for row in rows).items())),
    }


def _js_divergence(left: Counter[str], right: Counter[str]) -> float:
    keys = set(left) | set(right)
    total_left, total_right = sum(left.values()), sum(right.values())
    if not total_left or not total_right:
        return 0.0
    result = 0.0
    for key in keys:
        p, q = left[key] / total_left, right[key] / total_right
        mean = (p + q) / 2
        if p:
            result += p * math.log2(p / mean) / 2
        if q:
            result += q * math.log2(q / mean) / 2
    return result


def build(
    *, source: Path, reference: Path, official_sessions: Path, output: Path, manifest: Path,
    target_count: int, seed: int,
) -> dict[str, Any]:
    if output.exists() or manifest.exists():
        raise FileExistsError("output and manifest must not already exist")
    reference_rows = _load_jsonl(reference)
    official_rows = _load_jsonl(official_sessions)
    if target_count % len(reference_rows):
        raise ValueError("target_count must be an integer multiple of reference catalog rows")
    multiplier = target_count // len(reference_rows)
    edges = _rating_edges(reference_rows)
    reference_strata = Counter(_stratum(row, edges) for row in reference_rows)
    quotas = {key: value * multiplier for key, value in reference_strata.items()}
    official_targets = {str(row["ground_truth"]["parent_asin"]) for row in official_rows}

    reservoirs: dict[tuple[str, str, str], list[tuple[int, str]]] = defaultdict(list)
    seen_by_stratum: Counter[tuple[str, str, str]] = Counter()
    rngs = {key: _stable_rng(seed, key) for key in quotas}
    mandatory: dict[str, tuple[int, tuple[str, str, str]]] = {}
    source_digest = hashlib.sha256()
    parsed, invalid, no_identifier, out_of_reference_stratum = 0, 0, 0, 0
    with source.open("rb") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            source_digest.update(line)
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                invalid += 1
                continue
            parsed += 1
            identifier = _product_id(row)
            if not identifier:
                no_identifier += 1
                continue
            key = _stratum(row, edges)
            if identifier in official_targets:
                mandatory[identifier] = (offset, key)
            quota = quotas.get(key)
            if quota is None:
                out_of_reference_stratum += 1
                continue
            seen_by_stratum[key] += 1
            reservoir = reservoirs[key]
            if len(reservoir) < quota:
                reservoir.append((offset, identifier))
            else:
                index = rngs[key].randrange(seen_by_stratum[key])
                if index < quota:
                    reservoir[index] = (offset, identifier)

    shortages = {"|".join(key): quotas[key] - len(reservoirs[key]) for key in quotas if len(reservoirs[key]) < quotas[key]}
    if shortages:
        raise ValueError("raw metadata cannot satisfy reference-stratum quotas: " + json.dumps(shortages, sort_keys=True))

    selected_by_stratum = {key: list(reservoirs[key]) for key in quotas}
    selected_ids = {identifier for rows in selected_by_stratum.values() for _offset, identifier in rows}
    added_mandatory, mandatory_fallback = 0, 0
    for identifier, (offset, key) in sorted(mandatory.items()):
        if identifier in selected_ids:
            continue
        candidates = selected_by_stratum.get(key)
        if not candidates:
            key = max(selected_by_stratum, key=lambda value: len(selected_by_stratum[value]))
            candidates = selected_by_stratum[key]
            mandatory_fallback += 1
        replacement_index = next(
            (index for index in range(len(candidates) - 1, -1, -1)
             if candidates[index][1] not in mandatory),
            None,
        )
        if replacement_index is None:
            raise ValueError("no non-mandatory record available to retain all official targets")
        removed_offset, removed_id = candidates.pop(replacement_index)
        selected_ids.remove(removed_id)
        candidates.append((offset, identifier))
        selected_ids.add(identifier)
        added_mandatory += 1
    selected = [entry for rows in selected_by_stratum.values() for entry in rows]
    if len(selected) != target_count or len(selected_ids) != target_count:
        raise ValueError("selected product identifiers are not unique or do not match target_count")

    selected_offsets = {offset for offset, _identifier in selected}
    output.parent.mkdir(parents=True, exist_ok=True)
    output_digest = hashlib.sha256()
    selected_rows: list[dict[str, Any]] = []
    with source.open("rb") as handle, output.open("xb") as destination:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            if offset not in selected_offsets:
                continue
            row = json.loads(line)
            encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
            destination.write(encoded)
            output_digest.update(encoded)
            selected_rows.append(row)
    if len(selected_rows) != target_count:
        raise ValueError(f"materialized {len(selected_rows)} rows, expected {target_count}")

    reference_distribution = _distribution(reference_rows, edges)
    selected_distribution = _distribution(selected_rows, edges)
    divergence = {
        name: round(_js_divergence(Counter(values), Counter(selected_distribution[name])), 8)
        for name, values in reference_distribution.items()
    }
    result = {
        "schema_version": "1.0",
        "source_dataset": "Amazon Reviews 2023 Clothing_Shoes_and_Jewelry metadata",
        "official_metric_contract": False,
        "purpose": "Expanded metadata-derived catalog for non-official scale experiments; do not report as an official TechJam catalog.",
        "selection": {
            "method": "two-pass deterministic joint-stratified reservoir sampling",
            "seed": seed,
            "target_count": target_count,
            "reference_catalog_rows": len(reference_rows),
            "scale_multiplier": multiplier,
            "joint_strata": ["price_band", "log_rating_number_quantile", "feature_band"],
            "rating_number_log_edges": edges,
        },
        "source": {"path": str(source), "bytes": source.stat().st_size, "sha256": source_digest.hexdigest(),
                   "parsed_rows": parsed, "invalid_json_rows": invalid, "missing_parent_asin_rows": no_identifier,
                   "out_of_reference_stratum_rows": out_of_reference_stratum},
        "reference": {"path": str(reference), "sha256": _sha256(reference), "distribution": reference_distribution},
        "official_public_targets": {"requested": len(official_targets), "found_in_raw_metadata": len(mandatory),
                                     "inserted_into_catalog": added_mandatory, "fallback_stratum_insertions": mandatory_fallback,
                                     "missing_from_raw_metadata": sorted(official_targets - set(mandatory))},
        "output": {"path": str(output), "rows": len(selected_rows), "bytes": output.stat().st_size,
                   "sha256": output_digest.hexdigest(), "distribution": selected_distribution,
                   "js_divergence_vs_reference": divergence},
    }
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-metadata", type=Path, required=True)
    parser.add_argument("--reference-catalog", type=Path, required=True)
    parser.add_argument("--official-sessions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--target-count", type=int, default=500_000)
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()
    result = build(source=args.source_metadata.resolve(), reference=args.reference_catalog.resolve(),
                   official_sessions=args.official_sessions.resolve(), output=args.output.resolve(),
                   manifest=args.manifest.resolve(), target_count=args.target_count, seed=args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
