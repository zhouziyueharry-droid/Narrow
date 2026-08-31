from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Literal

from shopping_agent.domain.product_text import _number, _terms, _text
from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.interfaces import SemanticRetriever
from shopping_agent.retrieval.lexical import CatalogIndex


RetrievalIntent = Literal["buying", "browsing", "unknown"]


class ConstraintMatch(str, Enum):
    """Three-state constraint evidence from incomplete catalog metadata."""

    MATCH = "match"
    VIOLATE = "violate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RouteWeights:
    lexical: float
    dense: float
    attribute: float


@dataclass(frozen=True)
class CoarseRankerConfig:
    """Runtime policy for multi-route coarse ranking.

    Route limits deliberately exceed the final candidate count: recall is the
    coarse ranker's job, while the downstream ranker is responsible for final
    precision. RRF is used because lexical, vector, and attribute scores are on
    incompatible scales.
    """

    lexical_limit: int = 300
    dense_limit: int = 250
    attribute_limit: int = 250
    fused_limit: int = 500
    output_limit: int = 100
    rrf_rank_constant: float = 60.0
    buying_weights: RouteWeights = RouteWeights(lexical=1.0, dense=0.35, attribute=0.75)
    browsing_weights: RouteWeights = RouteWeights(lexical=0.45, dense=1.0, attribute=0.45)
    unknown_weights: RouteWeights = RouteWeights(lexical=0.8, dense=0.75, attribute=0.55)
    hard_confidence: float = 0.75
    soft_match_boost: float = 0.0035
    hard_match_boost: float = 0.0015
    unknown_hard_penalty: float = 0.0004
    quality_tiebreak_weight: float = 0.00008
    diversity_lambda: float = 0.86
    diversity_pool: int = 80
    category_cap: int = 5
    diversify_browsing: bool = False


@dataclass(frozen=True)
class CoarseRankRequest:
    query: str
    message: str = ""
    category: str = ""
    intent: RetrievalIntent = "unknown"
    constraints: tuple[Constraint, ...] = ()
    profile: dict[str, Any] = field(default_factory=dict)
    limit: int | None = None
    route_weights: RouteWeights | None = None
    fused_limit: int | None = None


def infer_retrieval_intent(
    intent: str | None,
    *,
    category: str,
    constraints: Iterable[Constraint],
    message: str = "",
) -> RetrievalIntent:
    """Normalize an upstream route, with a deterministic fallback.

    The fallback is intentionally conservative. Multiple reliable hard
    constraints are evidence of a targeted buying query; otherwise the ranker
    preserves a balanced route mix.
    """

    normalized = str(intent or "").strip().casefold()
    if normalized == "unknown":
        return "unknown"
    if normalized in {"buying", "buy", "targeted", "high_intent"}:
        return "buying"
    if normalized in {"browsing", "browse", "explore", "open_ended"}:
        return "browsing"
    message_text = message.strip().casefold()
    browsing_markers = (
        "still exploring", "just browsing", "not sure", "open to",
        "some ideas", "recommend something", "show me options",
    )
    if any(marker in message_text for marker in browsing_markers):
        return "browsing"
    if "a key requirement is:" in message_text:
        return "buying"
    reliable_hard = sum(
        item.strength == "hard" and item.confidence >= 0.75
        for item in constraints
    )
    if category and reliable_hard >= 1:
        return "buying"
    return "unknown"


def _product_corpus(product: dict[str, Any], *, structured_only: bool = False) -> str:
    fields = ("title", "categories", "store", "details") if structured_only else (
        "title", "categories", "store", "features", "details", "description"
    )
    return " ".join(_text(product.get(name)) for name in fields).casefold()


def _tokens(value: object) -> set[str]:
    return set(_terms(_text(value).casefold()))


def _contains_value(corpus: str, requested: object) -> bool:
    value = _text(requested).strip().casefold()
    if not value:
        return False
    if value in corpus:
        return True
    requested_terms = _tokens(value)
    return bool(requested_terms) and requested_terms.issubset(set(_terms(corpus)))


def evaluate_constraint(product: dict[str, Any], constraint: Constraint) -> ConstraintMatch:
    """Return MATCH, VIOLATE, or UNKNOWN without treating missing data as false."""

    field = constraint.field
    operator = constraint.operator
    if field == "budget":
        raw_price = product.get("price")
        if raw_price is None or raw_price == "":
            return ConstraintMatch.UNKNOWN
        price = _number(raw_price)
        target = _number(constraint.value)
        if price is None or target is None or not isfinite(price) or not isfinite(target):
            return ConstraintMatch.UNKNOWN
        if operator == "lte":
            return ConstraintMatch.MATCH if price <= target else ConstraintMatch.VIOLATE
        if operator == "gte":
            return ConstraintMatch.MATCH if price >= target else ConstraintMatch.VIOLATE
        if operator == "eq":
            return ConstraintMatch.MATCH if price == target else ConstraintMatch.VIOLATE
        return ConstraintMatch.UNKNOWN

    if field == "category":
        evidence = f"{_text(product.get('categories'))} {_text(product.get('title'))}".casefold()
    elif field == "brand":
        evidence = f"{_text(product.get('store'))} {_text(product.get('title'))}".casefold()
    else:
        evidence = _product_corpus(product)

    if not evidence.strip():
        return ConstraintMatch.UNKNOWN

    contains = _contains_value(evidence, constraint.value)
    if operator == "not_contains":
        return ConstraintMatch.VIOLATE if contains else ConstraintMatch.UNKNOWN
    if contains:
        return ConstraintMatch.MATCH

    # Only reliable structured fields justify a positive contradiction. Free
    # text not mentioning a color/material/style is missing evidence, not proof
    # that the product violates the request.
    if field in {"category", "brand"}:
        structured = _product_corpus(product, structured_only=True)
        return ConstraintMatch.VIOLATE if structured.strip() else ConstraintMatch.UNKNOWN
    return ConstraintMatch.UNKNOWN


