from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shopping_agent.dialogue.decision import decide_dialogue
from shopping_agent.dialogue.response_builder import build_agent_response
from shopping_agent.domain.product_text import _terms
from shopping_agent.domain.schemas import Constraint
from shopping_agent.domain.state import ShoppingState
from shopping_agent.ranking.interfaces import CandidateRanker
from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.coarse import (
    CoarseRankRequest,
    CoarseRanker,
    RouteWeights,
    infer_retrieval_intent,
)
from shopping_agent.retrieval.policy import plan_retrieval as build_retrieval_plan
from shopping_agent.retrieval.interfaces import SemanticRetriever
from shopping_agent.retrieval.lexical import CatalogIndex
from shopping_agent.understanding.interpreter import (
    StatePatch,
    apply_state_patch,
    resolve_semantic_patch,
    validate_state_patch,
)


ALLOWED_ATTRIBUTES = {
    "category", "material", "color", "size", "style", "brand",
    "budget", "feature", "use_case", "other",
}


def _constraint_text(constraint: Constraint) -> str:
    if constraint.field == "budget":
        return f"budget {constraint.value}"
    return str(constraint.value)


def _constraints(values: list[dict[str, Any]]) -> list[Constraint]:
    return [Constraint.model_validate(value) for value in values]


def _canonical_semantic_query(
    model_query: str,
    category: str,
    constraints: list[Constraint],
) -> str:
    """Preserve fluent model wording while guaranteeing complete active state."""

    parts = [model_query.strip()]
    current_terms = set(_terms(model_query.casefold()))
    required = [category]
    required.extend(
        _constraint_text(item)
        for item in constraints
        if item.operator != "not_contains"
    )
    for value in required:
        cleaned = str(value).strip()
        value_terms = set(_terms(cleaned.casefold()))
        if cleaned and (not value_terms or not value_terms.issubset(current_terms)):
            parts.append(cleaned)
            current_terms.update(value_terms)
    return " ".join(dict.fromkeys(part for part in parts if part)).strip()[:500]


def _retrieval_diagnostics(
    lexical: list[dict[str, Any]],
    dense: list[dict[str, Any]],
    attributes: list[dict[str, Any]],
    fused: list[dict[str, Any]],
) -> dict[str, Any]:
    route_sets = {
        "lexical": {str(item["parent_asin"]) for item in lexical},
        "dense": {str(item["parent_asin"]) for item in dense},
        "attribute": {str(item["parent_asin"]) for item in attributes},
    }
    union = set().union(*route_sets.values())
    membership: dict[str, int] = {}
    for values in route_sets.values():
        for parent_asin in values:
            membership[parent_asin] = membership.get(parent_asin, 0) + 1
    pairs: dict[str, float] = {}
    names = list(route_sets)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            combined = route_sets[left] | route_sets[right]
            pairs[f"{left}:{right}"] = round(
                len(route_sets[left] & route_sets[right]) / max(len(combined), 1), 4,
            )
    return {
        "route_counts": {name: len(values) for name, values in route_sets.items()},
        "route_union_count": len(union),
        "multi_route_count": sum(count >= 2 for count in membership.values()),
        "agreement_rate": round(
            sum(count >= 2 for count in membership.values()) / max(len(union), 1), 4,
        ),
        "pairwise_jaccard": pairs,
        "fused_count": len(fused),
    }


