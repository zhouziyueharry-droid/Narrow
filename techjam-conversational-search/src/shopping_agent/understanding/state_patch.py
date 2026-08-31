from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from shopping_agent.domain.schemas import ATTRIBUTE_VALUES, Attribute, Constraint


class StatePatch(BaseModel):
    """A bounded user-intent update; it cannot retrieve or recommend products."""

    action: Literal["add", "replace", "remove", "no_preference"] = "add"
    category: str | None = None
    constraints: list[Constraint] = Field(default_factory=list, max_length=20)
    remove_fields: list[Attribute] = Field(default_factory=list)
    no_preference: list[Attribute] = Field(default_factory=list)
    retire_soft: bool = False
    reset_scope: Literal["none", "soft", "all"] = "none"
    semantic_query: str = Field(default="", max_length=500)
    intent_summary: str = Field(default="", max_length=1000)
    language: Literal["zh", "en", "other"] = "en"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    parser: Literal["rules", "fallback", "deepseek"] = "rules"
    fallback_reasons: list[str] = Field(default_factory=list)
    retrieval_intent: Literal["buying", "browsing", "unknown"] = "unknown"
    model_output: dict[str, Any] = Field(default_factory=dict)


def _normalize_attribute_entry(entry: Any) -> str | None:
    """Coerce one remove_fields/no_preference entry to a bare Attribute name.

    The model occasionally returns "field: extra description" instead of the
    bare field name the schema requires (observed for ``remove_fields`` in
    the 20260830_211751_+0800 online run, e.g. "feature: spring bar tool").
    This is a purely mechanical formatting slip -- the field name itself is
    still present and unambiguous -- so it is corrected locally rather than
    spending a repair call on it. Anything that still does not resolve to a
    known Attribute after normalization is dropped rather than guessed.
    """

    if not isinstance(entry, str):
        return None
    candidate = entry.split(":", 1)[0].strip().strip("\"'").casefold()
    return candidate if candidate in ATTRIBUTE_VALUES else None


def normalize_raw_state_patch(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a raw (still-unvalidated) state-patch dict with
    ``remove_fields``/``no_preference`` entries normalized to bare Attribute
    names. Never raises; fields that cannot be resolved are dropped so the
    rest of the patch can still validate. Safe to call even when the raw
    dict already conforms to the schema (it is then a no-op)."""

    normalized = dict(raw)
    for key in ("remove_fields", "no_preference"):
        values = raw.get(key)
        if not isinstance(values, list):
            continue
        cleaned: list[str] = []
        for entry in values:
            attribute = _normalize_attribute_entry(entry)
            if attribute and attribute not in cleaned:
                cleaned.append(attribute)
        normalized[key] = cleaned
    return normalized


def validate_state_patch(patch: StatePatch) -> StatePatch:
    """Normalize, deduplicate, and resolve positive/negative collisions."""

    deduplicated: dict[tuple[str, str, str], Constraint] = {}
    for item in patch.constraints:
        if isinstance(item.value, str):
            item.value = re.sub(r"\s+", " ", item.value).strip(" .;,\t\n")
            if not item.value:
                continue
        elif item.field == "budget" and float(item.value) <= 0:
            continue
        key = (item.field, item.operator, str(item.value).casefold())
        deduplicated[key] = item

    negatives = {
        (item.field, str(item.value).casefold())
        for item in deduplicated.values()
        if item.operator == "not_contains"
    }
    if patch.parser == "deepseek" and any(
        item.operator != "not_contains"
        and (item.field, str(item.value).casefold()) in negatives
        for item in deduplicated.values()
    ):
        raise ValueError("Online intent contains contradictory constraints")
    constraints = [
        item
        for item in deduplicated.values()
        if item.operator == "not_contains"
        or (item.field, str(item.value).casefold()) not in negatives
    ]
    return patch.model_copy(update={
        "constraints": constraints[:20],
        "remove_fields": list(dict.fromkeys(patch.remove_fields)),
        "no_preference": list(dict.fromkeys(patch.no_preference)),
        "semantic_query": re.sub(r"\s+", " ", patch.semantic_query).strip()[:500],
        "intent_summary": re.sub(r"\s+", " ", patch.intent_summary).strip()[:1000],
    })


def apply_state_patch(
    active_values: list[dict[str, Any]],
    patch: StatePatch,
) -> tuple[list[Constraint], list[Constraint]]:
    active = [Constraint.model_validate(value) for value in active_values]
    superseded: list[Constraint] = []

    if patch.reset_scope == "all":
        superseded.extend(active)
        active = []
    elif patch.retire_soft or patch.reset_scope == "soft":
        superseded.extend(item for item in active if item.strength == "soft")
        active = [item for item in active if item.strength == "hard"]

    if patch.action == "replace":
        replacement_fields = {item.field for item in patch.constraints}
        if replacement_fields:
            # A replace whose incoming constraints re-state an existing value
            # unchanged (same field, operator and value) is not really an
            # override of that value -- the model just echoed it back while
            # replacing a sibling field. Do not log it as superseded, or the
            # override history misreports something as retracted when it
            # never left the active set. Only genuinely displaced values are
            # recorded (observed with public_0096 in the
            # 20260830_211751_+0800 online run: an "ignore my earlier
            # preference" reply that re-emitted the untouched category and
            # feature constraints alongside the real new material value).
            incoming_keys = {
                (item.field, item.operator, str(item.value).casefold())
                for item in patch.constraints
            }
            displaced = [
                item for item in active
                if item.field in replacement_fields
                and (item.field, item.operator, str(item.value).casefold()) not in incoming_keys
            ]
            superseded.extend(displaced)
            active = [
                item for item in active
                if item.field not in replacement_fields
                or (item.field, item.operator, str(item.value).casefold()) in incoming_keys
            ]

    removed_fields = set(patch.remove_fields) | set(patch.no_preference)
    if removed_fields:
        superseded.extend(item for item in active if item.field in removed_fields)
        active = [item for item in active if item.field not in removed_fields]

    for incoming in patch.constraints:
        value = str(incoming.value).casefold()
        conflicts = [
            item for item in active
            if item.field == incoming.field
            and str(item.value).casefold() == value
            and item.operator != incoming.operator
        ]
        if conflicts:
            superseded.extend(conflicts)
            active = [item for item in active if item not in conflicts]
        key = (incoming.field, incoming.operator, value)
        if not any(
            (item.field, item.operator, str(item.value).casefold()) == key
            for item in active
        ):
            active.append(incoming)
    return active, superseded
