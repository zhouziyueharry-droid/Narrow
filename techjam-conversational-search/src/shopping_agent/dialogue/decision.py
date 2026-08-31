from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from shopping_agent.dialogue.question_policy import choose_question, facet_scores, question_options
from shopping_agent.domain.schemas import Attribute


class DialogueDecision(BaseModel):
    """One bounded dialogue action chosen from user, state, and candidate context."""

    action: Literal["ask", "recommend", "confirm", "end"] = "recommend"
    ask_attribute: Attribute | None = None
    message: str = Field(default="", max_length=1000)
    reason: str = Field(default="", max_length=300)
    parser: Literal["fallback", "deepseek"] = "fallback"
    model_output: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_ask(self) -> "DialogueDecision":
        if self.action == "ask" and self.ask_attribute is None:
            raise ValueError("ask action requires ask_attribute")
        if self.action != "ask":
            self.ask_attribute = None
        return self


def decide_dialogue(
    *,
    turn: int,
    user_message: str,
    conversation_history: list[dict[str, str]],
    active_constraints: list[dict[str, Any]],
    no_preference: set[str],
    asked_attributes: list[str],
    pending_question: dict[str, Any] | None,
    question_history: list[dict[str, Any]],
    candidate_attributes: list[dict[str, set[str]]],
    ranked_candidates: list[dict[str, Any]],
    known_attributes: set[str],
    language: str,
    retrieval_context: dict[str, Any] | None = None,
) -> tuple[DialogueDecision, dict[str, float], list[dict[str, int | str]], dict[str, int]]:
    """Choose with the model online; use information gain only offline."""

    scores = facet_scores(
        candidate_attributes=candidate_attributes,
        asked_attributes=asked_attributes,
        no_preference=no_preference,
        known_attributes=known_attributes,
    )

    # Keep provider imports lazy so the dialogue and understanding packages do
    # not form an import cycle during graph construction.
    from shopping_agent.infrastructure.llm.deepseek import (
        DeepSeekInvalidResponse,
        is_configured,
        request_dialogue_decision,
    )

    if is_configured():
        payload = {
            "turn": turn,
            "user_message": user_message,
            "language": language,
            "recent_conversation": conversation_history[-8:],
            "active_constraints": active_constraints,
            "no_preference": sorted(no_preference),
            "asked_attributes": asked_attributes,
            "pending_question": pending_question,
            "question_history": question_history[-8:],
            "retrieval_context": retrieval_context or {},
            "candidate_facets": {
                attribute: {
                    "information_gain_score": round(score, 6),
                    "options": question_options(candidate_attributes, attribute),
                }
                for attribute, score in scores.items()
            },
            "top_candidates": [
                {
                    "parent_asin": str(item.get("parent_asin", "")),
                    "title": str(item.get("title", ""))[:200],
                    "score": round(float(item.get("reranker_score", 0.0)), 6),
                }
                for item in ranked_candidates[:10]
            ],
        }
        try:
            raw, usage = request_dialogue_decision(payload)
            decision = DialogueDecision.model_validate(raw)
            decision.parser = "deepseek"
            decision.model_output = raw
            if not decision.message.strip():
                raise DeepSeekInvalidResponse("online dialogue message is empty")
            if decision.ask_attribute in known_attributes | no_preference:
                raise DeepSeekInvalidResponse("dialogue decision asks an excluded attribute")
            options = question_options(candidate_attributes, decision.ask_attribute)
            return decision, scores, options, usage
        except Exception as exc:
            raise RuntimeError(
                f"Online dialogue failed ({type(exc).__name__}); offline fallback is disabled"
            ) from exc

    fallback_attribute, scores = choose_question(
        turn=turn, candidate_attributes=candidate_attributes,
        asked_attributes=asked_attributes, no_preference=no_preference,
        known_attributes=known_attributes,
    )
    fallback_options = question_options(candidate_attributes, fallback_attribute)
    action: Literal["ask", "recommend"] = "ask" if fallback_attribute else "recommend"
    return (
        DialogueDecision(
            action=action,
            ask_attribute=fallback_attribute,
            reason="candidate_information_gain" if fallback_attribute else "no_useful_question",
        ),
        scores,
        fallback_options,
        {"prompt_tokens": 0, "completion_tokens": 0},
    )
