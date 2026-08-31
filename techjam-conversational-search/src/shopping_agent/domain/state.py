from __future__ import annotations

from typing import Any, TypedDict

class ShoppingState(TypedDict, total=False):
    session_id: str
    turn: int
    top_k: int
    user_message: str
    user_profile: dict[str, Any]
    category: str
    # Constraints are checkpointed as plain dictionaries. This keeps LangGraph
    # serialization portable and avoids allowing arbitrary application classes.
    active_constraints: list[dict[str, Any]]
    superseded_constraints: list[dict[str, Any]]
    no_preference: list[str]
    asked_attributes: list[str]
    pending_question: dict[str, Any] | None
    question_history: list[dict[str, Any]]
    conversation_history: list[dict[str, str]]
    intent_changed: bool
    semantic_patch: dict[str, Any]
    semantic_confidence: float
    semantic_fallback_reasons: list[str]
    semantic_usage: dict[str, int]
    semantic_query: str
    model_semantic_query: str
    intent_summary: str
    user_language: str
    lexical_query: str
    search_query: str
    retrieval_intent: str
    retrieval_plan: dict[str, Any]
    retrieval_diagnostics: dict[str, Any]
    lexical_candidates: list[dict[str, Any]]
    dense_candidates: list[dict[str, Any]]
    attribute_candidates: list[dict[str, Any]]
    fused_candidates: list[dict[str, Any]]
    filtered_candidates: list[dict[str, Any]]
    ranked_candidates: list[dict[str, Any]]
    retrieval_attempt: int
    constraints_relaxed: bool
    recommended_asins: list[str]
    ask_attribute: str | None
    question_scores: dict[str, float]
    question_options: list[dict[str, Any]]
    candidate_count: int
    dialogue_action: str
    dialogue_reason: str
    dialogue_parser: str
    dialogue_model_output: dict[str, Any]
    dialogue_message: str
    dialogue_usage: dict[str, int]
    response_message: str
    recommendations: list[dict[str, Any]]
    usage: dict[str, int]
    errors: list[str]
