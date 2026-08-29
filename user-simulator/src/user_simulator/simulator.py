from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .acceptance import AcceptanceChecker
from .adapters import ShoppingAgentAdapter
from .metrics import aggregate_realistic, aggregate_techjam
from .models import (
    AcceptanceResult,
    ConversationTurn,
    NeedBasedGoal,
    Recommendation,
    ScenarioSpec,
    TargetProductGoal,
    UserState,
)
from .personas import get_persona
from .policy import UserPolicy
from .techjam import TechJamUserPolicy
from .verbalizers import TemplateVerbalizer, VerbalizationRequest


def _goal_constraints(goal: TargetProductGoal | NeedBasedGoal):
    if isinstance(goal, TargetProductGoal):
        return list(goal.constraints)
    return [*goal.hard_constraints, *goal.soft_preferences]


def _goal_snapshot(goal: TargetProductGoal | NeedBasedGoal) -> dict[str, Any]:
    """Serialize evaluation-only truth without exposing it to the Agent."""

    if isinstance(goal, TargetProductGoal):
        return {
            "goal_type": goal.goal_type,
            "goal_id": goal.goal_id,
            "target_product_id": goal.target_product_id,
            "category": goal.category,
            "constraints": [asdict(item) for item in goal.constraints],
            "source_dataset": goal.source_dataset,
        }
    return {
        "goal_type": goal.goal_type,
        "goal_id": goal.goal_id,
        "category": goal.category,
        "hard_constraints": [asdict(item) for item in goal.hard_constraints],
        "soft_preferences": [asdict(item) for item in goal.soft_preferences],
        "alternatives": goal.alternatives,
        "min_soft_matches": goal.min_soft_matches,
        "source_dataset": goal.source_dataset,
    }


def _dialogue_act_snapshot(act) -> dict[str, Any] | None:
    if act is None:
        return None
    return {
        "type": act.type.value,
        "attribute": act.attribute,
        "values": list(act.values),
        "reason_code": act.reason_code,
        "references": list(act.references),
        "allowed_facts": [asdict(item) for item in act.allowed_facts],
        "surface_text": act.surface_text,
    }


def _catalog_recommendations(
    response, catalog: dict, top_k: int
) -> list[Recommendation]:
    raw_recommendations = (
        response.raw.get("recommendations") if isinstance(response.raw, dict) else None
    )
    if not isinstance(raw_recommendations, list):
        return [
            item for item in response.recommendations if item.product_id in catalog
        ][:top_k]
    normalized: list[Recommendation] = []
    seen: set[str] = set()
    for raw in raw_recommendations:
        if isinstance(raw, dict):
            product_id = raw.get("parent_asin", raw.get("product_id", ""))
            score = raw.get("score")
        else:
            product_id = raw
            score = None
        product_id = str(product_id).strip()
        if not product_id or product_id in seen or product_id not in catalog:
            continue
        seen.add(product_id)
        normalized.append(
            Recommendation(
                product_id=product_id,
                score=float(score) if isinstance(score, (int, float)) else None,
                raw=raw,
            )
        )
        if len(normalized) >= top_k:
            break
    return normalized


