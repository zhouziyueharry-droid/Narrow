from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _stable_jitter(seed: int, index: int, width: int) -> int:
    digest = hashlib.sha256(f"{seed}\0{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % max(width, 1)


def _sample_offsets(file_size: int, sample_points: int, seed: int) -> list[int]:
    width = max(file_size // sample_points, 1)
    return [
        min(index * width + _stable_jitter(seed, index, width), file_size - 1)
        for index in range(sample_points)
    ]


def _read_complete_line(handle, offset: int) -> bytes:
    handle.seek(offset)
    if offset:
        handle.readline()
    return handle.readline()


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


def prepare(
    metadata_path: Path,
    output_path: Path,
    manifest_path: Path,
    *,
    sample_points: int,
    seed: int,
) -> dict[str, Any]:
    file_size = metadata_path.stat().st_size
    offsets = _sample_offsets(file_size, sample_points, seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    invalid_json = 0
    missing_parent_asin = 0
    with metadata_path.open("rb") as source:
        for offset in offsets:
            line = _read_complete_line(source, offset)
            if not line:
                continue
            try:
                row = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                invalid_json += 1
                continue
            parent_asin = str(row.get("parent_asin", "")).strip()
            if not parent_asin:
                missing_parent_asin += 1
                continue
            if parent_asin in seen:
                continue
            seen.add(parent_asin)
            selected.append(row)

    with output_path.open("w", encoding="utf-8", newline="\n") as target:
        for row in selected:
            target.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            target.write("\n")

    category_distribution = Counter(
        str((row.get("categories") or ["unknown"])[-1]) for row in selected
    )
    price_distribution = Counter(_price_band(row.get("price")) for row in selected)
    output_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "source_dataset": "Amazon Reviews 2023 Clothing_Shoes_and_Jewelry metadata",
        "source_path": str(metadata_path.resolve()),
        "source_bytes": file_size,
        "sampling": {
            "method": "systematic_byte_segments_with_seeded_jitter",
            "seed": seed,
            "requested_sample_points": sample_points,
            "unique_products_written": len(selected),
            "invalid_json": invalid_json,
            "missing_parent_asin": missing_parent_asin,
        },
        "output_path": str(output_path.resolve()),
        "output_bytes": output_path.stat().st_size,
        "output_sha256": output_sha256,
        "coverage": {
            "unique_leaf_categories": len(category_distribution),
            "price_band_distribution": dict(sorted(price_distribution.items())),
        },
        "review_data_used": False,
        "review_data_status": (
            "The review JSONL is reserved for a later user-history/profile layer; "
            "this catalog preparation uses item metadata only."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sample-points", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20260829)
    args = parser.parse_args()
    if args.sample_points < 1:
        raise ValueError("sample_points must be positive")
    result = prepare(
        args.metadata_path,
        args.output_path,
        args.manifest,
        sample_points=args.sample_points,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
