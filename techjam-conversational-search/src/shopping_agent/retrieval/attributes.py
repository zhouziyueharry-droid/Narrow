from __future__ import annotations

import heapq
from collections import defaultdict
from typing import Any, Iterable

from shopping_agent.domain.intent import COLORS, MATERIALS
from shopping_agent.domain.product_text import _text, _terms
from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.lexical import CatalogIndex


USE_CASES = {
    "running": {"run", "running", "jogging"},
    "fitness": {"gym", "fitness", "exercise", "workout", "training"},
    "winter": {"winter", "thermal", "warm", "insulated", "snow"},
    "outdoor": {"outdoor", "hiking", "trail", "camping"},
    "work": {"work", "office", "professional", "uniform"},
}

STYLES = {
    "casual": {"casual", "everyday", "relaxed"},
    "formal": {"formal", "dress", "dressy", "business"},
    "sport": {"sport", "athletic", "active", "performance"},
    "vintage": {"vintage", "retro", "classic"},
}

# Controlled, human-readable facets mined from otherwise unstructured catalog
# text. They deliberately map to the competition's generic ``feature`` field:
# the source catalog does not expose closure, pattern, occasion, fit and product
# properties as stable first-class columns.
FEATURES = {
    "pull on": {"pull on", "pull-on"},
    "zip": {"zip", "zipper", "zippered"},
    "button": {"button", "buttoned"},
    "lace up": {"lace up", "lace-up", "lacing"},
    "buckle": {"buckle", "buckled"},
    "hook and loop": {"hook and loop", "hook-and-loop", "velcro"},
    "slip on": {"slip on", "slip-on"},
    "floral": {"floral", "flower print"},
    "striped": {"striped", "stripe"},
    "plaid": {"plaid", "tartan"},
    "graphic": {"graphic", "graphic print"},
    "solid": {"solid", "solid color"},
    "animal print": {"animal print", "leopard print", "zebra print"},
    "waterproof": {"waterproof", "water resistant", "water-resistant"},
    "breathable": {"breathable", "ventilated"},
    "lightweight": {"lightweight", "light weight"},
    "stretch": {"stretch", "stretchy", "elastic"},
    "thermal": {"thermal", "insulated"},
    "slim fit": {"slim fit", "fitted"},
    "relaxed fit": {"relaxed fit", "loose fit", "oversized"},
    "party": {"party", "cocktail"},
    "wedding": {"wedding", "bridal"},
    "holiday": {"christmas", "holiday", "halloween"},
}

SIZE_ALIASES = {
    "small": {"small", " size s "},
    "medium": {"medium", " size m "},
    "large": {"large", " size l "},
    "x-large": {"x-large", "x large", "xl"},
    "plus size": {"plus size", "plus-size"},
    "wide": {"wide width", "wide fit"},
}


def _phrase_values(corpus: str, vocabulary: dict[str, set[str]]) -> set[str]:
    padded = f" {corpus} "
    return {
        normalized
        for normalized, variants in vocabulary.items()
        if any(f" {variant} " in padded for variant in variants)
    }


class AttributeIndex:
    """Structured apparel attribute index for retrieval and question entropy."""

    def __init__(self, catalog: CatalogIndex) -> None:
        self.catalog = catalog
        self.values: dict[str, dict[str, set[str]]] = {}
        self.postings: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        self.category_term_postings: dict[str, set[str]] = defaultdict(set)
        self._build()

    @staticmethod
    def _price_bucket(price: object) -> str | None:
        try:
            value = float(price)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if value < 25:
            return "under_25"
        if value < 50:
            return "25_to_50"
        if value < 100:
            return "50_to_100"
        if value < 200:
            return "100_to_200"
        return "over_200"

    def _extract(self, product: dict[str, Any]) -> dict[str, set[str]]:
        corpus = " ".join(
            _text(product.get(field))
            for field in ("title", "categories", "features", "details", "description", "store")
        ).casefold()
        words = set(_terms(corpus))
        attributes: dict[str, set[str]] = {
            "material": {item for item in MATERIALS if item in words},
            "color": {item for item in COLORS if item in words},
            "use_case": {name for name, vocabulary in USE_CASES.items() if words & vocabulary},
            "style": {name for name, vocabulary in STYLES.items() if words & vocabulary},
            "feature": _phrase_values(corpus, FEATURES),
            "size": _phrase_values(corpus, SIZE_ALIASES),
        }
        store = str(product.get("store") or "").strip().casefold()
        if store:
            attributes["brand"] = {store}
        categories = product.get("categories") or []
        if categories:
            attributes["category"] = {str(categories[-1]).strip().casefold()}
        bucket = self._price_bucket(product.get("price"))
        if bucket:
            attributes["budget"] = {bucket}
        return {field: values for field, values in attributes.items() if values}

    def _build(self) -> None:
        for parent_asin, product in self.catalog.products.items():
            attributes = self._extract(product)
            self.values[parent_asin] = attributes
            for field, values in attributes.items():
                for value in values:
                    self.postings[field][value].add(parent_asin)
                    if field == "category":
                        for term in _terms(value):
                            self.category_term_postings[term].add(parent_asin)

    def search(
        self,
        category: str,
        constraints: Iterable[Constraint],
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        scores: defaultdict[str, float] = defaultdict(float)
        category_terms = set(_terms(category))
        if category_terms:
            for term in category_terms:
                for parent_asin in self.category_term_postings.get(term, set()):
                    scores[parent_asin] += 1.0 / len(category_terms)

        for constraint in constraints:
            value = str(constraint.value).casefold()
            if constraint.field in {"material", "color"}:
                for normalized, parent_asins in self.postings[constraint.field].items():
                    if normalized in value or value in normalized:
                        for parent_asin in parent_asins:
                            scores[parent_asin] += 2.0
            elif constraint.field in {"style", "use_case", "brand", "size", "feature"}:
                for normalized, parent_asins in self.postings[constraint.field].items():
                    if normalized in value or value in normalized:
                        for parent_asin in parent_asins:
                            scores[parent_asin] += 1.8 if constraint.field == "feature" else 1.5

        best = heapq.nlargest(
            limit,
            scores.items(),
            key=lambda item: (
                item[1],
                int(self.catalog.products[item[0]].get("rating_number") or 0),
                item[0],
            ),
        )
        products = self.catalog.get_many([parent_asin for parent_asin, _ in best])
        for rank, (product, (_, score)) in enumerate(zip(products, best), start=1):
            product["attribute_rank"] = rank
            product["attribute_score"] = float(score)
        return products

    def candidate_attributes(self, parent_asins: Iterable[str]) -> list[dict[str, set[str]]]:
        return [self.values[parent_asin] for parent_asin in parent_asins if parent_asin in self.values]
