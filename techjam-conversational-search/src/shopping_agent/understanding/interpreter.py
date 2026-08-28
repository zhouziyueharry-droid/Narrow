from __future__ import annotations

import re
from typing import Any, Literal

from shopping_agent.domain.schemas import Constraint
from shopping_agent.infrastructure.llm.deepseek import (
    DeepSeekInvalidResponse,
    is_configured,
    request_state_patch,
)
from shopping_agent.understanding.fallback_parser import (
    rule_state_patch,
    semantic_fallback_patch,
)
from shopping_agent.understanding.prompts import DEEPSEEK_SYSTEM_PROMPT
from shopping_agent.understanding.state_patch import (
    StatePatch,
    apply_state_patch,
    validate_state_patch,
)


def _detect_language(message: str) -> Literal["zh", "en", "other"]:
    if re.search(r"[\u3400-\u9fff]", message):
        return "zh"
    if re.search(r"[a-z]", message, re.IGNORECASE):
        return "en"
    return "other"


def _fallback_semantic_query(
    message: str,
    category: str | None,
    constraints: list[Constraint],
) -> str:
    positive = [
        str(item.value)
        for item in constraints
        if item.operator != "not_contains" and item.field != "budget"
    ]
    parts = [category or "", *positive]
    if not any(parts):
        cleaned = re.sub(r"\s+", " ", message).strip()
        return cleaned[:500]
    return " ".join(
        dict.fromkeys(part.strip() for part in parts if part.strip())
    )[:500]


OVERRIDE_SENSITIVE_FIELDS = {"color", "material", "size", "style", "brand", "use_case"}


def _has_conflicting_value(
    active_constraints: list[dict[str, Any]],
    incoming: list[Constraint],
) -> bool:
    active_by_field: dict[str, set[str]] = {}
    for value in active_constraints:
        if value.get("operator") == "not_contains":
            continue
        active_by_field.setdefault(str(value.get("field", "")), set()).add(
            str(value.get("value", "")).casefold()
        )
    for item in incoming:
        if item.operator == "not_contains" or item.field not in OVERRIDE_SENSITIVE_FIELDS:
            continue
        existing = active_by_field.get(item.field)
        if existing and str(item.value).casefold() not in existing:
            return True
    return False


def _local_result(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    current_category: str,
    *,
    failure_reason: str | None = None,
    active_constraints: list[dict[str, Any]] | None = None,
) -> tuple[StatePatch, dict[str, int]]:
    fallback = semantic_fallback_patch(
        message,
        turn,
        rule_patch,
        current_category=current_category,
    )
    if failure_reason:
        fallback.fallback_reasons = list(dict.fromkeys([
            *fallback.fallback_reasons,
            failure_reason,
        ]))
    if (
        fallback.action != "replace"
        and _has_conflicting_value(active_constraints or [], fallback.constraints)
    ):
        fallback.action = "replace"
        fallback.fallback_reasons = list(dict.fromkeys([
            *fallback.fallback_reasons,
            "implicit_override_heuristic",
        ]))
    fallback.semantic_query = _fallback_semantic_query(
        message,
        fallback.category,
        fallback.constraints,
    )
    fallback.intent_summary = fallback.semantic_query
    fallback.language = _detect_language(message)
    return fallback, {"prompt_tokens": 0, "completion_tokens": 0}


def resolve_semantic_patch(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    *,
    current_category: str = "",
    active_constraints: list[dict[str, Any]] | None = None,
    current_semantic_query: str = "",
    intent_summary: str = "",
    user_profile: dict[str, Any] | None = None,
) -> tuple[StatePatch, dict[str, int]]:
    """Interpret every turn with the configured LLM, with deterministic fallback."""

    if not is_configured():
        return _local_result(
            message,
            turn,
            rule_patch,
            current_category,
            active_constraints=active_constraints,
        )

    payload = {
        "turn": turn,
        "current_category": current_category or None,
        "active_constraints": active_constraints or [],
        "current_semantic_query": current_semantic_query or None,
        "current_intent_summary": intent_summary or None,
        "user_profile": user_profile or {},
        "user_message": message,
        "rule_patch": rule_patch.model_dump(mode="json"),
    }
    try:
        model_patch, usage = request_state_patch(payload)
        local_patch = semantic_fallback_patch(
            message,
            turn,
            rule_patch,
            current_category=current_category,
        )
        patch = StatePatch(
            action=model_patch.action,
            category=model_patch.category or local_patch.category,
            constraints=[*local_patch.constraints, *model_patch.constraints],
            remove_fields=[*local_patch.remove_fields, *model_patch.remove_fields],
            no_preference=[*local_patch.no_preference, *model_patch.no_preference],
            retire_soft=local_patch.retire_soft or model_patch.retire_soft,
            semantic_query=model_patch.semantic_query or _fallback_semantic_query(
                message,
                model_patch.category or local_patch.category,
                [*local_patch.constraints, *model_patch.constraints],
            ),
            intent_summary=model_patch.intent_summary or model_patch.semantic_query,
            language=model_patch.language or _detect_language(message),
            confidence=max(local_patch.confidence, model_patch.confidence),
            parser="deepseek",
            fallback_reasons=model_patch.fallback_reasons,
        )
        return validate_state_patch(patch), usage
    except DeepSeekInvalidResponse:
        return _local_result(
            message,
            turn,
            rule_patch,
            current_category,
            failure_reason="deepseek_invalid_response",
            active_constraints=active_constraints,
        )
    except Exception:
        return _local_result(
            message,
            turn,
            rule_patch,
            current_category,
            failure_reason="deepseek_unavailable",
            active_constraints=active_constraints,
        )


__all__ = [
    "DEEPSEEK_SYSTEM_PROMPT",
    "StatePatch",
    "apply_state_patch",
    "resolve_semantic_patch",
    "rule_state_patch",
    "semantic_fallback_patch",
    "validate_state_patch",
]
