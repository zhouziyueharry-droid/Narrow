from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from dotenv import load_dotenv


def _jsonl_write(handle: TextIO, payload: dict[str, Any]) -> None:
    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    handle.flush()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_path(path: Path, project_root: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), project_root.resolve())).as_posix()
    except ValueError:
        return f"external/{path.name}"


def _git_value(project_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip()


def _score(sessions: list[dict[str, Any]], usage: dict[str, int]) -> dict[str, Any]:
    from evaluator.local_evaluator import metric_summary

    overall = metric_summary(sessions)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    technical_score = (
        0.50 * overall["hit_rate_at_10"]
        + 0.30 * overall["mrr"]
        + 0.20 * efficiency
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        grouped[str(session["scenario_type"])].append(session)
    return {
        **overall,
        "efficiency": round(efficiency, 6),
        "recommended_technical_score": round(technical_score, 6),
        "reported_token_usage": {
            **usage,
            "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
        },
        "scenario_metrics": {
            name: metric_summary(grouped[name]) for name in sorted(grouped)
        },
    }


def _candidate_counts(node_trace: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for stage in node_trace:
        for key, value in stage.get("updates", {}).items():
            if isinstance(value, dict) and isinstance(value.get("count"), int):
                result[key] = int(value["count"])
    return result


def _markdown_report(
    summary: dict[str, Any],
    config: dict[str, Any],
    sessions: list[dict[str, Any]],
    turns_by_sample: dict[str, list[dict[str, Any]]],
) -> str:
    lines = [
        "# Traced Evaluation Report",
        "",
        f"Run: `{config['run_id']}`  ",
        f"Model: `{config['model']}`  ",
        f"LLM enabled: `{config['llm_enabled']}`  ",
        f"Git commit: `{config['git_commit'] or 'uncommitted workspace'}`",
        "",
        "## Score",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Samples | {summary['sample_count']} |",
        f"| Hit Rate@10 | {summary['hit_rate_at_10']:.6f} |",
        f"| MRR | {summary['mrr']:.6f} |",
        f"| MTTC | {summary['mttc']:.6f} |",
        f"| Efficiency | {summary['efficiency']:.6f} |",
        f"| Technical Score | {summary['recommended_technical_score']:.6f} |",
        f"| Prompt tokens | {summary['reported_token_usage']['prompt_tokens']} |",
        f"| Completion tokens | {summary['reported_token_usage']['completion_tokens']} |",
        "",
        "## Scenario breakdown",
        "",
        "| Scenario | Samples | Hit Rate | MRR | MTTC |",
        "|---|---:|---:|---:|---:|",
    ]
    for scenario, metrics in summary["scenario_metrics"].items():
        lines.append(
            f"| {scenario} | {metrics['sample_count']} | "
            f"{metrics['hit_rate_at_10']:.6f} | {metrics['mrr']:.6f} | "
            f"{metrics['mttc']:.6f} |"
        )

    lines.extend([
        "",
        "## Representative conversations",
        "",
        "One long successful session per scenario is shown below. Complete data",
        "for every session is available in `sessions.jsonl`, `turns.jsonl`, and",
        "`node_traces.jsonl`.",
    ])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        grouped[str(session["scenario_type"])].append(session)
    selected = []
    for scenario in sorted(grouped):
        successful = [item for item in grouped[scenario] if item["hit"]]
        pool = successful or grouped[scenario]
        selected.append(max(pool, key=lambda item: int(item["turn_count"])))

    for session in selected:
        sample_id = str(session["sample_id"])
        title = str(session.get("target_product", {}).get("title") or "unknown")
        lines.extend([
            "",
            f"### {sample_id} — {session['scenario_type']}",
            "",
            f"Target: `{session['target_parent_asin']}` — {title}",
            "",
            f"Result: hit=`{session['hit']}`, first turn=`{session['first_hit_turn']}`, "
            f"rank=`{session['best_rank']}`",
        ])
        for turn in turns_by_sample.get(sample_id, []):
            lines.extend([
                "",
                f"#### Turn {turn['turn']}",
                "",
                f"**User:** {turn['user_message']}",
                "",
                f"**Agent:** {turn['agent_response'].get('message', '')}",
                "",
                f"- Asked attribute: `{turn['agent_response'].get('ask_attribute')}`",
                f"- Semantic query: `{turn['intent_state'].get('semantic_query', '')}`",
                f"- Target rank this turn: `{turn.get('target_rank')}`",
                f"- Candidate counts: `{json.dumps(turn['candidate_counts'], ensure_ascii=False)}`",
                f"- Active constraints: `{json.dumps(turn['intent_state'].get('active_constraints', []), ensure_ascii=False)}`",
                "- Top recommendations: "
                + ", ".join(
                    f"`{item.get('parent_asin')}`"
                    + (" **(target)**" if item.get("parent_asin") == session["target_parent_asin"] else "")
                    for item in turn["agent_response"].get("recommendations", [])[:5]
                ),
                "",
                "| Node stage | Updated fields |",
                "|---|---|",
            ])
            for stage in turn.get("node_trace", []):
                nodes = " + ".join(stage.get("nodes", []))
                fields = ", ".join(stage.get("updates", {}).keys())
                lines.append(f"| {nodes} | {fields} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run evaluator with durable conversations and node traces")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output-root", default="evaluation_runs")
    parser.add_argument("--candidate-limit", type=int, default=20)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--llm", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    load_dotenv(project_root / ".env")
    if args.llm:
        if not os.getenv("DEEPSEEK_API_KEY", "").strip():
            raise SystemExit("DEEPSEEK_API_KEY is empty; cannot run --llm")
        os.environ["SHOPPING_AGENT_ENABLE_LLM"] = "true"
    else:
        os.environ["SHOPPING_AGENT_ENABLE_LLM"] = "false"

    from evaluator.local_evaluator import (
        MAX_TURNS,
        TOP_K,
        catalog_index,
        coarse_category,
        customer_reply,
        initial_message,
        load_jsonl,
        materialize_hidden_fields,
        normalize_recommendations,
    )
    from shopping_agent.application.service import ShoppingAgent

    catalog_path = (project_root / args.catalog).resolve()
    dataset_path = (project_root / args.dataset).resolve()
    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%z")
    output_root = (project_root / args.output_root).resolve()
    output_dir = output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "LATEST.txt").write_text(run_id + "\n", encoding="utf-8")

    samples = load_jsonl(dataset_path)
    if args.max_samples is not None:
        samples = samples[: max(args.max_samples, 0)]
    config = {
        "run_id": run_id,
        "started_at": datetime.now().astimezone().isoformat(),
        "llm_enabled": bool(args.llm),
        "provider": "deepseek" if args.llm else "local_fallback",
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash") if args.llm else "local_fallback",
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com") if args.llm else None,
        "catalog": _portable_path(catalog_path, project_root),
        "catalog_sha256": _sha256(catalog_path),
        "dataset": _portable_path(dataset_path, project_root),
        "dataset_sha256": _sha256(dataset_path),
        "sample_count": len(samples),
        "candidate_limit_per_node": args.candidate_limit,
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": _git_value(project_root, "rev-parse", "HEAD"),
        "git_status": _git_value(project_root, "status", "--short"),
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    catalog_ids, categories, products = catalog_index(catalog_path)
    agent = ShoppingAgent(catalog_path)
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    session_scores: list[dict[str, Any]] = []
    session_artifacts: list[dict[str, Any]] = []
    turns_by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    started = time.perf_counter()

    with (
        (output_dir / "sessions.jsonl").open("w", encoding="utf-8") as session_file,
        (output_dir / "turns.jsonl").open("w", encoding="utf-8") as turn_file,
        (output_dir / "node_traces.jsonl").open("w", encoding="utf-8") as node_file,
    ):
        for sample_index, sample in enumerate(samples, start=1):
            sample_id = str(sample["sample_id"])
            session_id = f"{run_id}:{sample_id}"
            agent.reset(session_id, sample["user_profile"])
            target = str(sample["ground_truth"]["parent_asin"])
            intent_card, behavior = materialize_hidden_fields(sample, products)
            effective_sample = {**sample, "intent_card": intent_card, "behavior": behavior}
            disclosed: set[str] = set()
            boundary_used = False
            override_applied = sample["scenario_type"] != "intent_override"
            user_message = initial_message(
                effective_sample,
                coarse_category(categories.get(target, [])),
                disclosed,
            )
            hit_turn: int | None = None
            best_rank: int | None = None
            completed_turns = 0
            session_errors: list[str] = []

            for turn in range(1, MAX_TURNS + 1):
                completed_turns = turn
                call_started = time.perf_counter()
                error: str | None = None
                try:
                    response = agent.respond(session_id, user_message, turn, TOP_K)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    session_errors.append(error)
                    response = {"message": "", "ask_attribute": None, "recommendations": [], "usage": {}}
                latency_ms = round((time.perf_counter() - call_started) * 1000, 3)
                if not isinstance(response, dict) or not isinstance(response.get("message"), str):
                    error = error or "invalid_agent_response"
                    response = {"message": "", "ask_attribute": None, "recommendations": [], "usage": {}}
                turn_usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
                for key in usage:
                    value = turn_usage.get(key)
                    if isinstance(value, int) and value >= 0:
                        usage[key] += value

                ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
                raw_rank = ranked.index(target) + 1 if target in ranked else None
                target_rank = raw_rank if override_applied else None
                try:
                    node_trace = agent.get_turn_trace(
                        session_id,
                        turn,
                        candidate_limit=max(args.candidate_limit, 1),
                    )
                except Exception as exc:
                    node_trace = []
                    trace_error = f"trace:{type(exc).__name__}: {exc}"
                    session_errors.append(trace_error)
                    error = error or trace_error
                try:
                    intent_state = agent.get_intent_state(session_id)
                except Exception:
                    intent_state = {}

                turn_record = {
                    "run_id": run_id,
                    "sample_id": sample_id,
                    "scenario_type": sample["scenario_type"],
                    "turn": turn,
                    "user_message": user_message,
                    "agent_response": response,
                    "recommended_parent_asins": ranked,
                    "target_parent_asin": target,
                    "raw_target_rank": raw_rank,
                    "target_rank": target_rank,
                    "override_applied": override_applied,
                    "latency_ms": latency_ms,
                    "intent_state": intent_state,
                    "candidate_counts": _candidate_counts(node_trace),
                    "node_trace": node_trace,
                    "error": error,
                }
                _jsonl_write(turn_file, {key: value for key, value in turn_record.items() if key != "node_trace"})
                turns_by_sample[sample_id].append(turn_record)
                for stage_index, stage in enumerate(node_trace, start=1):
                    _jsonl_write(node_file, {
                        "run_id": run_id,
                        "sample_id": sample_id,
                        "scenario_type": sample["scenario_type"],
                        "turn": turn,
                        "stage_index": stage_index,
                        **stage,
                    })

                if target_rank is not None:
                    best_rank = target_rank
                    hit_turn = turn
                    break
                if turn == MAX_TURNS:
                    break
                override = effective_sample.get("behavior", {}).get("override") or {}
                if not override_applied and turn + 1 == int(override.get("turn", 3)):
                    override_applied = True
                    new_value = str(override.get("new_value", ""))
                    if new_value:
                        disclosed.add(new_value)
                    user_message = str(
                        override.get("message", "Actually, please ignore my earlier preference.")
                    )
                else:
                    user_message, boundary_used = customer_reply(
                        effective_sample,
                        response.get("ask_attribute"),
                        disclosed,
                        boundary_used,
                    )

            score_record = {
                "sample_id": sample_id,
                "scenario_type": sample["scenario_type"],
                "hit": hit_turn is not None,
                "first_hit_turn": hit_turn,
                "best_rank": best_rank,
                "reciprocal_rank": 0.0 if best_rank is None else 1.0 / best_rank,
            }
            session_scores.append(score_record)
            session_record = {
                **score_record,
                "run_id": run_id,
                "difficulty_bucket": sample.get("difficulty_bucket"),
                "turn_count": completed_turns,
                "user_profile": sample["user_profile"],
                "intent_card": intent_card,
                "behavior": behavior,
                "target_parent_asin": target,
                "target_product": products[target],
                "disclosed_constraints": sorted(disclosed),
                "errors": session_errors,
            }
            session_artifacts.append(session_record)
            _jsonl_write(session_file, session_record)
            agent.release_session(session_id)
            elapsed = time.perf_counter() - started
            print(
                f"[{sample_index}/{len(samples)}] {sample_id} hit={score_record['hit']} "
                f"turn={hit_turn} elapsed={elapsed:.1f}s",
                file=sys.stderr,
                flush=True,
            )

    summary = _score(session_scores, usage)
    summary["run_id"] = run_id
    summary["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    summary["artifact_files"] = {
        "config": "run_config.json",
        "sessions": "sessions.jsonl",
        "turns": "turns.jsonl",
        "node_traces": "node_traces.jsonl",
        "report": "report.md",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        _markdown_report(summary, config, session_artifacts, turns_by_sample),
        encoding="utf-8",
    )
    print(json.dumps({**summary, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
