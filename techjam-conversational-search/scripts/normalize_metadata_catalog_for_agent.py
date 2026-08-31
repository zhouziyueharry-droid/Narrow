"""Remove unused media fields from a metadata-derived catalog without changing products."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


AGENT_FIELDS = (
    "parent_asin", "title", "features", "description", "price", "categories",
    "details", "average_rating", "rating_number", "store",
)


def normalize(source: Path, output: Path, manifest: Path) -> dict:
    if output.exists() or manifest.exists():
        raise FileExistsError("output and manifest must not already exist")
    source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
    seen: set[str] = set()
    output.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_handle, output.open("xb") as output_handle:
        for line_number, line in enumerate(input_handle, start=1):
            source_hash.update(line)
            row = json.loads(line)
            identifier = str(row.get("parent_asin") or "").strip()
            if not identifier or identifier in seen:
                raise ValueError(f"duplicate or missing parent_asin at source line {line_number}")
            seen.add(identifier)
            normalized = {key: row.get(key) for key in AGENT_FIELDS}
            normalized["parent_asin"] = identifier
            encoded = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
            output_handle.write(encoded)
            output_hash.update(encoded)
    result = {
        "schema_version": "1.0",
        "purpose": "Agent-ready normalized view of a metadata-derived catalog; no product fields are invented.",
        "source": {"path": str(source), "sha256": source_hash.hexdigest(), "bytes": source.stat().st_size},
        "retained_fields": list(AGENT_FIELDS),
        "removed_fields": ["images", "videos", "bought_together", "main_category"],
        "output": {"path": str(output), "sha256": output_hash.hexdigest(), "bytes": output.stat().st_size,
                   "rows": len(seen)},
    }
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(normalize(args.source.resolve(), args.output.resolve(), args.manifest.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
