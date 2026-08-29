from __future__ import annotations

import csv
import hashlib
import json
import random
from collections.abc import Iterable
from pathlib import Path

from .models import (
    Constraint,
    NeedBasedGoal,
    OverrideEvent,
    Product,
    RelaxationEvent,
    ScenarioSpec,
    TargetProductGoal,
)
from .personas import PERSONA_TEMPLATES
from .techjam import (
    build_behavior,
    build_intent_card,
    classify_constraint,
    coarse_category,
)


def _flatten_details(value: object) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    if not isinstance(value, dict):
        return result
    for key, raw in value.items():
        name = str(key).strip().lower().replace(" ", "_")
        if raw in (None, "", []):
            continue
        vals = raw if isinstance(raw, list) else [raw]
        result[name] = [str(v) for v in vals if v not in (None, "")]
    return result


def _stable_seed(*parts: object) -> int:
    raw = "\0".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:4], "big")


def normalize_amazon_product(raw: dict) -> Product:
    product_id = str(raw.get("parent_asin") or raw.get("asin") or raw.get("product_id") or "").strip()
    if not product_id:
        raise ValueError("Product missing parent_asin/asin/product_id")
    categories = raw.get("categories") or []
    if not isinstance(categories, list):
        categories = [categories]
    features = raw.get("features") or []
    if not isinstance(features, list):
        features = [features]
    description = raw.get("description")
    if isinstance(description, list):
        description = " ".join(str(v) for v in description)
    price = raw.get("price")
    try:
        price = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price = None
    details = _flatten_details(raw.get("details"))
    if features:
        details.setdefault("feature", [str(value) for value in features if value not in (None, "")])
    brand = str(raw.get("store") or raw.get("brand") or "").strip() or None
    if brand:
        details.setdefault("brand", [brand])
    return Product(
        product_id=product_id,
        title=str(raw.get("title") or "product"),
        categories=[str(v) for v in categories],
        brand=brand,
        price=price,
        features=[str(v) for v in features],
        description=str(description) if description else None,
        attributes=details,
        raw=raw,
    )


class TechJamDatasetAdapter:
    def __init__(self, catalog_path: str | Path, sessions_path: str | Path | None = None):
        self.catalog_path = Path(catalog_path)
        self.sessions_path = Path(sessions_path) if sessions_path else None

    def load_products(self) -> Iterable[Product]:
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield normalize_amazon_product(json.loads(line))

    def build_target_sessions(
        self,
        persona_template: str = "casual_browser",
        max_turns: int = 10,
    ) -> list[ScenarioSpec]:
        if self.sessions_path is None:
            raise ValueError("sessions_path is required")
        catalog = {product.product_id: product for product in self.load_products()}
        result: list[ScenarioSpec] = []
        with self.sessions_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                sample = json.loads(line)
                target = str(sample["ground_truth"]["parent_asin"])
                sample_id = str(sample.get("sample_id", target))
                scenario_type = str(sample.get("scenario_type", "unknown"))
                product = catalog.get(target)
                if product is None:
                    raise ValueError(f"Session {sample_id} target {target} is missing from the catalog")
                intent_card = sample.get("intent_card")
                if not isinstance(intent_card, dict):
                    intent_card = build_intent_card(product.raw)
                behavior = sample.get("behavior")
                if not isinstance(behavior, dict):
                    behavior = build_behavior(scenario_type, intent_card, sample_id)
                constraints = [
                    Constraint(classify_constraint(str(value)), [str(value)], "hard", source="techjam")
                    for value in intent_card.get("hard_constraints", [])
                ]
                constraints.extend(
                    Constraint(
                        classify_constraint(str(value)),
                        [str(value)],
                        "soft",
                        source="techjam",
                        relaxable=True,
                    )
                    for value in intent_card.get("soft_preferences", [])
                )
                category = coarse_category(product.categories)
                goal = TargetProductGoal(
                    goal_id=sample_id,
                    target_product_id=target,
                    constraints=constraints,
                    category=category,
                    source_dataset="techjam",
                )
                result.append(
                    ScenarioSpec(
                        scenario_id=sample_id,
                        goal=goal,
                        persona_template=persona_template,
                        max_turns=max_turns,
                        seed=_stable_seed(sample_id, scenario_type),
                        protocol="techjam",
                        scenario_type=scenario_type,
                        user_profile=dict(sample.get("user_profile") or {}),
                        metadata={
                            "techjam": {
                                "category": category,
                                "intent_card": intent_card,
                                "behavior": behavior,
                            }
                        },
                    )
                )
        return result


