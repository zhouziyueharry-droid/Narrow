"""Part B: intent-schema repair for malformed StatePatch fields.

Covers the 2 "需求解析失败" (intent-schema) turns out of the 9 abnormal
turns identified in evaluation_runs/lambdamart_online_pro_200/lambdamart/
20260830_211751_+0800 (see docs/lambdamart_online_pro_report.md): the model
returned remove_fields/no_preference entries as "field: description" instead
of a bare Attribute name, which fails StatePatch's `list[Attribute]` schema.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from shopping_agent.domain.schemas import Constraint
from shopping_agent.understanding.state_patch import (
    StatePatch,
    apply_state_patch,
    normalize_raw_state_patch,
)

# Verbatim `remove_fields` payloads captured from llm_calls.jsonl for the two
# real intent-schema failures in the 20260830_211751_+0800 online run.
PUBLIC_0166_REMOVE_FIELDS = ["feature:Rain", "style:Women's-specific last"]
PUBLIC_0197_REMOVE_FIELDS = [
    "feature: watch band link remover",
    "feature: spring bar tool",
    "feature: up to 30mm wide watch band",
    "use_case: watch repair",
    "other: value kit for money saving",
]


def _minimal_raw_patch(remove_fields: list[str]) -> dict:
    return {
        "action": "replace",
        "retrieval_intent": "buying",
        "category": "Boots",
        "constraints": [],
        "remove_fields": remove_fields,
        "no_preference": [],
        "retire_soft": False,
        "semantic_query": "boots",
        "intent_summary": "boots",
        "language": "en",
        "confidence": 0.9,
        "fallback_reasons": [],
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_raw_remove_fields_with_description_suffix_fails_schema_validation() -> None:
    """Confirms the failure mode itself, so the fix below is proven against
    something that actually breaks rather than an already-passing case."""

    raw = _minimal_raw_patch(PUBLIC_0166_REMOVE_FIELDS)
    with pytest.raises(ValidationError):
        StatePatch.model_validate(raw)


def test_normalize_raw_state_patch_extracts_bare_attribute_names() -> None:
    raw = _minimal_raw_patch(PUBLIC_0166_REMOVE_FIELDS)
    normalized = normalize_raw_state_patch(raw)
    assert normalized["remove_fields"] == ["feature", "style"]
    # And the normalized dict now validates cleanly.
    patch = StatePatch.model_validate(normalized)
    assert patch.remove_fields == ["feature", "style"]


def test_normalize_raw_state_patch_drops_unresolvable_entries() -> None:
    raw = _minimal_raw_patch(["not_a_real_attribute: whatever", "", "  ", "material"])
    normalized = normalize_raw_state_patch(raw)
    assert normalized["remove_fields"] == ["material"]


def test_normalize_raw_state_patch_deduplicates() -> None:
    raw = _minimal_raw_patch(["feature: a", "feature: b", "FEATURE"])
    normalized = normalize_raw_state_patch(raw)
    assert normalized["remove_fields"] == ["feature"]


def test_normalize_raw_state_patch_is_noop_on_already_valid_input() -> None:
    raw = _minimal_raw_patch(["feature", "style"])
    normalized = normalize_raw_state_patch(raw)
    assert normalized["remove_fields"] == ["feature", "style"]


def test_normalize_raw_state_patch_leaves_other_fields_untouched() -> None:
    raw = _minimal_raw_patch(["feature:x"])
    normalized = normalize_raw_state_patch(raw)
    assert normalized["category"] == "Boots"
    assert normalized["confidence"] == 0.9


# ---------------------------------------------------------------------------
# Smoke tests: replay the 2 real captured payloads plus synthetic variants.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id,remove_fields,expected",
    [
        ("public_0166_real", PUBLIC_0166_REMOVE_FIELDS, ["feature", "style"]),
        ("public_0197_real", PUBLIC_0197_REMOVE_FIELDS, ["feature", "use_case", "other"]),
        ("single_colon", ["color:red is not wanted"], ["color"]),
        ("quoted_field", ['"brand": Nike'], ["brand"]),
        ("no_colon_valid", ["budget"], ["budget"]),
        ("mixed_case", ["Material: cotton"], ["material"]),
        ("garbage_only", ["not a field at all"], []),
        ("empty_list", [], []),
        ("already_clean_multi", ["category", "color", "size"], ["category", "color", "size"]),
        ("whitespace_padding", ["  feature :  extra  "], ["feature"]),
        ("colon_in_value_only", ["use_case: hiking: winter"], ["use_case"]),
        ("all_ten_attributes", [
            "category:x", "material:x", "color:x", "size:x", "style:x",
            "brand:x", "budget:x", "feature:x", "use_case:x", "other:x",
        ], [
            "category", "material", "color", "size", "style",
            "brand", "budget", "feature", "use_case", "other",
        ]),
    ],
)
def test_remove_fields_smoke(case_id: str, remove_fields: list[str], expected: list[str]) -> None:
    raw = _minimal_raw_patch(remove_fields)
    normalized = normalize_raw_state_patch(raw)
    assert normalized["remove_fields"] == expected, case_id
    # And it always validates afterward -- normalization must never leave the
    # patch in a still-broken state.
    StatePatch.model_validate(normalized)


def test_no_preference_field_gets_the_same_normalization() -> None:
    raw = _minimal_raw_patch([])
    raw["no_preference"] = ["brand: no strong opinion"]
    normalized = normalize_raw_state_patch(raw)
    assert normalized["no_preference"] == ["brand"]


# ---------------------------------------------------------------------------
# Override / full-reset bookkeeping fix (apply_state_patch).
#
# Verifies task B's "override / no preference / full reset" item, using the
# exact public_0096 turn-3 model reply from the online run: an "ignore my
# earlier preference" message where the model's action=replace re-emitted
# the untouched category and feature constraints unchanged alongside the one
# real new value. Before the fix, apply_state_patch recorded the unchanged
# constraints as "superseded" even though they never left the active set.
# ---------------------------------------------------------------------------


def _hard(field: str, value: str, turn: int = 1) -> Constraint:
    return Constraint(field=field, value=value, strength="hard", source_turn=turn)


def test_replace_does_not_report_unchanged_constraints_as_superseded() -> None:
    active = [
        _hard("category", "Tees & Blouses T-Shirts").model_dump(),
        _hard("feature", "Pull On closure").model_dump(),
    ]
    patch = StatePatch(
        action="replace",
        parser="deepseek",
        constraints=[
            _hard("category", "Tees & Blouses T-Shirts", turn=3),
            _hard("feature", "Pull On closure", turn=3),
            _hard("material", "polyester", turn=3),
        ],
    )
    new_active, superseded = apply_state_patch(active, patch)

    active_keys = {(item.field, str(item.value)) for item in new_active}
    assert active_keys == {
        ("category", "Tees & Blouses T-Shirts"),
        ("feature", "Pull On closure"),
        ("material", "polyester"),
    }
    # The unchanged constraints must not show up in the override history.
    superseded_keys = {(item.field, str(item.value)) for item in superseded}
    assert superseded_keys == set()


def test_replace_still_supersedes_a_genuinely_displaced_value() -> None:
    active = [_hard("color", "red").model_dump()]
    patch = StatePatch(
        action="replace",
        parser="deepseek",
        constraints=[_hard("color", "blue", turn=2)],
    )
    new_active, superseded = apply_state_patch(active, patch)

    assert [item.value for item in new_active] == ["blue"]
    assert [item.value for item in superseded] == ["red"]


def test_full_reset_clears_hard_and_soft_and_records_all_as_superseded() -> None:
    active = [
        _hard("category", "Boots").model_dump(),
        Constraint(field="color", value="black", strength="soft", source_turn=1).model_dump(),
    ]
    patch = StatePatch(action="add", reset_scope="all", parser="deepseek")
    new_active, superseded = apply_state_patch(active, patch)

    assert new_active == []
    assert {item.field for item in superseded} == {"category", "color"}


def test_soft_reset_retires_soft_but_keeps_hard() -> None:
    active = [
        _hard("category", "Boots").model_dump(),
        Constraint(field="color", value="black", strength="soft", source_turn=1).model_dump(),
    ]
    patch = StatePatch(action="add", reset_scope="soft", parser="deepseek")
    new_active, superseded = apply_state_patch(active, patch)

    assert [item.field for item in new_active] == ["category"]
    assert [item.field for item in superseded] == ["color"]


def test_no_preference_retires_matching_active_constraint() -> None:
    active = [_hard("brand", "Nike").model_dump()]
    patch = StatePatch(action="no_preference", no_preference=["brand"], parser="deepseek")
    new_active, superseded = apply_state_patch(active, patch)

    assert new_active == []
    assert [item.field for item in superseded] == ["brand"]
