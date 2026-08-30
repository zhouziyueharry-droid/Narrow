from __future__ import annotations

from typing import Any


CANDIDATE_KEYS = {
    "lexical_candidates",
    "dense_candidates",
    "attribute_candidates",
    "fused_candidates",
    "filtered_candidates",
    "ranked_candidates",
}

CANDIDATE_FIELDS = (
    "parent_asin", "title", "categories", "store", "price", "features",
    "average_rating", "rating_number", "lexical_rank", "lexical_score",
    "dense_rank", "dense_score", "attribute_rank", "attribute_score",
    "rrf_score", "route_count", "reranker_score", "reranker_explanation",
    "route_ranks", "route_weights", "retrieval_intent", "constraint_evidence",
    "constraint_boost", "coarse_score",
)


def compact_candidate(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    return {key: item[key] for key in CANDIDATE_FIELDS if key in item}


def compact_trace_values(
    values: dict[str, Any],
    candidate_limit: int,
) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, value in values.items():
        if key in CANDIDATE_KEYS and isinstance(value, list):
            compact[key] = {
                "count": len(value),
                "top": [compact_candidate(item) for item in value[:candidate_limit]],
            }
        elif key == "user_profile" and isinstance(value, dict):
            compact[key] = dict(value)
        elif isinstance(value, list) and len(value) > 100:
            compact[key] = {"count": len(value), "head": value[:100]}
        else:
            compact[key] = value
    return compact


def reconstruct_turn_trace(
    graph: Any,
    thread_id: str,
    turn: int,
    *,
    candidate_limit: int = 20,
) -> list[dict[str, Any]]:
    """Reconstruct compact node writes from adjacent LangGraph checkpoints."""

    config = {"configurable": {"thread_id": thread_id}}
    snapshots = [
        snapshot
        for snapshot in graph.get_state_history(config)
        if int(snapshot.values.get("turn", 0) or 0) == turn
    ]
    snapshots.sort(key=lambda item: int(item.metadata.get("step", -1)))
    trace: list[dict[str, Any]] = []
    for before, after in zip(snapshots, snapshots[1:]):
        nodes = [str(node) for node in before.next]
        if not nodes or nodes == ["__start__"]:
            continue
        changed = {
            key: value
            for key, value in after.values.items()
            if key not in before.values or before.values[key] != value
        }
        trace.append({
            "step": int(after.metadata.get("step", -1)),
            "nodes": nodes,
            "created_at": after.created_at,
            "updates": compact_trace_values(changed, candidate_limit),
        })
    return trace
