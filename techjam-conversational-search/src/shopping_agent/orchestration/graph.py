from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from shopping_agent.domain.state import ShoppingState
from shopping_agent.orchestration.nodes import ShoppingGraphNodes
from shopping_agent.orchestration.routing import route_after_filter
from shopping_agent.ranking.precise import PreciseReranker
from shopping_agent.ranking.interfaces import CandidateRanker
from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.coarse import CoarseRanker
from shopping_agent.retrieval.embedding import SentenceTransformerDenseIndex
from shopping_agent.retrieval.interfaces import SemanticRetriever
from shopping_agent.retrieval.lexical import CatalogIndex
from shopping_agent.retrieval.semantic import LocalDenseIndex


def build_shopping_graph(
    model: str | BaseChatModel | None = None,
    catalog_path: str | Path = "data/catalog.jsonl",
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    managed_persistence: bool = False,
    semantic_retriever: SemanticRetriever | None = None,
    reranker: CandidateRanker | None = None,
    catalog_index: CatalogIndex | None = None,
):
    """Assemble the real-user shopping graph from replaceable components."""

    del model
    catalog = catalog_index or CatalogIndex(catalog_path)
    attribute_index = AttributeIndex(catalog)
    if semantic_retriever is None:
        dense_backend = os.getenv("SHOPPING_DENSE_BACKEND", "local").strip().casefold()
        if dense_backend in {"bge", "sentence-transformer", "sentence_transformer"}:
            semantic_retriever = SentenceTransformerDenseIndex(
                catalog,
                model_name=os.getenv(
                    "SHOPPING_EMBEDDING_MODEL",
                    "BAAI/bge-small-en-v1.5",
                ),
                cache_dir=os.getenv(
                    "SHOPPING_EMBEDDING_CACHE",
                    ".cache/coarse_retrieval",
                ),
                use_faiss=os.getenv("SHOPPING_DENSE_USE_FAISS", "false").strip().casefold()
                in {"1", "true", "yes", "on"},
            )
        elif dense_backend == "local":
            semantic_retriever = LocalDenseIndex(catalog)
        else:
            raise ValueError(
                "SHOPPING_DENSE_BACKEND must be 'local' or 'bge', "
                f"got {dense_backend!r}"
            )
    coarse_ranker = CoarseRanker(catalog, semantic_retriever, attribute_index)
    nodes = ShoppingGraphNodes(
        catalog=catalog,
        semantic_retriever=semantic_retriever,
        attribute_index=attribute_index,
        coarse_ranker=coarse_ranker,
        reranker=reranker if reranker is not None else PreciseReranker(catalog_products=catalog.products),
    )

    builder = StateGraph(ShoppingState)
    builder.add_node("understand_user", nodes.understand_user)
    builder.add_node("validate_patch", nodes.validate_patch)
    builder.add_node("update_state", nodes.update_state)
    builder.add_node("build_query", nodes.build_query)
    builder.add_node("plan_retrieval", nodes.plan_retrieval)
    builder.add_node("lexical_retrieve", nodes.lexical_retrieve)
    builder.add_node("dense_retrieve_fallback", nodes.dense_retrieve)
    builder.add_node("attribute_retrieve", nodes.attribute_retrieve)
    builder.add_node("rrf_fusion", nodes.fuse_candidates)
    builder.add_node("constraint_filter", nodes.apply_constraints)
    builder.add_node("relax_and_backfill", nodes.relax_and_backfill)
    builder.add_node("rerank_fallback", nodes.rerank)
    builder.add_node("information_gain_question", nodes.select_question)
    builder.add_node("build_response", nodes.build_response)
    builder.add_node("validate_response", nodes.validate_response)

    builder.add_edge(START, "understand_user")
    builder.add_edge("understand_user", "validate_patch")
    builder.add_edge("validate_patch", "update_state")
    builder.add_edge("update_state", "build_query")
    builder.add_edge("build_query", "plan_retrieval")
    builder.add_edge("plan_retrieval", "lexical_retrieve")
    builder.add_edge("plan_retrieval", "dense_retrieve_fallback")
    builder.add_edge("plan_retrieval", "attribute_retrieve")
    builder.add_edge(
        ["lexical_retrieve", "dense_retrieve_fallback", "attribute_retrieve"],
        "rrf_fusion",
    )
    builder.add_edge("rrf_fusion", "constraint_filter")
    builder.add_conditional_edges(
        "constraint_filter",
        route_after_filter,
        {
            "relax_and_backfill": "relax_and_backfill",
            "rerank": "rerank_fallback",
        },
    )
    builder.add_edge("relax_and_backfill", "rerank_fallback")
    builder.add_edge("rerank_fallback", "information_gain_question")
    builder.add_edge("information_gain_question", "build_response")
    builder.add_edge("build_response", "validate_response")
    builder.add_edge("validate_response", END)

    saver = None if managed_persistence else (checkpointer or InMemorySaver())
    return builder.compile(checkpointer=saver)
