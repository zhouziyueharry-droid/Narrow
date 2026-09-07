from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from validate_smoke_traces import REQUIRED_AGENT_NODES, REQUIRED_SECTIONS

EXPECTED_SCENARIO_TYPES = {
    "realistic_hard:hidden_preferences",
    "realistic_hard:preference_override",
    "realistic_hard:budget_relaxation",
    "realistic_hard:override_and_relaxation",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(path: Path, expected_sessions: int) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(report, dict), "report root must be an object")
    missing = REQUIRED_SECTIONS - report.keys()
    require(not missing, f"missing report sections: {sorted(missing)}")
    require(report.get("mode") == "realistic", "mode must be realistic")
    require(
        report["evaluation"].get("official_metric_contract") is False,
        "realistic results must not claim the official metric contract",
    )
    sessions = report["sessions"]
    require(len(sessions) == expected_sessions, "unexpected session count")
    require(
        report["evaluation"].get("sample_count") == expected_sessions,
        "evaluation sample_count does not match sessions",
    )

    agent_usage = report["model_usage"]["agent"]
    verbalizer_usage = report["model_usage"]["user_verbalizer"]
    require(agent_usage.get("llm_enabled") is True, "Agent LLM is not enabled")
    require(agent_usage.get("provider") == "deepseek", "Agent did not use DeepSeek")
    require(agent_usage.get("error_count") == 0, "Agent reported API errors")
    require(
        agent_usage.get("reported_token_usage", {}).get("total_tokens", 0) > 0,
        "Agent did not report token usage",
    )
    require(
        "deepseek" in verbalizer_usage.get("providers", []),
        "user verbalizer did not use DeepSeek",
    )
    require(verbalizer_usage.get("api_calls", 0) > 0, "no verbalizer API calls")
    require(verbalizer_usage.get("fallbacks") == 0, "verbalizer used a fallback")

    scenario_types: Counter[str] = Counter()
    personas: Counter[str] = Counter()
    observed_nodes: Counter[str] = Counter()
    turns = 0
    blocked_candidates = 0
    accepted_while_asking = 0
    trace_errors = 0
    release_errors = 0

    for session in sessions:
        require(session.get("difficulty_profile") == "hard_v1", "wrong difficulty")
        scenario_types[session["scenario_type"]] += 1
        personas[session["persona"]] += 1
        goal = session["goal_snapshot"]
        require(goal.get("min_soft_matches") == 2, "min_soft_matches must be 2")
        require(len(goal.get("soft_preferences", [])) >= 3, "too few soft preferences")
        if session.get("session_release_error"):
            release_errors += 1

        conversation = session.get("conversation", [])
        require(conversation, f"{session['scenario_id']}: empty conversation")
        for turn in conversation:
            turns += 1
            if turn.get("agent_trace_error"):
                trace_errors += 1
            trace = turn.get("agent_layer_trace")
            require(trace, f"{session['scenario_id']} turn {turn['turn']}: no trace")
            turn_nodes: set[str] = set()
            for step in trace:
                require(isinstance(step.get("step"), int), "invalid trace step")
                require(isinstance(step.get("nodes"), list), "invalid trace nodes")
                require(isinstance(step.get("updates"), dict), "invalid trace updates")
                turn_nodes.update(str(node) for node in step["nodes"])
            missing_nodes = REQUIRED_AGENT_NODES - turn_nodes
            require(
                not missing_nodes,
                f"{session['scenario_id']} turn {turn['turn']}: "
                f"missing nodes {sorted(missing_nodes)}",
            )
            observed_nodes.update(turn_nodes)
            if turn.get("acceptance_candidate") and turn.get("acceptance_block_reason"):
                blocked_candidates += 1

        if session.get("success"):
            final_turn = conversation[-1]
            if final_turn.get("ask_attribute") is not None:
                accepted_while_asking += 1

    if expected_sessions >= 4:
        missing_types = EXPECTED_SCENARIO_TYPES - scenario_types.keys()
        require(not missing_types, f"missing scenario types: {sorted(missing_types)}")
    require(trace_errors == 0, f"found {trace_errors} trace errors")
    require(release_errors == 0, f"found {release_errors} session release errors")
    require(accepted_while_asking == 0, "accepted while Agent was still asking")
    require(
        blocked_candidates
        == report["mode_specific_metrics"].get("blocked_candidate_events"),
        "blocked candidate metric does not match detailed turns",
    )

    return {
        "valid": True,
        "report": str(path),
        "sessions": len(sessions),
        "turns": turns,
        "successes": sum(bool(session.get("success")) for session in sessions),
        "scenario_types": dict(sorted(scenario_types.items())),
        "personas": dict(sorted(personas.items())),
        "blocked_candidate_events": blocked_candidates,
        "accepted_while_agent_asks": accepted_while_asking,
        "agent_nodes": sorted(node for node in observed_nodes if node in REQUIRED_AGENT_NODES),
        "agent_total_tokens": agent_usage["reported_token_usage"]["total_tokens"],
        "verbalizer_total_tokens": verbalizer_usage["total_tokens"],
        "verbalizer_api_calls": verbalizer_usage["api_calls"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--expected-sessions", type=int, default=24)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.report, args.expected_sessions)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
