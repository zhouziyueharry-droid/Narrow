from __future__ import annotations

import json
import sys
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


def validate(path: Path, expected_mode: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    missing = REQUIRED_SECTIONS - report.keys()
    if missing:
        raise ValueError(f"{path}: missing sections {sorted(missing)}")
    if report.get("mode") != expected_mode:
        raise ValueError(f"{path}: expected mode {expected_mode!r}")
    if report["model_usage"]["combined"]["api_calls"] != 0:
        raise ValueError(f"{path}: traditional smoke used an API")

    turn_count = 0
    for session in report["sessions"]:
        for turn in session["conversation"]:
            turn_count += 1
            if turn.get("agent_trace_error") is not None:
                raise ValueError(
                    f"{path}: turn {turn['turn']} trace failed: "
                    f"{turn['agent_trace_error']}"
                )
            if not turn.get("agent_layer_trace"):
                raise ValueError(f"{path}: turn {turn['turn']} has no layer trace")
    if turn_count == 0:
        raise ValueError(f"{path}: no executed turns")
    return {"mode": expected_mode, "sessions": len(report["sessions"]), "turns": turn_count}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate_smoke_traces.py TECHJAM_JSON REALISTIC_JSON")
    results = [
        validate(Path(sys.argv[1]), "techjam"),
        validate(Path(sys.argv[2]), "realistic"),
    ]
    print(json.dumps({"valid": True, "reports": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
