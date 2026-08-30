from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from shopping_agent.domain.schemas import AgentTurn
from shopping_agent.observability.tracing import reconstruct_turn_trace
from shopping_agent.orchestration.graph import build_shopping_graph


class ShoppingAgent:
    """Real-user shopping agent with an evaluator-compatible adapter."""

    def __init__(
        self,
        catalog_path: str | Path = "data/catalog.jsonl",
        *,
        model: str | BaseChatModel | None = None,
        graph: Any | None = None,
    ) -> None:
        self.graph = graph or build_shopping_graph(model, catalog_path)
        self._profiles: dict[str, dict[str, Any]] = {}
        self._thread_ids: dict[str, str] = {}
        self._turns: dict[str, int] = {}
        self._histories: dict[str, list[dict[str, str]]] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self._profiles[session_id] = dict(user_profile)
        self._thread_ids[session_id] = f"{session_id}:{uuid.uuid4().hex}"
        self._turns[session_id] = 0
        self._histories[session_id] = []

    def start_session(
        self,
        session_id: str | None = None,
        user_profile: dict[str, Any] | None = None,
    ) -> str:
        """Start a normal user session without the competition request shape."""

        session_id = session_id or uuid.uuid4().hex
        self.reset(session_id, user_profile or {})
        return session_id

    def chat(self, session_id: str, user_message: str, *, top_k: int = 10) -> dict[str, Any]:
        """Handle one natural-language message and maintain the turn internally."""

        if session_id not in self._profiles:
            self.reset(session_id, {})
        turn = self._turns.get(session_id, 0) + 1
        return self.respond(session_id, user_message, turn=turn, top_k=top_k)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict[str, Any]:
        if session_id not in self._profiles:
            raise RuntimeError("reset must be called before respond")
        self._turns[session_id] = max(self._turns.get(session_id, 0), turn)

        payload = {
            "session_id": session_id,
            "turn": turn,
            "top_k": top_k,
            "user_message": user_message,
            "user_profile": self._profiles[session_id],
            "conversation_history": list(self._histories.get(session_id, [])),
            "messages": [{"role": "user", "content": json.dumps({
                "turn": turn,
                "top_k": top_k,
                "user_message": user_message,
            }, ensure_ascii=False)}],
        }
        result = self.graph.invoke(
            payload,
            config={"configurable": {"thread_id": self._thread_ids[session_id]}},
        )

        if "response_message" in result:
            response = {
                "message": str(result.get("response_message", "")),
                "ask_attribute": result.get("ask_attribute"),
                "recommendations": self._normalize_recommendations(result.get("recommendations", []), top_k),
                "usage": result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0}),
            }
            self._histories.setdefault(session_id, []).extend([
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": response["message"]},
            ])
            self._histories[session_id] = self._histories[session_id][-16:]
            return response

        decision = self._coerce_turn(result)
        response = {
            "message": decision.message,
            "ask_attribute": decision.ask_attribute,
            "recommendations": self._normalize_recommendations(
                [item.model_dump(exclude_none=True) for item in decision.recommendations], top_k
            ),
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
        self._histories.setdefault(session_id, []).extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response["message"]},
        ])
        self._histories[session_id] = self._histories[session_id][-16:]
        return response

    @staticmethod
    def _normalize_recommendations(items: list[Any], top_k: int) -> list[dict[str, Any]]:
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            parent_asin = str(item.get("parent_asin", "")).strip()
            if not parent_asin or parent_asin in seen:
                continue
            seen.add(parent_asin)
            output: dict[str, Any] = {"parent_asin": parent_asin}
            if isinstance(item.get("score"), (int, float)):
                output["score"] = float(item["score"])
            normalized.append(output)
            if len(normalized) >= min(max(top_k, 1), 10):
                break
        return normalized

    @staticmethod
    def _coerce_turn(result: dict[str, Any]) -> AgentTurn:
        structured = result.get("structured_response")
        if isinstance(structured, AgentTurn):
            return structured
        if isinstance(structured, dict):
            return AgentTurn.model_validate(structured)
        raise ValueError("Graph did not return a valid shopping response")

    def get_intent_state(self, session_id: str) -> dict[str, Any]:
        """Expose maintained intent state for a product UI or debugging panel."""

        if session_id not in self._thread_ids:
            raise KeyError(session_id)
        snapshot = self.graph.get_state(
            {"configurable": {"thread_id": self._thread_ids[session_id]}}
        )
        values = getattr(snapshot, "values", {})
        return {
            "category": values.get("category", ""),
            "active_constraints": values.get("active_constraints", []),
            "superseded_constraints": values.get("superseded_constraints", []),
            "no_preference": values.get("no_preference", []),
            "semantic_query": values.get("semantic_query", ""),
            "intent_summary": values.get("intent_summary", ""),
            "retrieval_intent": values.get("retrieval_intent", "unknown"),
            "language": values.get("user_language", "en"),
        }

    def get_turn_trace(
        self,
        session_id: str,
        turn: int,
        *,
        candidate_limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return compact node-by-node writes reconstructed from checkpoints."""

        if session_id not in self._thread_ids:
            raise KeyError(session_id)
        return reconstruct_turn_trace(
            self.graph,
            self._thread_ids[session_id],
            turn,
            candidate_limit=candidate_limit,
        )

    def release_session(self, session_id: str) -> None:
        """Release a completed trace session after its artifacts are persisted."""

        thread_id = self._thread_ids.pop(session_id, None)
        self._profiles.pop(session_id, None)
        self._turns.pop(session_id, None)
        self._histories.pop(session_id, None)
        checkpointer = getattr(self.graph, "checkpointer", None)
        if thread_id and checkpointer is not None and hasattr(checkpointer, "delete_thread"):
            checkpointer.delete_thread(thread_id)

DeepShoppingAgent = ShoppingAgent
