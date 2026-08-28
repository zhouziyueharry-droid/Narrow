from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from .models import DialogueAct, DialogueActType, Fact, Persona


@dataclass(slots=True)
class VerbalizationRequest:
    persona: Persona
    dialogue_act: DialogueAct
    allowed_facts: list[Fact]
    conversation_history: list[tuple[str, str]]
    language: str = "en"


class TemplateVerbalizer:
    def __init__(self) -> None:
        self.calls = 0

    def diagnostics(self) -> dict[str, str | int | None]:
        return {
            "provider": "template",
            "model": None,
            "calls": self.calls,
            "api_calls": 0,
            "fallbacks": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "last_error": None,
        }

    @staticmethod
    def _fact_text(attribute: str | None, values: list[str]) -> str:
        joined = ", ".join(values)
        if attribute == "budget_max" and values:
            return f"a budget up to ${values[0]}"
        if attribute == "budget_min" and values:
            return f"a budget starting around ${values[0]}"
        if attribute == "brand" and values:
            return f"the brand {joined}"
        if attribute:
            return f"{attribute.replace('_', ' ')}: {joined}"
        return joined

    def verbalize(self, request: VerbalizationRequest) -> str:
        self.calls += 1
        act = request.dialogue_act
        facts = {f.attribute: f.values for f in request.allowed_facts}

        if act.type == DialogueActType.INITIAL_REQUEST:
            parts = ["I'm looking for something"]
            if facts.get("category"):
                parts = [f"I'm looking for {facts['category'][0]}"]
            extras = [self._fact_text(key, values) for key, values in facts.items() if key != "category" and values]
            return parts[0] + (f". A key preference is {extras[0]}." if extras else ".")
        if act.type == DialogueActType.ANSWER_ATTRIBUTE:
            return f"I'd prefer {self._fact_text(act.attribute, act.values)}."
        if act.type == DialogueActType.NO_PREFERENCE:
            return f"I don't have a preference for {act.attribute}; please use your judgment."
        if act.type == DialogueActType.OVERRIDE:
            if act.values:
                return f"Actually, please change my {act.attribute} preference to {', '.join(act.values)}."
            return f"Actually, ignore my earlier {act.attribute} preference."
        if act.type == DialogueActType.RELAX_CONSTRAINT:
            return f"I can be more flexible: {self._fact_text(act.attribute, act.values)}."
        if act.type == DialogueActType.REQUEST_COMPARISON:
            return "Can you compare the strongest options for me?"
        if act.type == DialogueActType.REQUEST_MORE_OPTIONS:
            return "Those aren't quite right. Can you show me some more options?"
        if act.type == DialogueActType.ASK_PRODUCT_QUESTION:
            return "Can you tell me more about the best option?"
        if act.type == DialogueActType.REJECT:
            return "Those options aren't quite right yet."
        if act.type == DialogueActType.ACCEPT:
            return "That works for me."
        return "Please keep helping me narrow it down."


class OpenAICompatibleVerbalizer:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 120,
        timeout: int = 30,
        fallback: TemplateVerbalizer | None = None,
    ) -> None:
        deepseek_provider = provider == "deepseek"
        self.base_url = (
            base_url
            or os.environ.get("LLM_BASE_URL")
            or os.environ.get("DEEPSEEK_BASE_URL")
            or ("https://api.deepseek.com" if deepseek_provider else "https://api.openai.com/v1")
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
        self.provider = provider or ("deepseek" if "deepseek.com" in self.base_url else "openai_compatible")
        self.model = (
            model
            or os.environ.get("LLM_MODEL")
            or os.environ.get("DEEPSEEK_MODEL")
            or ("deepseek-v4-flash" if self.provider == "deepseek" else "")
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.fallback = fallback or TemplateVerbalizer()
        self.calls = 0
        self.api_calls = 0
        self.fallbacks = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.model)

    def diagnostics(self) -> dict[str, str | int | None]:
        return {
            "provider": self.provider,
            "model": self.model or None,
            "calls": self.calls,
            "api_calls": self.api_calls,
            "fallbacks": self.fallbacks,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "last_error": self.last_error,
        }

    def verbalize(self, request: VerbalizationRequest) -> str:
        self.calls += 1
        if not self.api_key or not self.model:
            self.fallbacks += 1
            self.last_error = "missing_api_key_or_model"
            return self.fallback.verbalize(request)

        facts = [{"attribute": f.attribute, "values": f.values} for f in request.allowed_facts]
        persona = {
            "name": request.persona.name,
            "verbosity": request.persona.verbosity,
            "patience": request.persona.patience,
            "shopping_expertise": request.persona.shopping_expertise,
        }
        prompt = (
            "You are verbalizing one simulated shopper turn. Output ONLY the shopper's English utterance. "
            "Do not invent facts, product IDs, preferences, or actions. Preserve the supplied dialogue act. "
            f"Persona: {json.dumps(persona)}\n"
            f"Dialogue act: {request.dialogue_act.type.value}\n"
            f"Attribute: {request.dialogue_act.attribute}\n"
            f"Allowed facts: {json.dumps(facts)}\n"
            f"Recent conversation: {json.dumps(request.conversation_history[-6:])}"
        )
        request_payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.provider == "deepseek":
            request_payload["thinking"] = {"type": "disabled"}
        payload = json.dumps(request_payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            self.api_calls += 1
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage") or {}
            self.prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
            self.completion_tokens += int(usage.get("completion_tokens", 0) or 0)
            if text:
                self.last_error = None
                return text
            self.fallbacks += 1
            self.last_error = "empty_response"
            return self.fallback.verbalize(request)
        except Exception as exc:  # noqa: BLE001 - deterministic template fallback is required
            self.fallbacks += 1
            self.last_error = f"{type(exc).__name__}:{exc}"
            return self.fallback.verbalize(request)
