from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SUITE_ID = "techjam_compatible_scale_v1"
DEFAULT_SEED = 20260830
SCENARIO_COUNTS = {
    "dev": {"buying": 80, "browsing": 80, "intent_override": 30, "boundary": 10},
    "core": {"buying": 400, "browsing": 400, "intent_override": 150, "boundary": 50},
    "challenge": {"intent_override": 100, "boundary": 100},
}
DIFFICULTY_WEIGHTS = ("easy", "medium", "hard"), (0.20, 0.50, 0.30)
OVERRIDE_SUBTYPES = (
    "budget_change",
    "brand_change",
    "category_or_use_case_change",
    "key_attribute_change",
)
BOUNDARY_SUBTYPES = (
    "exact_threshold",
    "negation_scope",
    "unit_or_size_ambiguity",
    "hard_soft_conflict",
)
MATERIAL_RE = re.compile(
    r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|linen|rubber|stainless steel|alloy)\b",
    re.IGNORECASE,
)
COLOR_RE = re.compile(
    r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange|silver|gold)\b",
    re.IGNORECASE,
)
USE_CASE_RE = re.compile(
    r"\b(running|hiking|walking|winter|outdoor|work|casual|travel|gym|wedding|sports?)\b",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean(value: object, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" -;,.")
    text = re.sub(r"https?://\S+", "", text).strip()
    return text[:limit].rstrip(" -;,.")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug[:64] or "unknown"


def _categories(raw: dict[str, Any]) -> list[str]:
    values = raw.get("categories") or []
    if not isinstance(values, list):
        values = [values]
    return [_clean(value, 80) for value in values if _clean(value, 80)]


def _coarse_category(raw: dict[str, Any]) -> str:
    excluded = {
        "clothing",
        "clothing shoes & jewelry",
        "clothing, shoes & jewelry",
        "amazon fashion",
    }
    cleaned: list[str] = []
    for value in _categories(raw):
        for part in value.split(","):
            part = part.strip()
            if part and part.lower() not in excluded:
                cleaned.append(part)
    return " ".join(cleaned[-2:]) if cleaned else "fashion item"


def _price(raw: dict[str, Any]) -> float | None:
    try:
        value = float(raw.get("price"))
    except (TypeError, ValueError):
        return None
    return value if value > 0 and math.isfinite(value) else None


def _price_band(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 15:
        return "under_15"
    if value < 30:
        return "15_30"
    if value < 60:
        return "30_60"
    if value < 120:
        return "60_120"
    return "120_plus"


def _searchable_text(raw: dict[str, Any]) -> str:
    values: list[str] = []
    for field in ("title", "features", "description", "details", "categories", "store"):
        value = raw.get(field)
        if isinstance(value, dict):
            values.extend(f"{key} {item}" for key, item in value.items())
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value not in (None, ""):
            values.append(str(value))
    return " ".join(values)


def _fact(attribute: str, text: str) -> dict[str, str]:
    return {"attribute": attribute, "text": _clean(text)}


def _product_candidate(raw: dict[str, Any]) -> dict[str, Any] | None:
    parent_asin = _clean(raw.get("parent_asin") or raw.get("asin"), 32)
    title = _clean(raw.get("title"), 180)
    category = _coarse_category(raw)
    if not parent_asin or not title or category == "fashion item":
        return None

    corpus = _searchable_text(raw)
    facts: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(attribute: str, text: str) -> None:
        cleaned = _clean(text)
        key = cleaned.lower()
        if cleaned and key not in seen and title.lower() not in key:
            seen.add(key)
            facts.append(_fact(attribute, cleaned))

    material = MATERIAL_RE.search(corpus)
    color = COLOR_RE.search(corpus)
    use_case = USE_CASE_RE.search(corpus)
    if material:
        add("material", f"material: {material.group(1).lower()}")
    if color:
        add("color", f"color: {color.group(1).lower()}")
    value = _price(raw)
    if value is not None:
        ceiling = math.ceil(value * 1.10 / 5.0) * 5.0
        add("budget", f"budget at or below ${ceiling:.2f}")
    brand = _clean(raw.get("store") or raw.get("brand"), 60)
    if brand:
        add("brand", f"brand: {brand}")
    if use_case:
        add("use_case", f"suitable for {use_case.group(1).lower()}")

    rating = raw.get("average_rating")
    try:
        rating_value = float(rating)
    except (TypeError, ValueError):
        rating_value = 0.0
    if rating_value >= 3.5:
        add("rating", f"average rating of at least {math.floor(rating_value * 2) / 2:.1f}")

    features = raw.get("features") or []
    if not isinstance(features, list):
        features = [features]
    for feature in features:
        cleaned = _clean(feature, 100)
        if 12 <= len(cleaned) <= 100 and not re.search(
            r"\b(gift|click|add to cart|customer service|guarantee|return)\b",
            cleaned,
            re.IGNORECASE,
        ):
            add("feature", cleaned)
        if len(facts) >= 7:
            break

    if len(facts) < 5:
        return None
    raw_categories = _categories(raw)
    return {
        "parent_asin": parent_asin,
        "title": title,
        "main_category": _clean(raw.get("main_category"), 80) or "unknown",
        "root_category": raw_categories[0] if raw_categories else "unknown",
        "category": category,
        "category_bucket": _slug(category),
        "price": value,
        "price_band": _price_band(value),
        "brand": brand or None,
        "facts": facts,
    }


def _load_excluded_targets(path: Path | None) -> set[str]:
    if path is None:
        return set()
    result: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            target = str((row.get("ground_truth") or {}).get("parent_asin") or "").strip()
            if target:
                result.add(target)
    return result


def _load_candidates(catalog: Path, excluded: set[str]) -> tuple[list[dict[str, Any]], int]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    row_count = 0
    with catalog.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row_count += 1
            candidate = _product_candidate(json.loads(line))
            if candidate is None:
                continue
            product_id = candidate["parent_asin"]
            if product_id in seen or product_id in excluded:
                continue
            seen.add(product_id)
            candidates.append(candidate)
    return candidates, row_count


def _balanced_select(
    candidates: list[dict[str, Any]], count: int, rng: random.Random
) -> list[dict[str, Any]]:
    pools: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        pools[(candidate["category_bucket"], candidate["price_band"])].append(candidate)
    keys = list(pools)
    rng.shuffle(keys)
    for pool in pools.values():
        rng.shuffle(pool)

    selected: list[dict[str, Any]] = []
    while len(selected) < count:
        progressed = False
        for key in keys:
            if pools[key]:
                selected.append(pools[key].pop())
                progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            break
    if len(selected) != count:
        raise ValueError(f"Only {len(selected)} eligible unique targets; {count} required")
    rng.shuffle(selected)
    return selected


def _difficulty_sequence(count: int, rng: random.Random) -> list[str]:
    names, weights = DIFFICULTY_WEIGHTS
    easy = round(count * weights[0])
    medium = round(count * weights[1])
    hard = count - easy - medium
    values = [names[0]] * easy + [names[1]] * medium + [names[2]] * hard
    rng.shuffle(values)
    return values


def _assignments(rng: random.Random) -> list[dict[str, str]]:
    assignments: list[dict[str, str]] = []
    # The 1,000-session core is an exact 5x scaling of the participant kit's
    # public 200-session scenario/difficulty distribution.
    official_difficulty = {
        "buying": "easy",
        "browsing": "medium",
        "intent_override": "hard",
        "boundary": "medium",
    }
    for scenario, count in SCENARIO_COUNTS["core"].items():
        for _ in range(count):
            assignments.append(
                {
                    "split": "core",
                    "scenario_type": scenario,
                    "difficulty": official_difficulty[scenario],
                    "subtype": "official_style",
                }
            )

    # The independent 200-session development split follows the same public
    # distribution exactly, but remains separate from the 1,000-session
    # headline evaluation split to reduce tuning leakage.
    for scenario, count in SCENARIO_COUNTS["dev"].items():
        for _ in range(count):
            assignments.append(
                {
                    "split": "dev",
                    "scenario_type": scenario,
                    "difficulty": official_difficulty[scenario],
                    "subtype": "official_style",
                }
            )
    for scenario, count in SCENARIO_COUNTS["challenge"].items():
        subtype_pool = OVERRIDE_SUBTYPES if scenario == "intent_override" else BOUNDARY_SUBTYPES
        for index in range(count):
            assignments.append(
                {
                    "split": "challenge",
                    "scenario_type": scenario,
                    "difficulty": "hard",
                    "subtype": subtype_pool[index % len(subtype_pool)],
                }
            )
    rng.shuffle(assignments)
    return assignments


def _choose_facts(
    candidate: dict[str, Any], difficulty: str, rng: random.Random
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    facts = list(candidate["facts"])
    priority = {"material": 0, "color": 1, "budget": 2, "use_case": 3, "brand": 4, "feature": 5, "rating": 6}
    facts.sort(key=lambda item: (priority.get(item["attribute"], 9), item["text"]))
    head = facts[:3]
    tail = facts[3:]
    rng.shuffle(head)
    rng.shuffle(tail)
    facts = head + tail
    hard_count = 2 if difficulty in {"easy", "medium"} else 3
    soft_count = 1 if difficulty == "easy" else 2
    return facts[:hard_count], facts[hard_count : hard_count + soft_count]


def _profile(facts: list[dict[str, str]], rng: random.Random) -> dict[str, Any]:
    tags = list(dict.fromkeys(item["attribute"] for item in facts))[:4]
    average = rng.choice((2.5, 3.0, 3.5, 4.0, 4.5, 5.0))
    style = "critical" if average <= 3.0 else "mixed" if average < 4.0 else "usually positive"
    frequency = rng.choice(("first purchase in this category", "1-2 prior purchases", "3-4 prior purchases", "frequent shopper"))
    return {
        "average_prior_rating": average,
        "preference_tags": tags,
        "purchase_frequency": frequency,
        "rating_style": style,
        "summary": f"A {frequency} who prioritizes {', '.join(tags)} and is {style} in reviews.",
        "profile_origin": "synthetic_from_catalog_metadata",
    }


def _first_fact(facts: list[dict[str, str]], attribute: str) -> dict[str, str] | None:
    return next((item for item in facts if item["attribute"] == attribute), None)


def _behavior(
    candidate: dict[str, Any],
    scenario_type: str,
    subtype: str,
    hard: list[dict[str, str]],
    soft: list[dict[str, str]],
    rng: random.Random,
) -> dict[str, Any]:
    category = candidate["category"]
    first_hard = hard[0]["text"]
    first_soft = (soft or hard)[0]["text"]
    behavior: dict[str, Any] = {"scenario_type": scenario_type}
    if scenario_type == "buying":
        templates = (
            "I'm ready to buy a {category}. A non-negotiable requirement is {constraint}.",
            "I need a {category}, and it must satisfy this: {constraint}.",
            "Please help me choose a {category}. The key requirement is {constraint}.",
        )
        behavior["initial_message"] = rng.choice(templates).format(
            category=category, constraint=first_hard
        )
        behavior["initial_disclosed"] = [first_hard]
    elif scenario_type == "browsing":
        templates = (
            "I'm comparing {category} options. I care about {preference}, but I need help narrowing them down.",
            "I'm browsing for a {category}. {preference} would be nice, and I'm open to questions.",
            "I haven't decided which {category} to buy. My starting preference is {preference}.",
        )
        behavior["initial_message"] = rng.choice(templates).format(
            category=category, preference=first_soft
        )
        behavior["initial_disclosed"] = [first_soft]
    elif scenario_type == "intent_override":
        new_fact = first_hard
        if subtype == "budget_change":
            preferred = _first_fact(hard + soft + candidate["facts"], "budget")
            new_fact = preferred["text"] if preferred else first_hard
            old_value = "I was initially trying to keep the price much lower"
        elif subtype == "brand_change":
            preferred = _first_fact(hard + soft + candidate["facts"], "brand")
            new_fact = preferred["text"] if preferred else first_hard
            old_value = "I was initially leaning toward a different brand"
        elif subtype == "category_or_use_case_change":
            preferred = _first_fact(hard + soft + candidate["facts"], "use_case")
            new_fact = preferred["text"] if preferred else f"the final category must be {category}"
            old_value = "I first thought this was mainly for casual use"
        else:
            preferred = next(
                (item for item in hard + soft + candidate["facts"] if item["attribute"] in {"material", "color", "feature"}),
                hard[0],
            )
            new_fact = preferred["text"]
            old_value = "At first I thought a different material or style would be fine"
        turn = rng.choice((3, 4))
        behavior.update(
            {
                "initial_message": f"I'm considering a {category}. {old_value}.",
                "initial_disclosed": [],
                "override": {
                    "turn": turn,
                    "subtype": subtype,
                    "old_value": old_value,
                    "new_value": new_fact,
                    "message": f"Actually, ignore that earlier preference. What I need now is: {new_fact}.",
                },
            }
        )
    else:
        if subtype == "exact_threshold":
            preferred = _first_fact(hard + soft + candidate["facts"], "budget")
            attribute = preferred["attribute"] if preferred else hard[0]["attribute"]
            fact = preferred["text"] if preferred else first_hard
            message = f"Treat this as an exact limit, not an approximation: {fact}."
        elif subtype == "negation_scope":
            attribute = "category"
            message = f"I do not want options outside {category}; that exclusion matters more than brand."
        elif subtype == "unit_or_size_ambiguity":
            attribute = "size"
            message = "Use the size or unit system stated in the listing; please do not silently convert or round it."
        else:
            attribute = hard[0]["attribute"]
            message = f"{first_hard} is required. {first_soft} is only a preference if those two conflict."
        behavior.update(
            {
                "initial_message": f"I'm looking for a {category}, but one limit needs to be interpreted carefully.",
                "initial_disclosed": [],
                "boundary": {"subtype": subtype, "attribute": attribute, "message": message},
            }
        )
    return behavior


def _session_row(
    candidate: dict[str, Any], assignment: dict[str, str], ordinal: int, rng: random.Random
) -> dict[str, Any]:
    hard, soft = _choose_facts(candidate, assignment["difficulty"], rng)
    scenario_type = assignment["scenario_type"]
    split = assignment["split"]
    sample_id = f"tcsv1_{split}_{ordinal:04d}"
    behavior = _behavior(
        candidate,
        scenario_type,
        assignment["subtype"],
        hard,
        soft,
        rng,
    )
    all_facts = hard + soft
    row = {
        "sample_id": sample_id,
        "scenario_type": scenario_type,
        "difficulty_bucket": assignment["difficulty"],
        "category_bucket": candidate["category_bucket"],
        "ground_truth": {"parent_asin": candidate["parent_asin"]},
        "user_profile": _profile(all_facts, rng),
        "generation_metadata": {
            "suite_id": SUITE_ID,
            "split": split,
            "subtype": assignment["subtype"],
            "construction_track": (
                "official_style_participant_materialized"
                if split in {"core", "dev"}
                else "custom_diagnostic"
            ),
            "source_dataset": "amazon_reviews_2023_resampled_clothing_50k",
            "official_session_reused": False,
            "official_metric_contract": False,
        },
    }
    if split not in {"core", "dev"}:
        row["intent_card"] = {
            "target_category": candidate["category"],
            "hard_constraints": [item["text"] for item in hard],
            "soft_preferences": [item["text"] for item in soft],
        }
        row["behavior"] = behavior
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _distribution(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def _smoke_rows(official_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wanted = {"buying": 8, "browsing": 8, "intent_override": 3, "boundary": 1}
    selected: list[dict[str, Any]] = []
    for scenario_type, count in wanted.items():
        selected.extend(
            [row for row in official_rows if row["scenario_type"] == scenario_type][:count]
        )
    return sorted(selected, key=lambda row: row["sample_id"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate catalog-derived TechJam-compatible development and evaluation sessions"
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--exclude-sessions", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    catalog = args.catalog.resolve()
    excluded_path = args.exclude_sessions.resolve() if args.exclude_sessions else None
    output_dir = args.output_dir.resolve()
    excluded = _load_excluded_targets(excluded_path)
    candidates, catalog_rows = _load_candidates(catalog, excluded)
    rng = random.Random(args.seed)
    assignments = _assignments(rng)
    selected = _balanced_select(candidates, len(assignments), rng)

    split_ordinals: Counter[str] = Counter()
    rows_by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate, assignment in zip(selected, assignments):
        split = assignment["split"]
        split_ordinals[split] += 1
        row_rng = random.Random(f"{args.seed}\0{candidate['parent_asin']}\0{split_ordinals[split]}")
        rows_by_split[split].append(
            _session_row(candidate, assignment, split_ordinals[split], row_rng)
        )

    for rows in rows_by_split.values():
        rows.sort(key=lambda row: row["sample_id"])
    smoke = _smoke_rows(rows_by_split["dev"])
    outputs = {
        "official_style_dev_200_rebuilt_amazon_clothing_50k.jsonl": rows_by_split["dev"],
        "official_style_core_1000_rebuilt_amazon_clothing_50k.jsonl": rows_by_split["core"],
        "custom_challenge_200_rebuilt_amazon_clothing_50k.jsonl": rows_by_split["challenge"],
        "official_style_smoke_20_rebuilt_amazon_clothing_50k.jsonl": smoke,
    }
    for name, rows in outputs.items():
        _write_jsonl(output_dir / name, rows)

    index_path = output_dir / "session_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "sample_id",
                "split",
                "scenario_type",
                "difficulty_bucket",
                "subtype",
                "category_bucket",
                "parent_asin",
            ),
        )
        writer.writeheader()
        for split in ("dev", "core", "challenge"):
            for row in rows_by_split[split]:
                writer.writerow(
                    {
                        "sample_id": row["sample_id"],
                        "split": split,
                        "scenario_type": row["scenario_type"],
                        "difficulty_bucket": row["difficulty_bucket"],
                        "subtype": row["generation_metadata"]["subtype"],
                        "category_bucket": row["category_bucket"],
                        "parent_asin": row["ground_truth"]["parent_asin"],
                    }
                )

    unique_rows = [
        *rows_by_split["dev"],
        *rows_by_split["core"],
        *rows_by_split["challenge"],
    ]
    target_ids = [row["ground_truth"]["parent_asin"] for row in unique_rows]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError("Target leakage: dev/core/challenge targets are not unique")
    if set(target_ids) & excluded:
        raise ValueError("Official target leakage detected")

    manifest = {
        "schema_version": "1.0",
        "suite_id": SUITE_ID,
        "seed": args.seed,
        "official_sessions_reused": False,
        "official_targets_reused": False,
        "official_metric_contract": False,
        "official_style_session_count": (
            len(rows_by_split["core"]) + len(rows_by_split["dev"])
        ),
        "official_style_development_session_count": len(rows_by_split["dev"]),
        "official_style_headline_session_count": len(rows_by_split["core"]),
        "custom_diagnostic_session_count": len(rows_by_split["challenge"]),
        "headline_split": "core",
        "headline_construction": "official_style_participant_materialized",
        "official_public_distribution_multiplier": 5,
        "target_source_catalog": {
            "path_hint": args.catalog.name,
            "sha256": _sha256(catalog),
            "row_count": catalog_rows,
            "eligible_non_official_targets": len(candidates),
        },
        "excluded_official_target_count": len(excluded),
        "unique_session_count": len(unique_rows),
        "derived_smoke_count": len(smoke),
        "splits": {
            split: {
                "sample_count": len(rows),
                "scenario_distribution": _distribution(rows, "scenario_type"),
                "difficulty_distribution": _distribution(rows, "difficulty_bucket"),
                "subtype_distribution": dict(
                    sorted(Counter(row["generation_metadata"]["subtype"] for row in rows).items())
                ),
            }
            for split, rows in rows_by_split.items()
        },
        "files": {},
    }
    for name in [*outputs, "session_index.csv"]:
        path = output_dir / name
        manifest["files"][name] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
