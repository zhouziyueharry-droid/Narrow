from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.coarse import (
    CoarseRanker,
    CoarseRankerConfig,
    CoarseRankRequest,
    ConstraintMatch,
    evaluate_constraint,
)
from shopping_agent.retrieval.lexical import CatalogIndex


PRODUCTS = [
    {
        "parent_asin": "OFFICE",
        "title": "Black leather office loafer",
        "categories": ["Shoes", "Women's Loafers"],
        "store": "Acme",
        "price": 79.0,
        "features": ["professional", "comfortable"],
        "details": {"Color": "Black", "Material": "Leather"},
        "description": ["A polished work shoe"],
        "average_rating": 4.6,
        "rating_number": 500,
    },
    {
        "parent_asin": "TRAIL",
        "title": "Waterproof hiking boot",
        "categories": ["Shoes", "Hiking Boots"],
        "store": "TrailCo",
        "price": 120.0,
        "features": ["waterproof", "rugged outdoor sole"],
        "details": {"Color": "Brown"},
        "description": ["Built for mountain trails"],
        "average_rating": 4.8,
        "rating_number": 900,
    },
    {
        "parent_asin": "UNKNOWN_MATERIAL",
        "title": "Minimal office flat",
        "categories": ["Shoes", "Women's Flats"],
        "store": "Acme",
        "price": None,
        "features": ["simple workwear"],
        "details": {"Color": "Black"},
        "description": [],
        "average_rating": 4.0,
        "rating_number": 50,
    },
    {
        "parent_asin": "RED_LOAFER",
        "title": "Red office loafer",
        "categories": ["Shoes", "Women's Loafers"],
        "store": "Other",
        "price": 60.0,
        "features": ["professional"],
        "details": {"Color": "Red"},
        "description": [],
        "average_rating": 4.2,
        "rating_number": 100,
    },
]


class FakeDenseRetriever:
    def __init__(self, catalog: CatalogIndex) -> None:
        self.catalog = catalog

    def search(self, query: str, limit: int = 200) -> list[dict[str, Any]]:
        order = ["TRAIL", "UNKNOWN_MATERIAL", "OFFICE", "RED_LOAFER"][:limit]
        products = self.catalog.get_many(order)
        for rank, product in enumerate(products, start=1):
            product["dense_rank"] = rank
            product["dense_score"] = 1.0 / rank
        return products


@pytest.fixture()
def catalog(tmp_path: Path) -> CatalogIndex:
    path = tmp_path / "catalog.jsonl"
    path.write_text(
        "".join(json.dumps(product) + "\n" for product in PRODUCTS),
        encoding="utf-8",
    )
    return CatalogIndex(path)


def make_ranker(catalog: CatalogIndex, **config: Any) -> CoarseRanker:
    return CoarseRanker(
        catalog,
        FakeDenseRetriever(catalog),
        AttributeIndex(catalog),
        CoarseRankerConfig(**config),
    )


def test_constraint_evidence_keeps_missing_metadata_unknown() -> None:
    product = PRODUCTS[2]
    assert evaluate_constraint(
        product,
        Constraint(field="material", value="leather", strength="hard"),
    ) is ConstraintMatch.UNKNOWN
    assert evaluate_constraint(
        product,
        Constraint(field="budget", operator="lte", value=80, strength="hard"),
    ) is ConstraintMatch.UNKNOWN


def test_explicit_hard_violations_are_filtered_but_unknowns_survive(catalog: CatalogIndex) -> None:
    results = make_ranker(catalog).rank(CoarseRankRequest(
        query="black office shoes",
        category="shoes",
        intent="buying",
        constraints=(
            Constraint(field="budget", operator="lte", value=80, strength="hard"),
            Constraint(field="brand", value="Acme", strength="hard"),
        ),
    ))
    asins = [item["parent_asin"] for item in results]
    assert "TRAIL" not in asins
    assert "RED_LOAFER" not in asins
    assert "OFFICE" in asins
    assert "UNKNOWN_MATERIAL" in asins


def test_soft_constraint_boost_is_explainable(catalog: CatalogIndex) -> None:
    results = make_ranker(catalog).rank(CoarseRankRequest(
        query="office loafer",
        intent="unknown",
        constraints=(Constraint(field="color", value="black", strength="soft"),),
    ))
    office = next(item for item in results if item["parent_asin"] == "OFFICE")
    red = next(item for item in results if item["parent_asin"] == "RED_LOAFER")
    assert office["constraint_boost"] > red["constraint_boost"]
    assert office["constraint_evidence"]["color:contains:black"] == "match"


def test_route_weights_change_between_buying_and_browsing(catalog: CatalogIndex) -> None:
    ranker = make_ranker(catalog)
    buying = ranker.rank(CoarseRankRequest(query="black leather", intent="buying"))
    browsing = ranker.rank(CoarseRankRequest(query="black leather", intent="browsing"))
    assert buying[0]["parent_asin"] == "OFFICE"
    assert browsing[0]["parent_asin"] != "OFFICE"
    assert buying[0]["route_ranks"]["lexical"] == 1
    assert browsing[0]["route_ranks"]["dense"] <= 2


def test_browsing_diversification_exposes_another_leaf_category(catalog: CatalogIndex) -> None:
    ranker = make_ranker(
        catalog,
        output_limit=3,
        diversity_pool=4,
        diversity_lambda=0.5,
        category_cap=1,
        diversify_browsing=True,
    )
    results = ranker.rank(CoarseRankRequest(
        query="office or outdoor shoes",
        intent="browsing",
        limit=3,
    ))
    leaf_categories = [item["categories"][-1] for item in results[:2]]
    assert len(set(leaf_categories)) == 2
    assert all("diversity_score" in item for item in results)