class SimulatorSession:
    def __init__(
        self,
        scenario: ScenarioSpec,
        catalog: dict,
        agent: ShoppingAgentAdapter,
        verbalizer=None,
        top_k: int = 10,
    ):
        self.scenario = scenario
        self._initial_goal_snapshot = _goal_snapshot(scenario.goal)
        self.catalog = catalog
        self.agent = agent
        self.top_k = top_k
        self.verbalizer = verbalizer or TemplateVerbalizer()
        self._verbalizer_start = self.verbalizer.diagnostics()
        self._session_wall_ms = 0.0
        self.policy = (
            TechJamUserPolicy(scenario)
            if scenario.protocol == "techjam"
            else UserPolicy(scenario)
        )
        self.acceptance = AcceptanceChecker(catalog)
        self.state = UserState(
            session_id=f"sim_{uuid.uuid4().hex}",
            turn=0,
            goal=scenario.goal,
            persona=get_persona(scenario.persona_template),
            active_constraints=_goal_constraints(scenario.goal),
        )

    def _history_for_verbalizer(self) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for turn in self.state.conversation_history:
            result.append(("user", turn.user_message))
            if turn.agent_response and turn.agent_response.message:
                result.append(("assistant", turn.agent_response.message))
        return result

    def _say(self, act) -> tuple[str, float]:
        started = time.perf_counter()
        if act.surface_text is not None:
            text = act.surface_text
        else:
            request = VerbalizationRequest(
                persona=self.state.persona,
                dialogue_act=act,
                allowed_facts=list(act.allowed_facts),
                conversation_history=self._history_for_verbalizer(),
            )
            text = self.verbalizer.verbalize(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return text, round(elapsed_ms, 3)

    def run(self, user_profile: dict | None = None) -> dict[str, Any]:
        session_started = time.perf_counter()
        effective_profile = (
            user_profile
            or self.scenario.user_profile
            or {"persona": self.state.persona.name}
        )
        self.agent.reset(self.state.session_id, effective_profile)
        initial_act = self.policy.initial_act(self.state)
        user_message, user_generation_latency_ms = self._say(initial_act)
        self.state.last_dialogue_act = initial_act
        user_dialogue_act = initial_act

        acceptance_result = None
        for turn in range(1, self.scenario.max_turns + 1):
            self.state.turn = turn
            agent_started = time.perf_counter()
            response = self.agent.respond(
                self.state.session_id, user_message, turn, self.top_k
            )
            agent_latency_ms = round((time.perf_counter() - agent_started) * 1000.0, 3)
            agent_layer_trace, agent_trace_error = self.agent.get_turn_trace(
                self.state.session_id, turn, candidate_limit=max(self.top_k, 20)
            )
            if self.scenario.protocol == "techjam" and response.error:
                response.ask_attribute = None
                response.recommendations = []
                response.usage = None
            else:
                response.recommendations = _catalog_recommendations(
                    response, self.catalog, self.top_k
                )
            acceptance_result = self.acceptance.check(
                self.state.goal, response.recommendations
            )
            acceptance_candidate = acceptance_result.accepted
            acceptance_block_reason = None
            if self.scenario.protocol == "realistic" and acceptance_result.accepted:
                if turn < self.scenario.min_turns_before_acceptance:
                    acceptance_block_reason = "minimum_conversation_turns_not_reached"
                elif self.scenario.require_no_pending_question and response.ask_attribute:
                    acceptance_block_reason = "agent_still_asking_clarification"
                if acceptance_block_reason:
                    acceptance_result = AcceptanceResult(
                        False,
                        hard_matches=acceptance_result.hard_matches,
                        hard_total=acceptance_result.hard_total,
                        soft_matches=acceptance_result.soft_matches,
                        evidence={
                            **acceptance_result.evidence,
                            "blocked_by": acceptance_block_reason,
                            "candidate_product_id": acceptance_result.product_id,
                            "candidate_rank": acceptance_result.rank,
                        },
                    )
            if (
                self.scenario.protocol == "techjam"
                and isinstance(self.policy, TechJamUserPolicy)
                and not self.policy.acceptance_allowed(turn)
            ):
                acceptance_result = AcceptanceResult(
                    False,
                    evidence={"blocked_by": "intent_override_not_applied"},
                )
            act = self.policy.next_act(self.state, response, acceptance_result.accepted)
            self.state.last_dialogue_act = act
            self.state.conversation_history.append(
                ConversationTurn(
                    turn=turn,
                    user_message=user_message,
                    agent_response=response,
                    user_dialogue_act=user_dialogue_act,
                    dialogue_act=act,
                    user_generation_latency_ms=user_generation_latency_ms,
                    agent_latency_ms=agent_latency_ms,
                    agent_usage_reported=response.usage is not None,
                    agent_layer_trace=agent_layer_trace,
                    agent_trace_error=agent_trace_error,
                    acceptance_candidate=acceptance_candidate,
                    acceptance_block_reason=acceptance_block_reason,
                )
            )

            if acceptance_result.accepted:
                self.state.accepted_product_id = acceptance_result.product_id
                self.state.terminated = True
                self.state.termination_reason = "accept"
                break

            if turn == self.scenario.max_turns:
                self.state.terminated = True
                self.state.termination_reason = "max_turns"
                break

            user_message, user_generation_latency_ms = self._say(act)
            user_dialogue_act = act

        self._session_wall_ms = round(
            (time.perf_counter() - session_started) * 1000.0, 3
        )
        return self.result(acceptance_result)

    def result(self, acceptance_result=None) -> dict[str, Any]:
        rank = (
            acceptance_result.rank
            if acceptance_result and acceptance_result.accepted
            else None
        )
        prompt_tokens = sum(
            item.agent_response.usage.prompt_tokens
            for item in self.state.conversation_history
            if item.agent_response and item.agent_response.usage
        )
        completion_tokens = sum(
            item.agent_response.usage.completion_tokens
            for item in self.state.conversation_history
            if item.agent_response and item.agent_response.usage
        )
        verbalizer_now = self.verbalizer.diagnostics()
        verbalizer_usage = {
            "provider": verbalizer_now["provider"],
            "model": verbalizer_now["model"],
            "calls": int(verbalizer_now["calls"])
            - int(self._verbalizer_start["calls"]),
            "api_calls": int(verbalizer_now["api_calls"])
            - int(self._verbalizer_start["api_calls"]),
            "fallbacks": int(verbalizer_now["fallbacks"])
            - int(self._verbalizer_start["fallbacks"]),
            "prompt_tokens": int(verbalizer_now["prompt_tokens"])
            - int(self._verbalizer_start["prompt_tokens"]),
            "completion_tokens": int(verbalizer_now["completion_tokens"])
            - int(self._verbalizer_start["completion_tokens"]),
            "last_error": verbalizer_now["last_error"],
        }
        agent_latencies = [
            item.agent_latency_ms for item in self.state.conversation_history
        ]
        user_generation_latencies = [
            item.user_generation_latency_ms for item in self.state.conversation_history
        ]
        return {
            "session_id": self.state.session_id,
            "scenario_id": self.scenario.scenario_id,
            "sample_id": self.scenario.scenario_id,
            "protocol": self.scenario.protocol,
            "scenario_type": self.scenario.scenario_type,
            "difficulty_profile": self.scenario.difficulty_profile,
            "acceptance_gate": {
                "min_turns_before_acceptance": self.scenario.min_turns_before_acceptance,
                "require_no_pending_question": self.scenario.require_no_pending_question,
                "blocked_candidate_events": sum(
                    item.acceptance_block_reason is not None
                    for item in self.state.conversation_history
                ),
            },
            "goal_type": self.state.goal.goal_type,
            "goal_snapshot": self._initial_goal_snapshot,
            "effective_goal_snapshot": {
                "active_constraints": [
                    asdict(item) for item in self.state.active_constraints if item.active
                ],
                "removed_constraints": [
                    asdict(item) for item in self.state.removed_constraints
                ],
                "override_history": [asdict(item) for item in self.state.override_history],
                "relaxation_history": [
                    asdict(item) for item in self.state.relaxation_history
                ],
            },
            "persona": self.state.persona.name,
            "success": self.state.termination_reason == "accept",
            "hit": self.state.termination_reason == "accept",
            "termination_reason": self.state.termination_reason,
            "turns": self.state.turn,
            "first_hit_turn": self.state.turn
            if self.state.termination_reason == "accept"
            else None,
            "accepted_product_id": self.state.accepted_product_id,
            "acceptance_rank": rank,
            "best_rank": rank,
            "reciprocal_rank": 1.0 / rank if rank else 0.0,
            "override_count": len(self.state.override_history),
            "relaxation_count": len(self.state.relaxation_history),
            "acceptance": {
                "hard_matches": acceptance_result.hard_matches
                if acceptance_result
                else 0,
                "hard_total": acceptance_result.hard_total if acceptance_result else 0,
                "soft_matches": acceptance_result.soft_matches
                if acceptance_result
                else 0,
                "evidence": acceptance_result.evidence if acceptance_result else {},
            },
            "reported_token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "verbalizer_usage": verbalizer_usage,
            "latency": {
                "unit": "milliseconds",
                "agent": {
                    "call_count": len(agent_latencies),
                    "total_ms": round(sum(agent_latencies), 3),
                },
                "user_generation": {
                    "call_count": len(user_generation_latencies),
                    "total_ms": round(sum(user_generation_latencies), 3),
                },
                "session_wall_ms": self._session_wall_ms,
            },
            "agent_errors": [
                item.agent_response.error
                for item in self.state.conversation_history
                if item.agent_response and item.agent_response.error
            ],
            "conversation": [
                {
                    "turn": item.turn,
                    "user": item.user_message,
                    "assistant": item.agent_response.message
                    if item.agent_response
                    else "",
                    "ask_attribute": item.agent_response.ask_attribute
                    if item.agent_response
                    else None,
                    "recommendations": [
                        r.product_id
                        for r in (
                            item.agent_response.recommendations
                            if item.agent_response
                            else []
                        )
                    ],
                    "user_dialogue_act": _dialogue_act_snapshot(
                        item.user_dialogue_act
                    ),
                    "next_dialogue_act": item.dialogue_act.type.value
                    if item.dialogue_act
                    else None,
                    "next_dialogue_act_detail": _dialogue_act_snapshot(
                        item.dialogue_act
                    ),
                    "user_generation_latency_ms": item.user_generation_latency_ms,
                    "agent_latency_ms": item.agent_latency_ms,
                    "agent_usage_reported": item.agent_usage_reported,
                    "agent_layer_trace": item.agent_layer_trace,
                    "agent_trace_error": item.agent_trace_error,
                    "acceptance_candidate": item.acceptance_candidate,
                    "acceptance_block_reason": item.acceptance_block_reason,
                    "reported_token_usage": {
                        "prompt_tokens": (
                            item.agent_response.usage.prompt_tokens
                            if item.agent_response and item.agent_response.usage
                            else 0
                        ),
                        "completion_tokens": (
                            item.agent_response.usage.completion_tokens
                            if item.agent_response and item.agent_response.usage
                            else 0
                        ),
                    },
                }
                for item in self.state.conversation_history
            ],
        }


class Simulator:
    def __init__(
        self,
        catalog: dict,
        agent: ShoppingAgentAdapter,
        verbalizer=None,
        top_k: int = 10,
        agent_metadata: dict[str, Any] | None = None,
    ):
        self.catalog = catalog
        self.agent = agent
        self.verbalizer = verbalizer or TemplateVerbalizer()
        self.top_k = top_k
        self.agent_metadata = agent_metadata or {}

    def run_scenario(
        self, scenario: ScenarioSpec, user_profile: dict | None = None
    ) -> dict[str, Any]:
        session = SimulatorSession(
            scenario, self.catalog, self.agent, self.verbalizer, self.top_k
        )
        result: dict[str, Any] | None = None
        try:
            result = session.run(user_profile)
            return result
        finally:
            release_error = self.agent.release_session(session.state.session_id)
            if result is not None:
                result["session_release_error"] = release_error

    def run_many(
        self,
        scenarios: list[ScenarioSpec],
        *,
        session_output: str | Path | None = None,
        event_output: str | Path | None = None,
    ) -> dict[str, Any]:
        session_path = Path(session_output) if session_output else None
        event_path = Path(event_output) if event_output else None
        if session_path:
            session_path.parent.mkdir(parents=True, exist_ok=True)
        if event_path:
            event_path.parent.mkdir(parents=True, exist_ok=True)
        session_handle = (
            session_path.open("w", encoding="utf-8") if session_path else None
        )
        event_handle = event_path.open("w", encoding="utf-8") if event_path else None
        sessions: list[dict[str, Any]] = []
        try:
            for index, scenario in enumerate(scenarios, 1):
                started = time.perf_counter()
                if event_handle:
                    event_handle.write(json.dumps({
                        "timestamp": datetime.now(UTC).isoformat(),
                        "event": "session_started",
                        "index": index,
                        "total": len(scenarios),
                        "scenario_id": scenario.scenario_id,
                        "protocol": scenario.protocol,
                    }) + "\n")
                    event_handle.flush()
                try:
                    session = self.run_scenario(scenario)
                except Exception as exc:
                    if event_handle:
                        event_handle.write(json.dumps({
                            "timestamp": datetime.now(UTC).isoformat(),
                            "event": "session_failed",
                            "index": index,
                            "total": len(scenarios),
                            "scenario_id": scenario.scenario_id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "elapsed_ms": round(
                                (time.perf_counter() - started) * 1000.0, 3
                            ),
                        }) + "\n")
                        event_handle.flush()
                    raise
                sessions.append(session)
                if session_handle:
                    session_handle.write(json.dumps(session, ensure_ascii=False) + "\n")
                    session_handle.flush()
                if event_handle:
                    event_handle.write(json.dumps({
                        "timestamp": datetime.now(UTC).isoformat(),
                        "event": "session_completed",
                        "index": index,
                        "total": len(scenarios),
                        "scenario_id": scenario.scenario_id,
                        "success": session["success"],
                        "turns": session["turns"],
                        "elapsed_ms": round(
                            (time.perf_counter() - started) * 1000.0, 3
                        ),
                    }) + "\n")
                    event_handle.flush()
        finally:
            if session_handle:
                session_handle.close()
            if event_handle:
                event_handle.close()
        protocols = {scenario.protocol for scenario in scenarios}
        if len(protocols) > 1:
            raise ValueError("run_many requires scenarios from one protocol")
        protocol = next(iter(protocols), "realistic")
        max_turns = max((scenario.max_turns for scenario in scenarios), default=10)
        if protocol == "techjam":
            return aggregate_techjam(sessions, self.agent_metadata, max_turns=max_turns)
        return aggregate_realistic(sessions, self.agent_metadata, max_turns=max_turns)
