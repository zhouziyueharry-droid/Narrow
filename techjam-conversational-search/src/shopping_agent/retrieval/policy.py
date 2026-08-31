from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from shopping_agent.domain.product_text import _terms
from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.coarse import RetrievalIntent, RouteWeights


@dataclass(frozen=True)
class RetrievalPlan:
    """Per-turn retrieval budget and fusion policy.

    The controller uses only observable intent state. It does not inspect the
    hidden evaluation target, so the same decision is available in production
    and in an offline trace.
    """

    lexical_limit: int
    dense_limit: int
    attribute_limit: int
    fused_limit: int
    route_weights: RouteWeights
    specificity: float
    over_general: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


GENERIC_CATEGORIES = {
    "", "clothing", "clothing item", "fashion", "accessories", "product", "item",
}


def plan_retrieval(
    *,
    intent: RetrievalIntent,
    category: str,
    constraints: Iterable[Constraint],
    query: str,
) -> RetrievalPlan:
    active = [item for item in constraints if item.operator != "not_contains"]
    reliable_hard = sum(
        item.strength == "hard" and item.confidence >= 0.75 for item in active
    )
    structured = sum(
        item.field in {"material", "color", "size", "style", "brand", "budget", "feature", "use_case"}
        for item in active
    )
    query_signal = min(len(set(_terms(query))) / 8.0, 1.5)
    category_signal = 0.0 if category.strip().casefold() in GENERIC_CATEGORIES else 1.0
    specificity = round(
        category_signal + reliable_hard * 1.5 + (len(active) - reliable_hard) * 0.65 + query_signal,
        3,
    )
    over_general = category_signal == 0.0 and not active and len(set(_terms(query))) <= 3

    reasons = [f"intent:{intent}"]
    if over_general:
        reasons.append("clarify:over_general")
    if reliable_hard:
        reasons.append("targeted:reliable_hard_constraints")
    if structured >= 2:
        reasons.append("route:structured_evidence")

    if intent == "buying":
        weights = RouteWeights(
            lexical=1.0,
            dense=0.35,
            attribute=0.85 if structured >= 2 else 0.75,
        )
        return RetrievalPlan(360, 300, 360, 650, weights, specificity, over_general, tuple(reasons))
    if intent == "browsing":
        weights = RouteWeights(0.45, 1.0, 0.45)
        return RetrievalPlan(320, 360, 300, 650, weights, specificity, over_general, tuple(reasons))

    weights = RouteWeights(
        lexical=0.8,
        dense=0.75,
        attribute=0.65 if structured >= 2 else 0.55,
    )
    return RetrievalPlan(340, 300, 320, 625, weights, specificity, over_general, tuple(reasons))
