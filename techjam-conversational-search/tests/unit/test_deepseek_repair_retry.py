"""Part B: the bounded JSON/schema repair retry itself (deepseek.py).

These tests exercise the provider-facing repair mechanism directly (mocking
the OpenAI client, no network) rather than through interpreter.py/decision.py,
so they can prove: (1) exactly one repair call is made, never more; (2) a
response with no content at all skips repair entirely (nothing to repair);
(3) intent vs dialogue failures carry a distinct, machine-readable
`DeepSeekInvalidResponse.kind`; (4) a repair that also fails still raises,
matching the "no silent local fallback" requirement.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from shopping_agent.infrastructure.llm import deepseek


def _openai_stub(monkeypatch, completions):
    class StubOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=completions)

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=StubOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")


def _response(content: str, prompt_tokens: int = 1, completion_tokens: int = 1):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


VALID_STATE_PATCH = json.dumps({
    "action": "add", "category": "shoes", "constraints": [],
    "semantic_query": "shoes", "intent_summary": "shoes", "language": "en", "confidence": 0.9,
})

VALID_DIALOGUE_DECISION = json.dumps({
    "action": "recommend", "message": "Here are some options.", "reason": "candidates fit",
})


# ---------------------------------------------------------------------------
# request_state_patch: repair-retry mechanics
# ---------------------------------------------------------------------------


def test_request_state_patch_recovers_via_one_repair_call_on_malformed_json(monkeypatch) -> None:
    calls: list[dict] = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return _response("{not valid json at all")
            return _response(VALID_STATE_PATCH, prompt_tokens=4, completion_tokens=2)

    _openai_stub(monkeypatch, Completions())
    patch, usage = deepseek.request_state_patch({"turn": 1})

    assert len(calls) == 2
    assert patch.category == "shoes"
    # The repair call must replay the same schema prompt and reference the
    # bad output + a concrete error, not silently re-ask the question.
    repair_messages = calls[1]["messages"]
    assert repair_messages[0] == calls[0]["messages"][0]  # same system prompt, unchanged
    assert repair_messages[-2]["content"] == "{not valid json at all"
    assert "failed schema validation" in repair_messages[-1]["content"]
    assert usage["completion_tokens"] >= 2


def test_request_state_patch_repairs_malformed_remove_fields_end_to_end(monkeypatch) -> None:
    """The exact public_0166 remove_fields shape: the first reply is valid
    JSON but fails the Attribute schema, and is fixed locally (no 2nd call)."""

    bad = json.dumps({
        "action": "replace", "category": "Boots", "constraints": [],
        "remove_fields": ["feature:Rain", "style:Women's-specific last"],
        "semantic_query": "boots", "intent_summary": "boots", "language": "en", "confidence": 0.9,
    })
    calls: list[dict] = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return _response(bad)

    _openai_stub(monkeypatch, Completions())
    patch, usage = deepseek.request_state_patch({"turn": 4})

    assert len(calls) == 1  # local normalization only; no repair call spent
    assert patch.remove_fields == ["feature", "style"]


def test_request_state_patch_raises_intent_kind_when_repair_also_fails(monkeypatch) -> None:
    class Completions:
        def create(self, **kwargs):
            return _response("still not json")

    _openai_stub(monkeypatch, Completions())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as excinfo:
        deepseek.request_state_patch({"turn": 1})
    assert excinfo.value.kind == "intent"
    assert "repair attempt" in str(excinfo.value)


def test_request_state_patch_skips_repair_when_there_is_no_content_at_all(monkeypatch) -> None:
    calls: list[dict] = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[], usage=None)

    _openai_stub(monkeypatch, Completions())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as excinfo:
        deepseek.request_state_patch({"turn": 1})
    assert len(calls) == 1  # nothing textual to repair -- no wasted second call
    assert excinfo.value.kind == "intent"


# ---------------------------------------------------------------------------
# request_dialogue_decision: repair-retry mechanics
# ---------------------------------------------------------------------------


def test_request_dialogue_decision_recovers_via_one_repair_call_on_malformed_json(monkeypatch) -> None:
    calls: list[dict] = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return _response("not json")
            return _response(VALID_DIALOGUE_DECISION)

    _openai_stub(monkeypatch, Completions())
    result, usage = deepseek.request_dialogue_decision({"turn": 1})

    assert len(calls) == 2
    assert result["action"] == "recommend"


def test_request_dialogue_decision_raises_dialogue_kind_when_repair_also_fails(monkeypatch) -> None:
    class Completions:
        def create(self, **kwargs):
            return _response("[]")  # valid JSON, but not an object

    _openai_stub(monkeypatch, Completions())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as excinfo:
        deepseek.request_dialogue_decision({"turn": 1})
    assert excinfo.value.kind == "dialogue"


# ---------------------------------------------------------------------------
# repair_dialogue_decision: the business-rule repair path decision.py drives
# ---------------------------------------------------------------------------


def test_repair_dialogue_decision_returns_corrected_payload(monkeypatch) -> None:
    class Completions:
        def create(self, **kwargs):
            return _response(json.dumps({
                "action": "ask", "ask_attribute": "color",
                "message": "What color?", "reason": "material already known",
            }))

    _openai_stub(monkeypatch, Completions())
    result, usage = deepseek.repair_dialogue_decision(
        {"turn": 1},
        {"action": "ask", "ask_attribute": "material", "message": "m", "reason": "r"},
        "ask_attribute 'material' is already known",
    )
    assert result["ask_attribute"] == "color"


def test_repair_dialogue_decision_raises_dialogue_kind_on_provider_failure(monkeypatch) -> None:
    class Completions:
        def create(self, **kwargs):
            raise ValueError("provider down")

    _openai_stub(monkeypatch, Completions())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as excinfo:
        deepseek.repair_dialogue_decision({"turn": 1}, {"action": "ask"}, "bad")
    assert excinfo.value.kind == "dialogue"


# ---------------------------------------------------------------------------
# intent vs dialogue classification is a real, testable distinction
# ---------------------------------------------------------------------------


def test_intent_and_dialogue_invalid_responses_carry_distinct_kinds(monkeypatch) -> None:
    class BadIntent:
        def create(self, **kwargs):
            return _response("nope")

    _openai_stub(monkeypatch, BadIntent())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as intent_exc:
        deepseek.request_state_patch({"turn": 1})

    class BadDialogue:
        def create(self, **kwargs):
            return _response("nope")

    _openai_stub(monkeypatch, BadDialogue())
    with pytest.raises(deepseek.DeepSeekInvalidResponse) as dialogue_exc:
        deepseek.request_dialogue_decision({"turn": 1})

    assert intent_exc.value.kind == "intent"
    assert dialogue_exc.value.kind == "dialogue"
    assert intent_exc.value.kind != dialogue_exc.value.kind
