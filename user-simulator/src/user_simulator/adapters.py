from __future__ import annotations

from typing import Any, Protocol

from .models import AgentResponse, Recommendation, Usage


class ShoppingAgentAdapter(Protocol):
    def reset(self, session_id: str, user_profile: dict) -> None: ...

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> AgentResponse: ...


class PythonAgentAdapter:
    """Wraps a Python shopping agent, including the TechJam reset/respond contract."""

    def __init__(self, agent: Any):
        self.agent = agent

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.agent.reset(session_id, user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> AgentResponse:
        try:
            payload = self.agent.respond(session_id, user_message, turn, top_k)
        except Exception as exc:  # noqa: BLE001 - isolate third-party Agent failures
            return AgentResponse(error=f"agent_exception:{type(exc).__name__}:{exc}")

        if not isinstance(payload, dict):
            return AgentResponse(error="invalid_agent_response:not_a_dict", raw=payload)

        message = payload.get("message")
        error = None
        if not isinstance(message, str):
            message = ""
            error = "invalid_agent_response:message_not_string"

        ask_attribute = payload.get("ask_attribute")
        if ask_attribute is not None and not isinstance(ask_attribute, str):
            ask_attribute = None

        recommendations: list[Recommendation] = []
        seen: set[str] = set()
        raw_recs = payload.get("recommendations")
        if isinstance(raw_recs, list):
            for raw in raw_recs[:100]:
                if isinstance(raw, dict):
                    product_id = raw.get("parent_asin", raw.get("product_id", ""))
                    score = raw.get("score")
                else:
                    product_id = raw
                    score = None
                product_id = str(product_id).strip()
                if not product_id or product_id in seen:
                    continue
                seen.add(product_id)
                recommendations.append(
                    Recommendation(
                        product_id=product_id,
                        score=float(score) if isinstance(score, (int, float)) else None,
                        raw=raw,
                    )
                )
                if len(recommendations) >= top_k:
                    break

        usage = None
        raw_usage = payload.get("usage")
        if isinstance(raw_usage, dict):
            pt = raw_usage.get("prompt_tokens", 0)
            ct = raw_usage.get("completion_tokens", 0)
            usage = Usage(
                prompt_tokens=pt if isinstance(pt, int) and pt >= 0 else 0,
                completion_tokens=ct if isinstance(ct, int) and ct >= 0 else 0,
            )

        return AgentResponse(
            message=message,
            ask_attribute=ask_attribute,
            recommendations=recommendations,
            usage=usage,
            raw=payload,
            error=error,
        )