@dataclass
class ShoppingGraphNodes:
    """Bound graph-node implementations with explicit component dependencies."""

    catalog: CatalogIndex
    semantic_retriever: SemanticRetriever
    attribute_index: AttributeIndex
    coarse_ranker: CoarseRanker
    reranker: CandidateRanker

    def understand_user(self, state: ShoppingState) -> dict[str, Any]:
        patch, usage = resolve_semantic_patch(
            state.get("user_message", ""),
            int(state.get("turn", 1)),
            current_category=state.get("category", ""),
            active_constraints=state.get("active_constraints", []),
            current_semantic_query=state.get("semantic_query", ""),
            intent_summary=state.get("intent_summary", ""),
            user_profile=state.get("user_profile", {}),
            previous_ask_attribute=state.get("ask_attribute"),
            previous_question_options=state.get("question_options", []),
            conversation_history=state.get("conversation_history", []),
        )
        return {
            "semantic_patch": patch.model_dump(mode="json"),
            "semantic_confidence": patch.confidence,
            "semantic_fallback_reasons": patch.fallback_reasons,
            "semantic_usage": usage,
        }

    def validate_patch(self, state: ShoppingState) -> dict[str, Any]:
        patch = validate_state_patch(StatePatch.model_validate(state.get("semantic_patch", {})))
        return {
            "semantic_patch": patch.model_dump(mode="json"),
            "semantic_confidence": patch.confidence,
            "semantic_fallback_reasons": patch.fallback_reasons,
        }

    def update_state(self, state: ShoppingState) -> dict[str, Any]:
        patch = StatePatch.model_validate(state.get("semantic_patch", {}))
        active, superseded = apply_state_patch(
            list(state.get("active_constraints", [])),
            patch,
        )
        no_preference = set(state.get("no_preference", []))
        if patch.reset_scope == "all":
            no_preference.clear()
        no_preference.update(patch.no_preference)
        newly_specified = {item.field for item in patch.constraints}
        if patch.category:
            newly_specified.add("category")
        no_preference.difference_update(newly_specified)
        resolved_category = patch.category or (
            "" if patch.reset_scope == "all" else state.get("category", "")
        )
        if patch.parser == "deepseek":
            semantic_query = _canonical_semantic_query(
                patch.semantic_query,
                resolved_category,
                active,
            )
        else:
            fallback_parts = [resolved_category]
            fallback_parts.extend(
                _constraint_text(item)
                for item in active
                if item.operator != "not_contains"
            )
            semantic_query = " ".join(
                dict.fromkeys(part for part in fallback_parts if part)
            ).strip() or patch.semantic_query or state.get("semantic_query", "")
        question_history = list(state.get("question_history", []))
        pending = state.get("pending_question")
        remaining_pending = pending
        if pending:
            pending_attribute = str(pending.get("attribute", ""))
            answered_fields = {item.field for item in patch.constraints}
            answered_fields.update(patch.no_preference)
            answered_fields.update(patch.remove_fields)
            status = "answered" if pending_attribute in answered_fields else "unanswered"
            if status == "answered":
                remaining_pending = None
            if question_history and question_history[-1].get("status") == "pending":
                question_history[-1] = {**question_history[-1], "status": status}

        category_changed = bool(
            patch.category
            and state.get("category")
            and patch.category != state.get("category")
        )
        update: dict[str, Any] = {
            "category": resolved_category,
            "active_constraints": [item.model_dump() for item in active],
            "superseded_constraints": list(state.get("superseded_constraints", []))
            + [item.model_dump() for item in superseded],
            "no_preference": sorted(no_preference),
            "intent_changed": patch.action == "replace",
            "semantic_query": semantic_query,
            "model_semantic_query": patch.semantic_query,
            "intent_summary": patch.intent_summary
            or semantic_query
            or state.get("intent_summary", ""),
            "user_language": patch.language or state.get("user_language", "en"),
            "retrieval_attempt": 0,
            "constraints_relaxed": False,
            "pending_question": remaining_pending,
            "question_history": [] if category_changed or patch.reset_scope == "all" else question_history,
        }
        if patch.action == "replace" or patch.reset_scope == "all":
            update["recommended_asins"] = []
        if category_changed or patch.reset_scope == "all":
            update["asked_attributes"] = []
        return update

    def build_query(self, state: ShoppingState) -> dict[str, Any]:
        constraints = _constraints(state.get("active_constraints", []))
        parts = [state.get("category", "")]
        parts.extend(
            _constraint_text(item)
            for item in constraints
            if item.operator != "not_contains"
        )
        semantic_query = state.get("semantic_query", "").strip()
        if semantic_query:
            parts.append(semantic_query)
        lexical_query = " ".join(dict.fromkeys(part for part in parts if part)).strip()
        retrieval_intent = infer_retrieval_intent(
            state.get("semantic_patch", {}).get("retrieval_intent", "unknown")
            if state.get("semantic_patch", {}).get("parser") == "deepseek" else None,
            category=state.get("category", ""),
            constraints=constraints,
            message=state.get("user_message", ""),
        )
        return {
            "lexical_query": lexical_query,
            "search_query": semantic_query or lexical_query,
            "retrieval_intent": retrieval_intent,
        }

    def plan_retrieval(self, state: ShoppingState) -> dict[str, Any]:
        plan = build_retrieval_plan(
            intent=state.get("retrieval_intent", "unknown"),
            category=state.get("category", ""),
            constraints=_constraints(state.get("active_constraints", [])),
            query=state.get("semantic_query", "") or state.get("search_query", ""),
        )
        return {"retrieval_plan": plan.to_dict()}

    def lexical_retrieve(self, state: ShoppingState) -> dict[str, Any]:
        plan = state.get("retrieval_plan", {})
        return {
            "lexical_candidates": self.catalog.search(
                state.get("lexical_query", ""),
                constraints=[],
                limit=int(plan.get("lexical_limit", self.coarse_ranker.config.lexical_limit)),
            )
        }

    def dense_retrieve(self, state: ShoppingState) -> dict[str, Any]:
        plan = state.get("retrieval_plan", {})
        return {
            "dense_candidates": self.semantic_retriever.search(
                state.get("semantic_query", "") or state.get("search_query", ""),
                limit=int(plan.get("dense_limit", self.coarse_ranker.config.dense_limit)),
            )
        }

    def attribute_retrieve(self, state: ShoppingState) -> dict[str, Any]:
        plan = state.get("retrieval_plan", {})
        return {
            "attribute_candidates": self.attribute_index.search(
                state.get("category", ""),
                _constraints(state.get("active_constraints", [])),
                limit=int(plan.get("attribute_limit", self.coarse_ranker.config.attribute_limit)),
            )
        }

    def fuse_candidates(self, state: ShoppingState) -> dict[str, Any]:
        plan = state.get("retrieval_plan", {})
        raw_weights = plan.get("route_weights", {})
        route_weights = RouteWeights(
            lexical=float(raw_weights.get("lexical", 0.8)),
            dense=float(raw_weights.get("dense", 0.75)),
            attribute=float(raw_weights.get("attribute", 0.55)),
        )
        lexical = list(state.get("lexical_candidates", []))
        dense = list(state.get("dense_candidates", []))
        attributes = list(state.get("attribute_candidates", []))
        fused = self.coarse_ranker.rank_from_routes(
            CoarseRankRequest(
                query=state.get("semantic_query", "") or state.get("search_query", ""),
                message=state.get("user_message", ""),
                category=state.get("category", ""),
                intent=state.get("retrieval_intent", "unknown"),
                constraints=tuple(_constraints(state.get("active_constraints", []))),
                profile=state.get("user_profile", {}),
                limit=int(plan.get("fused_limit", self.coarse_ranker.config.fused_limit)),
                route_weights=route_weights,
                fused_limit=int(plan.get("fused_limit", self.coarse_ranker.config.fused_limit)),
            ),
            lexical=lexical,
            dense=dense,
            attributes=attributes,
        )
        return {
            "fused_candidates": fused,
            "retrieval_diagnostics": _retrieval_diagnostics(
                lexical, dense, attributes, fused,
            ),
        }

    def apply_constraints(self, state: ShoppingState) -> dict[str, Any]:
        # CoarseRanker already applies tri-state hard filtering and soft boosts.
        # Keep this graph boundary/node name stable for traces and routing.
        return {"filtered_candidates": list(state.get("fused_candidates", []))}

    def relax_and_backfill(self, state: ShoppingState) -> dict[str, Any]:
        constraints = _constraints(state.get("active_constraints", []))
        broad_query = state.get("category", "") or state.get("lexical_query", "")
        fallback = self.catalog.search(broad_query, constraints=constraints, limit=200)
        merged = list(state.get("filtered_candidates", []))
        seen = {str(item["parent_asin"]) for item in merged}
        for candidate in fallback:
            parent_asin = str(candidate["parent_asin"])
            if parent_asin not in seen:
                seen.add(parent_asin)
                merged.append({**candidate, "rrf_score": 0.0, "route_count": 1})
        return {
            "filtered_candidates": merged,
            "constraints_relaxed": True,
            "retrieval_attempt": int(state.get("retrieval_attempt", 0)) + 1,
        }

    def rerank(self, state: ShoppingState) -> dict[str, Any]:
        ranked = self.reranker.rank(
            state.get("filtered_candidates", []),
            query=state.get("semantic_query", "") or state.get("search_query", ""),
            category=state.get("category", ""),
            constraints=_constraints(state.get("active_constraints", [])),
            profile=state.get("user_profile", {}),
            previously_recommended=set(state.get("recommended_asins", [])),
        )
        return {"ranked_candidates": ranked}

    def select_question(self, state: ShoppingState) -> dict[str, Any]:
        top_ids = [
            str(item["parent_asin"])
            for item in state.get("ranked_candidates", [])[:50]
        ]
        candidate_attributes = self.attribute_index.candidate_attributes(top_ids)
        known_attributes = {
            item.field
            for item in _constraints(state.get("active_constraints", []))
            if item.operator != "not_contains"
        }
        if state.get("category"):
            known_attributes.add("category")
        decision, scores, options, usage = decide_dialogue(
            turn=int(state.get("turn", 1)),
            user_message=state.get("user_message", ""),
            conversation_history=list(state.get("conversation_history", [])),
            active_constraints=list(state.get("active_constraints", [])),
            pending_question=state.get("pending_question"),
            question_history=list(state.get("question_history", [])),
            ranked_candidates=list(state.get("ranked_candidates", [])),
            candidate_attributes=candidate_attributes,
            asked_attributes=list(state.get("asked_attributes", [])),
            no_preference=set(state.get("no_preference", [])),
            known_attributes=known_attributes,
            language=state.get("user_language", "en"),
            retrieval_context={
                "plan": state.get("retrieval_plan", {}),
                "diagnostics": state.get("retrieval_diagnostics", {}),
            },
        )
        attribute = str(decision.ask_attribute) if decision.ask_attribute else None
        asked = list(state.get("asked_attributes", []))
        history = list(state.get("question_history", []))
        pending_question = None
        if attribute:
            asked.append(attribute)
            pending_question = {
                "attribute": attribute,
                "options": options,
                "turn": int(state.get("turn", 1)),
            }
            history.append({**pending_question, "status": "pending"})
        return {
            "ask_attribute": attribute,
            "asked_attributes": asked,
            "question_scores": scores,
            "question_options": options,
            "candidate_count": len(state.get("ranked_candidates", [])),
            "pending_question": pending_question,
            "question_history": history,
            "dialogue_action": decision.action,
            "dialogue_reason": decision.reason,
            "dialogue_parser": decision.parser,
            "dialogue_model_output": decision.model_output,
            "dialogue_message": decision.message,
            "dialogue_usage": usage,
        }

    def build_response(self, state: ShoppingState) -> dict[str, Any]:
        return build_agent_response(state)

    def validate_response(self, state: ShoppingState) -> dict[str, Any]:
        errors: list[str] = []
        top_k = min(max(int(state.get("top_k", 10)), 1), 10)
        seen: set[str] = set()
        valid: list[dict[str, Any]] = []
        for item in state.get("recommendations", []):
            parent_asin = str(item.get("parent_asin", ""))
            if parent_asin in seen or parent_asin not in self.catalog.products:
                errors.append(f"invalid_or_duplicate:{parent_asin}")
                continue
            seen.add(parent_asin)
            valid.append(item)
            if len(valid) >= top_k:
                break
        attribute = state.get("ask_attribute")
        if attribute not in ALLOWED_ATTRIBUTES and attribute is not None:
            errors.append(f"invalid_attribute:{attribute}")
            attribute = None
        history = list(state.get("recommended_asins", []))
        history.extend(item["parent_asin"] for item in valid)
        return {
            "ask_attribute": attribute,
            "recommendations": valid,
            "recommended_asins": list(dict.fromkeys(history)),
            "errors": errors,
        }
