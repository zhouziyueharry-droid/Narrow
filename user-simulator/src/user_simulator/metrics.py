from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from typing import Any

SCHEMA_VERSION = "1.0"


def _token_totals(sessions: list[dict[str, Any]]) -> dict[str, int]:
    prompt = sum(
        int(item.get("reported_token_usage", {}).get("prompt_tokens", 0))
        for item in sessions
    )
    completion = sum(
        int(item.get("reported_token_usage", {}).get("completion_tokens", 0))
        for item in sessions
    )
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def _verbalizer_totals(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    providers = sorted(
        {
            str(item.get("verbalizer_usage", {}).get("provider"))
            for item in sessions
            if item.get("verbalizer_usage", {}).get("provider")
        }
    )
    models = sorted(
        {
            str(item.get("verbalizer_usage", {}).get("model"))
            for item in sessions
            if item.get("verbalizer_usage", {}).get("model")
        }
    )
    totals = {
        key: sum(int(item.get("verbalizer_usage", {}).get(key, 0)) for item in sessions)
        for key in (
            "calls",
            "api_calls",
            "fallbacks",
            "prompt_tokens",
            "completion_tokens",
        )
    }
    totals["total_tokens"] = totals["prompt_tokens"] + totals["completion_tokens"]
    return {"providers": providers, "models": models, **totals}


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _latency_summary(values: list[float], count_key: str) -> dict[str, Any]:
    if not values:
        return {
            "available": False,
            count_key: 0,
            "total_ms": None,
            "mean_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
        }
    return {
        "available": True,
        count_key: len(values),
        "total_ms": round(sum(values), 3),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(float(_percentile(values, 0.50)), 3),
        "p95_ms": round(float(_percentile(values, 0.95)), 3),
        "p99_ms": round(float(_percentile(values, 0.99)), 3),
        "max_ms": round(max(values), 3),
    }


def _latency_metrics(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    agent_values: list[float] = []
    user_values: list[float] = []
    session_values: list[float] = []
    for session in sessions:
        for turn in session.get("conversation", []):
            if isinstance(turn.get("agent_latency_ms"), (int, float)):
                agent_values.append(float(turn["agent_latency_ms"]))
            if isinstance(turn.get("user_generation_latency_ms"), (int, float)):
                user_values.append(float(turn["user_generation_latency_ms"]))
        session_wall = session.get("latency", {}).get("session_wall_ms")
        if isinstance(session_wall, (int, float)):
            session_values.append(float(session_wall))
    return {
        "available": bool(agent_values and user_values and session_values),
        "unit": "milliseconds",
        "clock": "time.perf_counter",
        "agent": _latency_summary(agent_values, "call_count"),
        "user_generation": _latency_summary(user_values, "call_count"),
        "session_wall": _latency_summary(session_values, "session_count"),
    }


def _mean_turns(sessions: list[dict[str, Any]]) -> float | None:
    if not sessions:
        return None
    return round(statistics.fmean(int(item["turns"]) for item in sessions), 6)


def _turn_metrics(sessions: list[dict[str, Any]], max_turns: int) -> dict[str, Any]:
    turn_values = [int(item["turns"]) for item in sessions]
    successful = [item for item in sessions if item["success"]]
    unsuccessful = [item for item in sessions if not item["success"]]
    distribution = Counter(turn_values)
    first_hit_distribution = Counter(
        int(item["first_hit_turn"])
        for item in successful
        if item.get("first_hit_turn") is not None
    )
    return {
        "max_turns": max_turns,
        "session_count": len(sessions),
        "total_executed_turns": sum(turn_values),
        "mean_executed_turns": _mean_turns(sessions),
        "median_executed_turns": (
            round(float(statistics.median(turn_values)), 6) if turn_values else None
        ),
        "successful_session_mean_turns": _mean_turns(successful),
        "unsuccessful_session_mean_turns": _mean_turns(unsuccessful),
        "executed_turn_distribution": {
            str(turn): distribution.get(turn, 0) for turn in range(1, max_turns + 1)
        },
        "first_hit_turn_distribution": {
            str(turn): first_hit_distribution.get(turn, 0)
            for turn in range(1, max_turns + 1)
        },
    }


def _model_usage(
    sessions: list[dict[str, Any]],
    agent_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = dict(agent_metadata or {})
    agent_tokens = _token_totals(sessions)
    verbalizer = _verbalizer_totals(sessions)
    agent_calls = sum(int(item.get("turns", 0)) for item in sessions)
    agent_errors = sum(len(item.get("agent_errors", [])) for item in sessions)
    usage_reported_calls = sum(
        1
        for item in sessions
        for turn in item.get("conversation", [])
        if turn.get("agent_usage_reported") is True
    )
    llm_enabled = metadata.get("llm_enabled")
    agent_api_calls = 0 if llm_enabled is False else None
    agent_cost = (
        0.0 if agent_api_calls == 0 and agent_tokens["total_tokens"] == 0 else None
    )
    agent_cost_status = (
        "not_applicable_no_api_usage"
        if agent_cost == 0.0
        else "not_calculated_no_pricing"
    )
    verbalizer_cost = (
        0.0
        if verbalizer["api_calls"] == 0 and verbalizer["total_tokens"] == 0
        else None
    )
    verbalizer_cost_status = (
        "not_applicable_no_api_usage"
        if verbalizer_cost == 0.0
        else "not_calculated_no_pricing"
    )
    combined_tokens = {
        "prompt_tokens": agent_tokens["prompt_tokens"] + verbalizer["prompt_tokens"],
        "completion_tokens": (
            agent_tokens["completion_tokens"] + verbalizer["completion_tokens"]
        ),
    }
    combined_tokens["total_tokens"] = (
        combined_tokens["prompt_tokens"] + combined_tokens["completion_tokens"]
    )
    combined_api_calls = (
        agent_api_calls + verbalizer["api_calls"]
        if isinstance(agent_api_calls, int)
        else None
    )
    combined_cost = 0.0 if agent_cost == 0.0 and verbalizer_cost == 0.0 else None
    return {
        "agent": {
            "class_path": metadata.get("class_path"),
            "provider": metadata.get("provider", "unspecified"),
            "model": metadata.get("model"),
            "llm_enabled": llm_enabled,
            "respond_calls": agent_calls,
            "api_calls": agent_api_calls,
            "api_call_count_status": (
                "known_disabled" if agent_api_calls == 0 else "not_reported_by_agent"
            ),
            "usage_reported_calls": usage_reported_calls,
            "error_count": agent_errors,
            "reported_token_usage": agent_tokens,
            "estimated_cost_usd": agent_cost,
            "cost_status": agent_cost_status,
        },
        "user_verbalizer": {
            **verbalizer,
            "estimated_cost_usd": verbalizer_cost,
            "cost_status": verbalizer_cost_status,
        },
        "combined": {
            "api_calls": combined_api_calls,
            "reported_token_usage": combined_tokens,
            "estimated_cost_usd": combined_cost,
            "cost_status": (
                "not_applicable_no_api_usage"
                if combined_cost == 0.0
                else "not_calculated_no_pricing"
            ),
        },
    }


def _techjam_metric_summary(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    if not sessions:
        return {
            "sample_count": 0,
            "hit_rate_at_10": 0.0,
            "mrr": 0.0,
            "mttc": None,
        }
    count = len(sessions)
    hit_rate = sum(int(item["success"]) for item in sessions) / count
    mrr = statistics.fmean(
        0.0 if not item["success"] else 1.0 / int(item["acceptance_rank"])
        for item in sessions
    )
    mttc = statistics.fmean(
        int(item["turns"]) if item["success"] else 11 for item in sessions
    )
    return {
        "sample_count": count,
        "hit_rate_at_10": round(hit_rate, 6),
        "mrr": round(mrr, 6),
        "mttc": round(mttc, 6),
    }


def aggregate_techjam(
    sessions: list[dict[str, Any]],
    agent_metadata: dict[str, Any] | None = None,
    *,
    max_turns: int = 10,
) -> dict[str, Any]:
    overall = _techjam_metric_summary(sessions)
    mttc = float(overall["mttc"]) if overall["mttc"] is not None else 11.0
    efficiency = max(0.0, min(1.0, (11.0 - mttc) / 10.0))
    technical_score = (
        0.50 * overall["hit_rate_at_10"] + 0.30 * overall["mrr"] + 0.20 * efficiency
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        grouped[str(session.get("scenario_type", "unknown"))].append(session)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "techjam",
        "evaluation": {
            "benchmark": "techjam",
            "official_metric_contract": True,
            **overall,
            "efficiency": round(efficiency, 6),
            "recommended_technical_score": round(technical_score, 6),
        },
        "turn_metrics": _turn_metrics(sessions, max_turns),
        "latency": _latency_metrics(sessions),
        "model_usage": _model_usage(sessions, agent_metadata),
        "mode_specific_metrics": {
            "target_match": "exact_parent_asin",
            "miss_turn_value": 11,
            "scenario_metrics": {
                name: _techjam_metric_summary(grouped[name]) for name in sorted(grouped)
            },
        },
        "sessions": sessions,
    }


def aggregate_realistic(
    sessions: list[dict[str, Any]],
    agent_metadata: dict[str, Any] | None = None,
    *,
    max_turns: int = 10,
) -> dict[str, Any]:
    count = len(sessions)
    successes = [item for item in sessions if item["success"]]
    mrr = (
        sum(
            1.0 / item["acceptance_rank"]
            for item in successes
            if item["acceptance_rank"]
        )
        / count
        if count
        else 0.0
    )
    hard_rates = [
        item["acceptance"]["hard_matches"] / item["acceptance"]["hard_total"]
        for item in successes
        if item.get("acceptance", {}).get("hard_total", 0)
    ]
    persona_distribution = Counter(
        str(item.get("persona", "unknown")) for item in sessions
    )
    difficulty_distribution = Counter(
        str(item.get("scenario_type", "realistic")) for item in sessions
    )
    blocked_candidate_events = sum(
        int(item.get("acceptance_gate", {}).get("blocked_candidate_events", 0))
        for item in sessions
    )
    accepted_while_agent_asks = sum(
        bool(item.get("success"))
        and bool(item.get("conversation"))
        and bool(item["conversation"][-1].get("ask_attribute"))
        for item in sessions
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "realistic",
        "evaluation": {
            "benchmark": "catalog_generated_realistic",
            "official_metric_contract": False,
            "sample_count": count,
            "successful_sessions": len(successes),
            "success_rate": round(len(successes) / count, 6) if count else 0.0,
            "mrr": round(mrr, 6),
        },
        "turn_metrics": _turn_metrics(sessions, max_turns),
        "latency": _latency_metrics(sessions),
        "model_usage": _model_usage(sessions, agent_metadata),
        "mode_specific_metrics": {
            "acceptance": "need_based",
            "hard_constraint_satisfaction_at_acceptance": (
                round(statistics.fmean(hard_rates), 6) if hard_rates else None
            ),
            "mean_soft_matches_at_acceptance": (
                round(
                    statistics.fmean(
                        item.get("acceptance", {}).get("soft_matches", 0)
                        for item in successes
                    ),
                    6,
                )
                if successes
                else None
            ),
            "persona_distribution": dict(sorted(persona_distribution.items())),
            "difficulty_distribution": dict(sorted(difficulty_distribution.items())),
            "blocked_candidate_events": blocked_candidate_events,
            "accepted_while_agent_asks": accepted_while_agent_asks,
            "override_events": sum(
                int(item.get("override_count", 0)) for item in sessions
            ),
            "relaxation_events": sum(
                int(item.get("relaxation_count", 0)) for item in sessions
            ),
        },
        "sessions": sessions,
    }
