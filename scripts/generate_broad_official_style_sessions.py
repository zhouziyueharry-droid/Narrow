from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from generate_techjam_compatible_sessions import (
    _balanced_select,
    _load_candidates,
    _session_row,
    _write_jsonl,
)


SUITE_ID = "techjam_compatible_broad_500k_v1"
SCENARIO_COUNTS = {
    "buying": 400,
    "browsing": 400,
    "intent_override": 150,
    "boundary": 50,
}
OFFICIAL_DIFFICULTY = {
    "buying": "easy",
    "browsing": "medium",
    "intent_override": "hard",
    "boundary": "medium",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _session_targets(paths: list[Path]) -> set[str]:
    result: set[str] = set()
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                target = str((row.get("ground_truth") or {}).get("parent_asin") or "").strip()
                if target:
                    result.add(target)
    return result


def _assignments() -> list[dict[str, str]]:
    return [
        {
            "split": "core",
            "scenario_type": scenario,
            "difficulty": OFFICIAL_DIFFICULTY[scenario],
            "subtype": "official_style",
        }
        for scenario, count in SCENARIO_COUNTS.items()
        for _ in range(count)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate 1,000 official-style sessions from the full broad catalog"
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--exclude-sessions", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--suite-id", default=SUITE_ID)
    parser.add_argument("--sample-prefix", default="tcsv1_broad_core")
    parser.add_argument(
        "--source-dataset",
        default="rebuilt_amazon_reviews_2023_cross_category_500k",
    )
    args = parser.parse_args()

    catalog = args.catalog.resolve()
    excluded = _session_targets([path.resolve() for path in args.exclude_sessions])
    candidates, catalog_rows = _load_candidates(catalog, excluded)
    rng = random.Random(args.seed)
    assignments = _assignments()
    rng.shuffle(assignments)
    selected = _balanced_select(candidates, len(assignments), rng)

    rows: list[dict[str, Any]] = []
    for ordinal, (candidate, assignment) in enumerate(zip(selected, assignments), 1):
        row_rng = random.Random(f"{args.seed}\0{candidate['parent_asin']}\0{ordinal}")
        row = _session_row(candidate, assignment, ordinal, row_rng)
        row["sample_id"] = f"{args.sample_prefix}_{ordinal:04d}"
        row["generation_metadata"].update(
            {
                "suite_id": args.suite_id,
                "split": "broad_core",
                "source_dataset": args.source_dataset,
            }
        )
        rows.append(row)
    rows.sort(key=lambda row: row["sample_id"])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(args.output, rows)
    scenario_distribution = Counter(row["scenario_type"] for row in rows)
    difficulty_distribution = Counter(row["difficulty_bucket"] for row in rows)
    main_categories = Counter(candidate.get("main_category", "unknown") for candidate in selected)
    root_categories = Counter(candidate.get("root_category", "unknown") for candidate in selected)
    manifest = {
        "schema_version": "1.0",
        "suite_id": args.suite_id,
        "seed": args.seed,
        "sample_count": len(rows),
        "official_metric_contract": False,
        "construction": "official_style_participant_materialized",
        "catalog_path_hint": catalog.name,
        "catalog_rows": catalog_rows,
        "catalog_sha256": _sha256(catalog),
        "source_dataset": args.source_dataset,
        "excluded_target_count": len(excluded),
        "eligible_full_catalog_targets": len(candidates),
        "scenario_distribution": dict(sorted(scenario_distribution.items())),
        "difficulty_distribution": dict(sorted(difficulty_distribution.items())),
        "main_category_distribution": dict(sorted(main_categories.items())),
        "root_category_distribution": dict(sorted(root_categories.items())),
        "output": {
            "path": args.output.name,
            "bytes": args.output.stat().st_size,
            "sha256": _sha256(args.output),
        },
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
