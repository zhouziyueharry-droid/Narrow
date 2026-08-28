from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_SECTIONS = {
    "evaluation",
    "turn_metrics",
    "latency",
    "model_usage",
    "mode_specific_metrics",
    "sessions",
}

REQUIRED_AGENT_NODES = {
    "understand_user",
    "validate_patch",
    "update_state",
    "build_query",
    "lexical_retrieve",
    "dense_retrieve_fallback",
    "attribute_retrieve",
    "rrf_fusion",
    "constraint_filter",
    "rerank_fallback",
    "information_gain_question",
    "build_response",
    "validate_response",
}


def validate(
    path: Path, expected_mode: str, expected_sessions: int
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_SECTIONS - report.keys()
    if missing:
        raise ValueError(f"{path}: missing sections {sorted(missing)}")
    if report.get("mode") != expected_mode:
        raise ValueError(f"{path}: expected mode {expected_mode!r}")
    if report["model_usage"]["combined"]["api_calls"] != 0:
        raise ValueError(f"{path}: traditional evaluation used an API")
    if report["evaluation"]["sample_count"] != expected_sessions:
        raise ValueError(
            f"{path}: expected {expected_sessions} sessions, got "
            f"{report['evaluation']['sample_count']}"
        )
    if len(report["sessions"]) != expected_sessions:
        raise ValueError(f"{path}: sessions length does not match expected count")

    turn_count = 0
    node_counts = {node: 0 for node in REQUIRED_AGENT_NODES}
    for session in report["sessions"]:
        if not isinstance(session.get("goal_snapshot"), dict):
            raise TypeError(f"{path}: {session['scenario_id']} has no goal snapshot")
        for turn in session["conversation"]:
            turn_count += 1
            if turn.get("agent_trace_error") is not None:
                raise ValueError(
                    f"{path}: turn {turn['turn']} trace failed: "
                    f"{turn['agent_trace_error']}"
                )
            trace = turn.get("agent_layer_trace")
            if not trace:
                raise ValueError(f"{path}: turn {turn['turn']} has no layer trace")
            observed_nodes: set[str] = set()
            for step in trace:
                if not isinstance(step.get("step"), int):
                    raise TypeError(f"{path}: trace step is not an integer")
                if not isinstance(step.get("nodes"), list) or not step["nodes"]:
                    raise ValueError(f"{path}: trace nodes are missing")
                if not isinstance(step.get("updates"), dict):
                    raise TypeError(f"{path}: trace updates are not an object")
                observed_nodes.update(str(node) for node in step["nodes"])
            missing_nodes = REQUIRED_AGENT_NODES - observed_nodes
            if missing_nodes:
                raise ValueError(
                    f"{path}: {session['scenario_id']} turn {turn['turn']} "
                    f"missing nodes {sorted(missing_nodes)}"
                )
            for node in observed_nodes:
                if node in node_counts:
                    node_counts[node] += 1
    if turn_count == 0:
        raise ValueError(f"{path}: no executed turns")
    return {
        "mode": expected_mode,
        "sessions": len(report["sessions"]),
        "turns": turn_count,
        "node_counts": node_counts,
        "trace_coverage": 1.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("techjam", type=Path)
    parser.add_argument("realistic", type=Path)
    parser.add_argument("--expected-techjam", type=int, default=1)
    parser.add_argument("--expected-realistic", type=int, default=1)
    args = parser.parse_args()
    results = [
        validate(args.techjam, "techjam", args.expected_techjam),
        validate(args.realistic, "realistic", args.expected_realistic),
    ]
    print(json.dumps({"valid": True, "reports": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