class CoarseRanker:
    """Independent multi-route retrieval and coarse-ranking pipeline."""

    def __init__(
        self,
        catalog: CatalogIndex,
        semantic_retriever: SemanticRetriever,
        attribute_index: AttributeIndex | None = None,
        config: CoarseRankerConfig | None = None,
    ) -> None:
        self.catalog = catalog
        self.semantic_retriever = semantic_retriever
        self.attribute_index = attribute_index or AttributeIndex(catalog)
        self.config = config or CoarseRankerConfig()

    def rank(self, request: CoarseRankRequest) -> list[dict[str, Any]]:
        constraints = list(request.constraints)
        intent = infer_retrieval_intent(
            request.intent,
            category=request.category,
            constraints=constraints,
            message=request.message,
        )
        weights = request.route_weights or self._weights(intent)
        lexical_query = self._lexical_query(request)
        semantic_query = request.query.strip() or lexical_query

        lexical = self.catalog.search(
            lexical_query,
            constraints=[],
            limit=self.config.lexical_limit,
        ) if weights.lexical > 0.0 else []
        dense = self.semantic_retriever.search(
            semantic_query,
            limit=self.config.dense_limit,
        ) if weights.dense > 0.0 else []
        attributes = self.attribute_index.search(
            request.category,
            constraints,
            limit=self.config.attribute_limit,
        ) if weights.attribute > 0.0 else []

        return self.rank_from_routes(
            request,
            lexical=lexical,
            dense=dense,
            attributes=attributes,
        )

    def rank_from_routes(
        self,
        request: CoarseRankRequest,
        *,
        lexical: list[dict[str, Any]],
        dense: list[dict[str, Any]],
        attributes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fuse already-retrieved routes inside the LangGraph pipeline."""

        constraints = list(request.constraints)
        intent = infer_retrieval_intent(
            request.intent,
            category=request.category,
            constraints=constraints,
            message=request.message,
        )
        weights = request.route_weights or self._weights(intent)
        fused = self._fuse(
            (("lexical", lexical, weights.lexical),
             ("dense", dense, weights.dense),
             ("attribute", attributes, weights.attribute)),
            limit=request.fused_limit,
        )
        scored = self._apply_constraints_and_boosts(fused, constraints, intent)
        scored.sort(key=self._sort_key)

        limit = request.limit or self.config.output_limit
        if self.config.diversify_browsing and intent == "browsing" and len(scored) > limit:
            scored = self._diversify(scored, limit)
        route_weights = {
            "lexical": weights.lexical,
            "dense": weights.dense,
            "attribute": weights.attribute,
        }
        return [
            {**item, "retrieval_intent": intent, "route_weights": route_weights}
            for item in scored[:limit]
        ]

    def _weights(self, intent: RetrievalIntent) -> RouteWeights:
        if intent == "buying":
            return self.config.buying_weights
        if intent == "browsing":
            return self.config.browsing_weights
        return self.config.unknown_weights

    @staticmethod
    def _lexical_query(request: CoarseRankRequest) -> str:
        parts = [request.category, request.query]
        parts.extend(
            _text(item.value)
            for item in request.constraints
            if item.operator != "not_contains"
        )
        return " ".join(dict.fromkeys(item.strip() for item in parts if item.strip()))

    def _fuse(
        self,
        routes: Iterable[tuple[str, list[dict[str, Any]], float]],
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        fused: dict[str, dict[str, Any]] = {}
        for route_name, candidates, weight in routes:
            for rank, candidate in enumerate(candidates, start=1):
                parent_asin = str(candidate["parent_asin"])
                item = fused.setdefault(parent_asin, {
                    **candidate,
                    "rrf_score": 0.0,
                    "route_count": 0,
                    "route_ranks": {},
                    "route_scores": {},
                })
                for key, value in candidate.items():
                    item.setdefault(key, value)
                item["rrf_score"] += weight / (self.config.rrf_rank_constant + rank)
                item["route_count"] += 1
                item["route_ranks"][route_name] = rank
                raw_score = candidate.get(f"{route_name}_score")
                if raw_score is None and route_name == "dense":
                    raw_score = candidate.get("dense_score")
                if raw_score is not None:
                    item["route_scores"][route_name] = float(raw_score)
        return sorted(
            fused.values(),
            key=lambda item: (-float(item["rrf_score"]), -int(item["route_count"])),
        )[:limit or self.config.fused_limit]

    def _apply_constraints_and_boosts(
        self,
        candidates: list[dict[str, Any]],
        constraints: list[Constraint],
        intent: RetrievalIntent,
    ) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for candidate in candidates:
            source = self.catalog.products.get(str(candidate["parent_asin"]), candidate)
            evidence: dict[str, str] = {}
            hard_violation = False
            boost = 0.0
            for constraint in constraints:
                match = evaluate_constraint(source, constraint)
                key = f"{constraint.field}:{constraint.operator}:{constraint.value}"
                evidence[key] = match.value
                reliable_hard = (
                    constraint.strength == "hard"
                    and constraint.confidence >= self.config.hard_confidence
                )
                if reliable_hard and match is ConstraintMatch.VIOLATE:
                    hard_violation = True
                    break
                if match is ConstraintMatch.MATCH:
                    coefficient = (
                        self.config.hard_match_boost
                        if reliable_hard else self.config.soft_match_boost
                    )
                    boost += coefficient * constraint.confidence
                elif reliable_hard and match is ConstraintMatch.UNKNOWN and intent == "buying":
                    boost -= self.config.unknown_hard_penalty * constraint.confidence
            if hard_violation:
                continue
            quality = self._quality(source)
            coarse_score = float(candidate["rrf_score"]) + boost
            output.append({
                **candidate,
                "constraint_evidence": evidence,
                "constraint_boost": boost,
                "quality_tiebreak": quality,
                "coarse_score": coarse_score,
            })
        return output

    @staticmethod
    def _quality(product: dict[str, Any]) -> float:
        rating = _number(product.get("average_rating") or 0.0) or 0.0
        count = _number(product.get("rating_number") or 0.0) or 0.0
        return min(max(rating / 5.0, 0.0), 1.0) * min(count / 500.0, 1.0)

    def _sort_key(self, item: dict[str, Any]) -> tuple[float, float, int, str]:
        adjusted = float(item["coarse_score"]) + (
            self.config.quality_tiebreak_weight * float(item.get("quality_tiebreak", 0.0))
        )
        return (-adjusted, -float(item["rrf_score"]), -int(item["route_count"]), str(item["parent_asin"]))

    def _diversify(self, candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        """Light category-aware MMR over the best fused candidates.

        Product-to-product similarity uses semantic tokens already available in
        the catalog, avoiding a second model call and keeping this component
        usable with any SemanticRetriever implementation.
        """

        pool = candidates[: max(limit, self.config.diversity_pool)]
        selected: list[dict[str, Any]] = []
        remaining = list(pool)
        token_cache: dict[str, set[str]] = {}
        category_counts: dict[str, int] = {}
        best_score = max(float(item["coarse_score"]) for item in pool) or 1.0
        worst_score = min(float(item["coarse_score"]) for item in pool)
        scale = max(best_score - worst_score, 1e-12)

        while remaining and len(selected) < limit:
            best_index = 0
            best_value = float("-inf")
            for index, candidate in enumerate(remaining):
                category = self._leaf_category(candidate)
                if category and category_counts.get(category, 0) >= self.config.category_cap:
                    continue
                relevance = (float(candidate["coarse_score"]) - worst_score) / scale
                redundancy = max(
                    (self._candidate_similarity(candidate, prior, token_cache) for prior in selected),
                    default=0.0,
                )
                value = (
                    self.config.diversity_lambda * relevance
                    - (1.0 - self.config.diversity_lambda) * redundancy
                )
                if value > best_value:
                    best_value = value
                    best_index = index
            chosen = remaining.pop(best_index)
            category = self._leaf_category(chosen)
            if category:
                category_counts[category] = category_counts.get(category, 0) + 1
            chosen = {**chosen, "diversity_score": best_value}
            selected.append(chosen)
        if len(selected) < limit:
            seen = {str(item["parent_asin"]) for item in selected}
            selected.extend(item for item in candidates if str(item["parent_asin"]) not in seen)
        return selected[:limit]

    @staticmethod
    def _leaf_category(candidate: dict[str, Any]) -> str:
        categories = candidate.get("categories") or []
        if isinstance(categories, list) and categories:
            return str(categories[-1]).strip().casefold()
        return ""

    def _candidate_similarity(
        self,
        left: dict[str, Any],
        right: dict[str, Any],
        cache: dict[str, set[str]],
    ) -> float:
        def tokens(candidate: dict[str, Any]) -> set[str]:
            parent_asin = str(candidate["parent_asin"])
            if parent_asin not in cache:
                source = self.catalog.products.get(parent_asin, candidate)
                cache[parent_asin] = _tokens(
                    f"{_text(source.get('title'))} {_text(source.get('categories'))}"
                )
            return cache[parent_asin]

        left_terms = tokens(left)
        right_terms = tokens(right)
        union = left_terms | right_terms
        return len(left_terms & right_terms) / len(union) if union else 0.0
