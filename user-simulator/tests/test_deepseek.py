from __future__ import annotations

import json

from user_simulator.models import DialogueAct, DialogueActType, Fact
from user_simulator.personas import get_persona
from user_simulator.verbalizers import OpenAICompatibleVerbalizer, VerbalizationRequest


def _request() -> VerbalizationRequest:
    fact = Fact("color", ["black"])
    return VerbalizationRequest(
        persona=get_persona("casual_browser"),
        dialogue_act=DialogueAct(
            DialogueActType.ANSWER_ATTRIBUTE,
            attribute="color",
            values=["black"],
            allowed_facts=[fact],
        ),
        allowed_facts=[fact],
        conversation_history=[],
    )


def test_deepseek_verbalizer_uses_current_chat_contract(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [{"message": {"content": "Black would be ideal."}}],
                    "usage": {"prompt_tokens": 25, "completion_tokens": 5},
                }
            ).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    verbalizer = OpenAICompatibleVerbalizer(provider="deepseek", api_key="test-key")

    text = verbalizer.verbalize(_request())
    diagnostics = verbalizer.diagnostics()

    assert text == "Black would be ideal."
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert captured["payload"]["max_tokens"] == 120
    assert captured["timeout"] == 30
    assert diagnostics["api_calls"] == 1
    assert diagnostics["fallbacks"] == 0
    assert diagnostics["prompt_tokens"] == 25
    assert diagnostics["completion_tokens"] == 5


def test_deepseek_failure_is_visible_and_falls_back(monkeypatch):
    def fail_urlopen(request, timeout):
        raise TimeoutError("provider timeout")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
    verbalizer = OpenAICompatibleVerbalizer(provider="deepseek", api_key="test-key")

    text = verbalizer.verbalize(_request())
    diagnostics = verbalizer.diagnostics()

    assert text == "I'd prefer color: black."
    assert diagnostics["api_calls"] == 1
    assert diagnostics["fallbacks"] == 1
    assert diagnostics["last_error"] == "TimeoutError:provider timeout"
