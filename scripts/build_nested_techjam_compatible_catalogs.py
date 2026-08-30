from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, TextIO


TARGETS = {
    "resampled_50k.jsonl": 50_000,
    "nested_200k.jsonl": 200_000,
    "nested_500k.jsonl": 500_000,
}


def _product_id(row: dict[str, Any]) -> str:
    return str(row.get("parent_asin") or row.get("asin") or row.get("product_id") or "").strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_unique(
    source: Path,
    destination: TextIO,
    seen: set[str],
    target_count: int,
) -> int:
    added = 0
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if len(seen) >= target_count:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            product_id = _product_id(row)
            if not product_id or product_id in seen:
                continue
            seen.add(product_id)
            destination.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            added += 1
    return added


def _build(
    destination: Path,
    target_count: int,
    sources: list[Path],
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    seen: set[str] = set()
    provenance: list[dict[str, Any]] = []
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        for source in sources:
            before = len(seen)
            added = _append_unique(source, output, seen, target_count)
            provenance.append(
                {
                    "source": source.name,
                    "added": added,
                    "catalog_count_after_source": len(seen),
                    "catalog_count_before_source": before,
                }
            )
            if len(seen) == target_count:
                break
    if len(seen) != target_count:
        temporary.unlink(missing_ok=True)
        raise ValueError(
            f"Could only build {len(seen)} unique products for {destination.name}; "
            f"{target_count} required"
        )
    temporary.replace(destination)
    return {
        "path": destination.name,
        "product_count": len(seen),
        "bytes": destination.stat().st_size,
        "sha256": _sha256(destination),
        "sources": provenance,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build exact nested 50k, 200k, and 500k TechJam-compatible catalogs"
    )
    parser.add_argument("--resampled-source", type=Path, required=True)
    parser.add_argument("--scale-source", type=Path, required=True)
    parser.add_argument("--cross-category-source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    resampled = args.resampled_source.resolve()
    scale = args.scale_source.resolve()
    cross = args.cross_category_source.resolve()
    output_dir = args.output_dir.resolve()
    inputs = [resampled, scale, cross]
    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise SystemExit("Missing source catalogs: " + ", ".join(missing))

    base = output_dir / "resampled_50k.jsonl"
    medium = output_dir / "nested_200k.jsonl"
    large = output_dir / "nested_500k.jsonl"
    catalogs = {
        "resampled_50k": _build(base, TARGETS[base.name], [resampled, scale, cross]),
        "nested_200k": _build(medium, TARGETS[medium.name], [base, scale, cross]),
        "nested_500k": _build(large, TARGETS[large.name], [medium, cross, scale]),
    }
    manifest = {
        "schema_version": "1.0",
        "suite_id": "techjam_compatible_scale_v1",
        "construction": "nested_by_parent_asin",
        "subset_invariants": [
            "resampled_50k is a prefix/subset of nested_200k",
            "nested_200k is a prefix/subset of nested_500k",
        ],
        "catalogs": catalogs,
    }
    manifest_path = output_dir / "catalog_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
