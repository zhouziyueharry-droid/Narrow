"""Replaceable lexical, semantic, attribute, and fusion retrieval components."""

from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.coarse import (
    CoarseRanker,
    CoarseRankerConfig,
    CoarseRankRequest,
    ConstraintMatch,
    RouteWeights,
    evaluate_constraint,
    infer_retrieval_intent,
)
from shopping_agent.retrieval.embedding import SentenceTransformerDenseIndex
from shopping_agent.retrieval.fusion import reciprocal_rank_fusion
from shopping_agent.retrieval.interfaces import SemanticRetriever
from shopping_agent.retrieval.lexical import CatalogIndex
from shopping_agent.retrieval.policy import RetrievalPlan, plan_retrieval
from shopping_agent.retrieval.semantic import LocalDenseIndex

__all__ = [
    "AttributeIndex",
    "CatalogIndex",
    "CoarseRanker",
    "CoarseRankerConfig",
    "CoarseRankRequest",
    "ConstraintMatch",
    "LocalDenseIndex",
    "RouteWeights",
    "RetrievalPlan",
    "SemanticRetriever",
    "SentenceTransformerDenseIndex",
    "evaluate_constraint",
    "infer_retrieval_intent",
    "plan_retrieval",
    "reciprocal_rank_fusion",
]
