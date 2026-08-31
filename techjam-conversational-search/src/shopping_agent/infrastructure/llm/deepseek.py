from __future__ import annotations

import json
import os
from typing import Any

from shopping_agent.understanding.prompts import DEEPSEEK_SYSTEM_PROMPT
from shopping_agent.understanding.state_patch import StatePatch, normalize_raw_state_patch


class DeepSeekInvalidResponse(Exception):
    """The provider replied, but its content did not satisfy the requested
    schema (JSON syntax, Pydantic validation, or a bounded post-validation
    policy check such as "do not ask about an already-known attribute").

    ``kind`` distinguishes which contract was violated: "intent" for the
    understanding-turn StatePatch, "dialogue" for the dialogue-policy
    decision. Keeping this on the exception (rather than only in the wrapping
    RuntimeError's message text) lets callers and tests branch on it directly
    instead of parsing "Online intent failed" / "Online dialogue failed"
    strings.
    """

    def __init__(self, message: str, *, kind: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind


def _is_transient_provider_error(exc: Exception) -> bool:
    """Return whether a provider failure is safe to retry once."""

    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code == 429 or isinstance(status_code, int) and status_code >= 500:
        return True
    return type(exc).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "RateLimitError",
    }


def is_configured() -> bool:
    enabled = os.getenv("SHOPPING_AGENT_ENABLE_LLM", "false").strip().casefold() in {
        "1", "true", "yes", "on",
    }
    if enabled and not os.getenv("DEEPSEEK_API_KEY", "").strip():
        raise RuntimeError("Online mode requires DEEPSEEK_API_KEY; offline fallback is disabled")
    return enabled


def _usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
    }


def _sum_usage(*parts: dict[str, int]) -> dict[str, int]:
    return {
        "prompt_tokens": sum(int(part.get("prompt_tokens", 0)) for part in parts),
        "completion_tokens": sum(int(part.get("completion_tokens", 0)) for part in parts),
    }


def _repair_request_once(
    client: Any,
    original_request: dict[str, Any],
    invalid_content: str,
    error_message: str,
) -> tuple[str, dict[str, int]]:
    """Send exactly one bounded repair turn for a response that came back as
    text but failed schema validation.

    This is deliberately narrow: it replays the *same* system/user turn the
    normal call already sent (no new prompt engineering, per the "don't
    rewrite the prompt" constraint), appends the model's own invalid reply
    and the concrete validation error, and asks for a corrected JSON object
    only. It is not a fresh interpretation request -- the model is not
    invited to reconsider the user's intent, only to fix the output shape.
    Raises on any provider or parsing failure; callers get exactly one such
    attempt and must not loop.
    """

    repair_request = {
        **original_request,
        "messages": [
            *original_request["messages"],
            {"role": "assistant", "content": invalid_content},
            {
                "role": "user",
                "content": (
                    "That reply failed schema validation: " + error_message + "\n"
                    "Return the corrected JSON object only, matching the schema "
                    "in the system message exactly. Keep every value that was "
                    "already correct; change only what the error requires. No "
                    "commentary, no markdown fences, JSON only."
                ),
            },
        ],
    }
    response = client.chat.completions.create(**repair_request)
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        raise ValueError("repair response content is empty or not text")
    return content, _usage_dict(response)