def _realistic_goal(
    product: Product,
    *,
    budget_multiplier: float = 1.10,
    min_soft_preferences: int = 1,
    min_soft_matches: int = 1,
    source_dataset: str = "catalog_realistic",
) -> NeedBasedGoal | None:
    category = product.categories[-1] if product.categories else None
    hard: list[Constraint] = []
    if category:
        hard.append(Constraint("category", [category], "hard", source="catalog"))
    if product.price is not None:
        hard.append(
            Constraint(
                "budget_max",
                [f"{product.price * budget_multiplier:.2f}"],
                "hard",
                source="catalog",
                relaxable=True,
            )
        )

    soft: list[Constraint] = []
    if product.brand:
        soft.append(Constraint("brand", [product.brand], "soft", source="catalog", relaxable=True))
    for attribute in ("color", "material", "size", "style", "feature"):
        values = product.attributes.get(attribute, [])
        if values:
            soft.append(
                Constraint(attribute, [values[0]], "soft", source="catalog", relaxable=True)
            )
        if len(soft) >= 3:
            break
    if not hard or len(soft) < min_soft_preferences:
        return None
    return NeedBasedGoal(
        goal_id=f"realistic:{product.product_id}",
        category=category,
        hard_constraints=hard,
        soft_preferences=soft,
        min_soft_matches=min(min_soft_matches, len(soft)),
        source_dataset=source_dataset,
    )


def build_realistic_scenarios(
    products: Iterable[Product],
    count: int = 100,
    seed: int = 42,
    max_turns: int = 10,
    persona_templates: list[str] | None = None,
    persona_driven_override_enabled: bool = True,
    difficulty_profile: str = "standard",
    budget_multiplier: float = 1.10,
    min_soft_preferences: int = 1,
    min_soft_matches: int = 1,
    initial_disclosure_policy: str = "category_plus_one",
    min_turns_before_acceptance: int = 1,
    require_no_pending_question: bool = False,
    scheduled_variants: bool = False,
) -> list[ScenarioSpec]:
    """Build satisfiable need-based sessions from catalog metadata only."""

    persona_pool = persona_templates or list(PERSONA_TEMPLATES)
    unknown = sorted(set(persona_pool) - set(PERSONA_TEMPLATES))
    if unknown:
        raise ValueError(f"Unknown persona templates: {', '.join(unknown)}")
    candidates: list[tuple[Product, NeedBasedGoal]] = []
    for product in products:
        goal = _realistic_goal(
            product,
            budget_multiplier=budget_multiplier,
            min_soft_preferences=min_soft_preferences,
            min_soft_matches=min_soft_matches,
            source_dataset=(
                f"catalog_realistic_{difficulty_profile}"
                if difficulty_profile != "standard"
                else "catalog_realistic"
            ),
        )
        if scheduled_variants and goal is not None and not any(
            constraint.attribute == "budget_max"
            for constraint in goal.hard_constraints
        ):
            continue
        if goal is not None:
            candidates.append((product, goal))
    rng = random.Random(seed)
    rng.shuffle(candidates)
    scenarios: list[ScenarioSpec] = []
    for index, (product, goal) in enumerate(candidates[:count]):
        persona = persona_pool[index % len(persona_pool)]
        preference_tags = [constraint.attribute for constraint in goal.soft_preferences]
        variant = "hidden_preferences"
        scheduled_overrides: list[OverrideEvent] = []
        scheduled_relaxations: list[RelaxationEvent] = []
        scenario_min_turns = min_turns_before_acceptance
        if scheduled_variants:
            variant = (
                "hidden_preferences",
                "preference_override",
                "budget_relaxation",
                "override_and_relaxation",
            )[index % 4]
            if variant in {"preference_override", "override_and_relaxation"}:
                preference = goal.soft_preferences[0]
                scheduled_overrides.append(
                    OverrideEvent(2, preference.attribute, list(preference.values), [])
                )
                scenario_min_turns = max(scenario_min_turns, 3)
            if variant in {"budget_relaxation", "override_and_relaxation"}:
                budget = next(
                    constraint
                    for constraint in goal.hard_constraints
                    if constraint.attribute == "budget_max"
                )
                scheduled_relaxations.append(
                    RelaxationEvent(4, budget.attribute, list(budget.values), [])
                )
                scenario_min_turns = max(scenario_min_turns, 5)
        scenarios.append(
            ScenarioSpec(
                scenario_id=f"realistic_{index + 1:04d}_{product.product_id}",
                goal=goal,
                persona_template=persona,
                max_turns=max_turns,
                initial_disclosure_policy=initial_disclosure_policy,
                scheduled_overrides=scheduled_overrides,
                scheduled_relaxations=scheduled_relaxations,
                persona_driven_override_enabled=persona_driven_override_enabled,
                seed=_stable_seed(seed, product.product_id, persona),
                protocol="realistic",
                scenario_type=(
                    f"realistic_hard:{variant}"
                    if difficulty_profile != "standard"
                    else "realistic"
                ),
                user_profile={
                    "purchase_frequency": "3-4 prior purchases",
                    "average_prior_rating": 4.0,
                    "rating_style": "mixed",
                    "preference_tags": preference_tags,
                    "summary": f"Prior purchases emphasize {', '.join(preference_tags)}.",
                },
                metadata={
                    "seed_product_id": product.product_id,
                    "difficulty_profile": difficulty_profile,
                    "difficulty_variant": variant,
                },
                min_turns_before_acceptance=scenario_min_turns,
                require_no_pending_question=require_no_pending_question,
                difficulty_profile=difficulty_profile,
            )
        )
    if len(scenarios) < count:
        raise ValueError(f"Only {len(scenarios)} catalog products can seed realistic scenarios; requested {count}")
    return scenarios


