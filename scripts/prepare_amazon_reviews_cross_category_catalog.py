from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _stable_offset(seed: int, source: str, index: int, width: int) -> int:
    digest = hashlib.sha256(f"{seed}\0{source}\0{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % max(width, 1)


def _selected_line_indices(
    row_count: int, quota: int, seed: int, source: str
) -> set[int]:
    selected: set[int] = set()
    for index in range(quota):
        start = index * row_count // quota
        end = (index + 1) * row_count // quota
        selected.add(start + _stable_offset(seed, source, index, end - start))
    if len(selected) != quota:
        raise ValueError(f"line-index selection was not unique for {source}")
    return selected


def _allocate_quotas(row_counts: list[int], target_products: int) -> list[int]:
    total = sum(row_counts)
    if target_products > total:
        raise ValueError(
            f"target_products={target_products} exceeds available rows={total}"
        )
    exact = [target_products * count / total for count in row_counts]
    quotas = [int(value) for value in exact]
    remainder = target_products - sum(quotas)
    order = sorted(
        range(len(row_counts)),
        key=lambda index: (exact[index] - quotas[index], row_counts[index]),
        reverse=True,
    )
    for index in order[:remainder]:
        quotas[index] += 1
    return quotas


def _price_band(price: object) -> str:
    if not isinstance(price, (int, float)):
        return "unknown"
    if price < 15:
        return "under_15"
    if price < 30:
        return "15_30"
    if price < 60:
        return "30_60"
    if price < 120:
        return "60_120"
    return "120_plus"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare(
    metadata_paths: list[Path],
    output_path: Path,
    manifest_path: Path,
    *,
    target_products: int,
    seed: int,
) -> dict[str, Any]:
    resolved_paths = [path.resolve() for path in metadata_paths]
    row_counts = []
    for path in resolved_paths:
        with path.open("rb") as handle:
            row_counts.append(sum(1 for _ in handle))
    quotas = _allocate_quotas(row_counts, target_products)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    category_distribution: Counter[str] = Counter()
    price_distribution: Counter[str] = Counter()
    source_selected: Counter[str] = Counter()
    invalid_json = 0
    missing_parent_asin = 0
    duplicates = 0

    def write_row(raw_line: bytes, source_name: str, target) -> bool:
        nonlocal invalid_json, missing_parent_asin, duplicates
        try:
            row = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid_json += 1
            return False
        parent_asin = str(row.get("parent_asin", "")).strip()
        if not parent_asin:
            missing_parent_asin += 1
            return False
        if parent_asin in seen:
            duplicates += 1
            return False
        seen.add(parent_asin)
        target.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        target.write("\n")
        source_selected[source_name] += 1
        leaf_category = str((row.get("categories") or ["unknown"])[-1])
        category_distribution[leaf_category] += 1
        price_distribution[_price_band(row.get("price"))] += 1
        return True

    with output_path.open("w", encoding="utf-8", newline="\n") as target:
        for path, row_count, quota in zip(
            resolved_paths, row_counts, quotas, strict=True
        ):
            source_name = path.parent.name
            selected_indices = _selected_line_indices(
                row_count, quota, seed, source_name
            )
            with path.open("rb") as source:
                for line_index, raw_line in enumerate(source):
                    if line_index in selected_indices:
                        write_row(raw_line, source_name, target)

        if len(seen) < target_products:
            for path in resolved_paths:
                source_name = path.parent.name
                with path.open("rb") as source:
                    for raw_line in source:
                        if (
                            write_row(raw_line, source_name, target)
                            and len(seen) == target_products
                        ):
                            break
                if len(seen) == target_products:
                    break

    if len(seen) != target_products:
        raise ValueError(
            f"only {len(seen)} unique valid products available; "
            f"target_products={target_products}"
        )

    sources = []
    for path, rows, quota in zip(resolved_paths, row_counts, quotas, strict=True):
        sources.append(
            {
                "category": path.parent.name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "rows": rows,
                "planned_quota": quota,
                "selected_products": source_selected[path.parent.name],
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "source_dataset": "Amazon Reviews 2023 non-clothing metadata",
        "sources": sources,
        "sampling": {
            "method": "proportional_disjoint_line_segments_with_seeded_jitter",
            "seed": seed,
            "target_products": target_products,
            "unique_products_written": len(seen),
            "invalid_json": invalid_json,
            "missing_parent_asin": missing_parent_asin,
            "duplicate_parent_asin": duplicates,
        },
        "output_path": str(output_path.resolve()),
        "output_bytes": output_path.stat().st_size,
        "output_sha256": _sha256_file(output_path),
        "coverage": {
            "source_category_distribution": dict(sorted(source_selected.items())),
            "unique_leaf_categories": len(category_distribution),
            "price_band_distribution": dict(sorted(price_distribution.items())),
        },
        "clothing_source_used": False,
        "review_data_used": False,
        "official_metric_contract": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_paths", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--target-products", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260829)
    args = parser.parse_args()
    if args.target_products < 1:
        raise ValueError("target_products must be positive")
    result = prepare(
        args.metadata_paths,
        args.output,
        args.manifest,
        target_products=args.target_products,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
