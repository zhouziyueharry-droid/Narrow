from __future__ import annotations

from .models import (
    AcceptanceResult,
    NeedBasedGoal,
    Product,
    Recommendation,
    ShoppingGoal,
    TargetProductGoal,
)


def _norm(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _product_values(product: Product, attribute: str) -> list[str]:
    if attribute == "category":
        return product.categories
    if attribute == "brand":
        return [product.brand] if product.brand else []
    if attribute in {"budget_max", "budget_min"}:
        return [str(product.price)] if product.price is not None else []
    return product.attributes.get(attribute, [])


def _matches(product: Product, attribute: str, values: list[str], alternatives: dict[str, list[str]]) -> bool:
    if not values:
        return False
    if attribute == "budget_max":
        return product.price is not None and product.price <= float(values[0])
    if attribute == "budget_min":
        return product.price is not None and product.price >= float(values[0])
    accepted_values = {_norm(v) for v in values + alternatives.get(attribute, [])}
    product_values = {_norm(v) for v in _product_values(product, attribute)}
    return bool(accepted_values & product_values)


class AcceptanceChecker:
    def __init__(self, catalog: dict[str, Product]):
        self.catalog = catalog

    def check(self, goal: ShoppingGoal, recommendations: list[Recommendation]) -> AcceptanceResult:
        if isinstance(goal, TargetProductGoal):
            for rank, rec in enumerate(recommendations, 1):
                if rec.product_id == goal.target_product_id:
                    return AcceptanceResult(True, rec.product_id, rank)
            return AcceptanceResult(False)

        assert isinstance(goal, NeedBasedGoal)
        active_hard = [c for c in goal.hard_constraints if c.active]
        active_soft = [c for c in goal.soft_preferences if c.active]
        best_near_miss: tuple[int, int, int, str] | None = None
        for rank, rec in enumerate(recommendations, 1):
            product = self.catalog.get(rec.product_id)
            if product is None:
                continue
            hard_total = len(active_hard)
            hard_matches = sum(
                _matches(product, c.attribute, c.values, goal.alternatives)
                for c in active_hard
            )
            soft_matches = sum(
                _matches(product, c.attribute, c.values, goal.alternatives)
                for c in active_soft
            )
            candidate = (hard_matches, soft_matches, -rank, rec.product_id)
            if best_near_miss is None or candidate[:3] > best_near_miss[:3]:
                best_near_miss = candidate
            if hard_matches == hard_total and soft_matches >= goal.min_soft_matches:
                return AcceptanceResult(
                    True,
                    rec.product_id,
                    rank,
                    hard_matches=hard_matches,
                    hard_total=hard_total,
                    soft_matches=soft_matches,
                    evidence={"mode": "need_based"},
                )
        hard_total = len(active_hard)
        if best_near_miss is None:
            return AcceptanceResult(
                False,
                hard_total=hard_total,
                evidence={"mode": "need_based", "reason": "no_valid_candidates"},
            )
        hard_matches, soft_matches, negative_rank, product_id = best_near_miss
        return AcceptanceResult(
            False,
            hard_matches=hard_matches,
            hard_total=hard_total,
            soft_matches=soft_matches,
            evidence={
                "mode": "need_based",
                "reason": "best_candidate_below_acceptance_threshold",
                "best_candidate_id": product_id,
                "best_candidate_rank": -negative_rank,
                "required_soft_matches": goal.min_soft_matches,
            },
        )