class AmazonReviews2023Adapter:
    """Reads Amazon Reviews 2023 metadata JSONL after users download it locally."""

    def __init__(self, metadata_path: str | Path):
        self.metadata_path = Path(metadata_path)

    def load_products(self) -> Iterable[Product]:
        with self.metadata_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield normalize_amazon_product(json.loads(line))

    def build_target_goal(self, product: Product) -> TargetProductGoal:
        constraints: list[Constraint] = []
        if product.brand:
            constraints.append(Constraint("brand", [product.brand], "soft", relaxable=True, source="amazon_reviews_2023"))
        if product.price is not None:
            constraints.append(Constraint("budget_max", [str(product.price)], "hard", source="amazon_reviews_2023"))
        for attribute in ("color", "material", "size"):
            values = product.attributes.get(attribute, [])
            if values:
                constraints.append(Constraint(attribute, values[:1], "soft", relaxable=True, source="amazon_reviews_2023"))
        return TargetProductGoal(
            goal_id=f"amazon_reviews_2023:{product.product_id}",
            target_product_id=product.product_id,
            constraints=constraints,
            category=product.categories[-1] if product.categories else None,
            source_dataset="amazon_reviews_2023",
        )


class AmazonESCIAdapter:
    """Reads Amazon Shopping Queries / ESCI CSV data.

    Expected columns follow the public dataset naming convention where available:
    query, product_id or asin, and esci_label.
    """

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)

    def rows(self) -> Iterable[dict[str, str]]:
        with self.csv_path.open(encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)

    def build_need_goals(self, catalog: dict[str, Product], limit: int | None = None) -> list[NeedBasedGoal]:
        grouped: dict[str, list[dict[str, str]]] = {}
        for row in self.rows():
            query = row.get("query") or row.get("query_text") or ""
            if not query:
                continue
            grouped.setdefault(query, []).append(row)

        goals: list[NeedBasedGoal] = []
        for rows in grouped.values():
            exact_ids: list[str] = []
            substitute_ids: list[str] = []
            for row in rows:
                pid = str(row.get("product_id") or row.get("asin") or row.get("product_id_locale") or "").strip()
                label = str(row.get("esci_label") or row.get("label") or "").strip().lower()
                if pid not in catalog:
                    continue
                if label.startswith("e") or label == "exact":
                    exact_ids.append(pid)
                elif label.startswith("s") or label == "substitute":
                    substitute_ids.append(pid)
            if not exact_ids:
                continue
            seed_product = catalog[exact_ids[0]]
            hard: list[Constraint] = []
            soft: list[Constraint] = []
            if seed_product.categories:
                hard.append(Constraint("category", [seed_product.categories[-1]], "hard", source="amazon_esci"))
            if seed_product.brand:
                soft.append(Constraint("brand", [seed_product.brand], "soft", relaxable=True, source="amazon_esci"))
            alternatives: dict[str, list[str]] = {}
            brands = sorted({catalog[p].brand for p in substitute_ids if catalog[p].brand and catalog[p].brand != seed_product.brand})
            if brands:
                alternatives["brand"] = brands[:5]
            goals.append(
                NeedBasedGoal(
                    goal_id=f"esci:{len(goals)}",
                    category=seed_product.categories[-1] if seed_product.categories else None,
                    hard_constraints=hard,
                    soft_preferences=soft,
                    alternatives=alternatives,
                    min_soft_matches=0 if not soft else 1,
                    source_dataset="amazon_esci",
                )
            )
            if limit is not None and len(goals) >= limit:
                break
        return goals