def request_state_patch(payload: dict[str, Any]) -> tuple[StatePatch, dict[str, int]]:
    """Call DeepSeek's OpenAI-compatible JSON endpoint.

    On a schema-invalid reply this makes exactly one bounded repair attempt
    before giving up: first a local, deterministic normalization of
    ``remove_fields``/``no_preference`` entries (no extra call), then, if
    still invalid, one repair turn back to the model. Failures that never
    produced a response at all (empty choices, no message) skip straight to
    the error -- there is nothing textual to hand back for repair.
    """

    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    request = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [
            {"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Return the JSON state patch for:\n"
                + json.dumps(payload, ensure_ascii=False),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 800,
        "stream": False,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    response = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(**request)
            break
        except Exception as exc:  # noqa: BLE001 - normalize provider SDK failures
            if attempt == 1 or not _is_transient_provider_error(exc):
                raise
    if response is None:  # pragma: no cover - defensive guard
        raise RuntimeError("DeepSeek request failed without a response")

    try:
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("response content is empty or not text")
    except Exception as exc:
        raise DeepSeekInvalidResponse(
            "DeepSeek returned an invalid StatePatch", kind="intent",
        ) from exc

    repair_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        patch = StatePatch.model_validate_json(content)
    except Exception as first_exc:
        patch = None
        try:
            raw = json.loads(content)
            if isinstance(raw, dict):
                patch = StatePatch.model_validate(normalize_raw_state_patch(raw))
        except Exception:
            patch = None
        if patch is None:
            try:
                repaired_content, repair_usage = _repair_request_once(
                    client, request, content, str(first_exc),
                )
                try:
                    patch = StatePatch.model_validate_json(repaired_content)
                except Exception:
                    repaired_raw = json.loads(repaired_content)
                    patch = StatePatch.model_validate(normalize_raw_state_patch(repaired_raw))
            except Exception as repair_exc:
                raise DeepSeekInvalidResponse(
                    "DeepSeek returned an invalid StatePatch after one repair attempt",
                    kind="intent",
                ) from repair_exc

    return patch, _sum_usage(_usage_dict(response), repair_usage)


def request_dialogue_decision(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Request one structured dialogue-policy decision from DeepSeek.

    Repairs a reply that is not even parseable JSON (one bounded retry); a
    reply that *is* valid JSON but fails the DialogueDecision schema or the
    dialogue-policy rules (e.g. asking about an already-known attribute) is
    repaired instead by the caller via :func:`repair_dialogue_decision`,
    which has the policy context (known/declined attributes) this function
    does not.
    """

    from openai import OpenAI

    from shopping_agent.dialogue.prompts import DIALOGUE_DECISION_SYSTEM_PROMPT

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    request = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [
            {"role": "system", "content": DIALOGUE_DECISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Return the JSON dialogue decision for:\n"
                + json.dumps(payload, ensure_ascii=False),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 500,
        "stream": False,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    response = None
    for attempt in range(2):
        try:
            response = client.chat.completions.create(**request)
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 1 or not _is_transient_provider_error(exc):
                raise
    if response is None:  # pragma: no cover
        raise RuntimeError("DeepSeek request failed without a response")

    try:
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("response content is empty or not text")
    except Exception as exc:
        raise DeepSeekInvalidResponse(
            "DeepSeek returned an invalid dialogue decision", kind="dialogue",
        ) from exc

    repair_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        result = json.loads(content)
        if not isinstance(result, dict):
            raise TypeError("dialogue decision is not an object")
    except Exception as first_exc:
        try:
            repaired_content, repair_usage = _repair_request_once(
                client, request, content, str(first_exc),
            )
            result = json.loads(repaired_content)
            if not isinstance(result, dict):
                raise TypeError("dialogue decision is not an object")
        except Exception as repair_exc:
            raise DeepSeekInvalidResponse(
                "DeepSeek returned an invalid dialogue decision after one repair attempt",
                kind="dialogue",
            ) from repair_exc

    return result, _sum_usage(_usage_dict(response), repair_usage)


def repair_dialogue_decision(
    payload: dict[str, Any],
    invalid_result: dict[str, Any],
    error_message: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    """One bounded repair turn for a dialogue decision that parsed as JSON
    but failed schema validation or a post-validation policy rule (an
    excluded ``ask_attribute``, an empty ``message``, an overlong
    ``reason``). Replays the same request the normal call sent, so this
    costs no extra prompt engineering; the caller (``dialogue/decision.py``)
    supplies the exact validation error so the model can target the fix.
    """

    from openai import OpenAI

    from shopping_agent.dialogue.prompts import DIALOGUE_DECISION_SYSTEM_PROMPT

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    original_request = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        "messages": [
            {"role": "system", "content": DIALOGUE_DECISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Return the JSON dialogue decision for:\n"
                + json.dumps(payload, ensure_ascii=False),
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 500,
        "stream": False,
        "extra_body": {"thinking": {"type": "disabled"}},
    }
    try:
        repaired_content, usage = _repair_request_once(
            client,
            original_request,
            json.dumps(invalid_result, ensure_ascii=False),
            error_message,
        )
        result = json.loads(repaired_content)
        if not isinstance(result, dict):
            raise TypeError("dialogue decision is not an object")
    except Exception as exc:
        raise DeepSeekInvalidResponse(
            "DeepSeek returned an invalid dialogue decision after one repair attempt",
            kind="dialogue",
        ) from exc
    return result, usage
