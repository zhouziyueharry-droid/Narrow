from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _portable_path(path: Path, project_root: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), project_root.resolve())).as_posix()
    except ValueError:
        return f"external/{path.name}"


def _summary(sessions: list[dict[str, Any]], usage: dict[str, int]) -> dict[str, Any]:
    from evaluator.local_evaluator import metric_summary

    score_rows = [
        {
            "hit": row["hit"],
            "first_hit_turn": row["first_hit_turn"],
            "best_rank": row["best_rank"],
            "reciprocal_rank": row["reciprocal_rank"],
        }
        for row in sessions
    ]
    overall = metric_summary(score_rows)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    technical_score = (
        0.50 * overall["hit_rate_at_10"]
        + 0.30 * overall["mrr"]
        + 0.20 * efficiency
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session, score in zip(sessions, score_rows):
        grouped[str(session["scenario_type"])].append(score)
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


def _report(summary: dict[str, Any], config: dict[str, Any]) -> str:
    usage = summary["reported_token_usage"]
    lines = [
        "# Parallel Traced Evaluation Report",
        "",
        f"Run: `{config['run_id']}`  ",
        f"Model: `{config['model']}`  ",
        f"Workers: `{config['workers']}`  ",
        f"Samples: `{summary['sample_count']}`",
        "",
        "## Score",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Hit Rate@10 | {summary['hit_rate_at_10']:.6f} |",
        f"| MRR | {summary['mrr']:.6f} |",
        f"| MTTC | {summary['mttc']:.6f} |",
        f"| Efficiency | {summary['efficiency']:.6f} |",
        f"| Technical Score | {summary['recommended_technical_score']:.6f} |",
        f"| Prompt tokens | {usage['prompt_tokens']} |",
        f"| Completion tokens | {usage['completion_tokens']} |",
        f"| Total tokens | {usage['total_tokens']} |",
        "",
        "## Scenario breakdown",
        "",
        "| Scenario | Samples | Hit Rate | MRR | MTTC |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, metrics in summary["scenario_metrics"].items():
        lines.append(
            f"| {name} | {metrics['sample_count']} | "
            f"{metrics['hit_rate_at_10']:.6f} | {metrics['mrr']:.6f} | "
            f"{metrics['mttc']:.6f} |"
        )
    lines.extend([
        "",
        "Complete aggregate data is stored in `sessions.jsonl`, `turns.jsonl`,",
        "and `node_traces.jsonl`. Per-worker raw outputs and logs are under `shards/`.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run traced evaluation in isolated parallel shards and aggregate results"
    )
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output-root", default="evaluation_runs/parallel_traced")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--candidate-limit", type=int, default=20)
    parser.add_argument(
        "--llm",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable Agent DeepSeek calls. Disabled by default to avoid accidental API use.",
    )
    args = parser.parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    load_dotenv(project_root / ".env")
    if args.llm and not os.getenv("DEEPSEEK_API_KEY", "").strip():
        raise SystemExit("DEEPSEEK_API_KEY is empty; cannot run --llm")

    dataset_path = (project_root / args.dataset).resolve()
    catalog_path = (project_root / args.catalog).resolve()
    samples = _load_jsonl(dataset_path)
    worker_count = min(args.workers, max(len(samples), 1))
    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%z")
    output_root = (project_root / args.output_root).resolve()
    output_dir = output_root / run_id
    shards_dir = output_dir / "shards"
    shards_dir.mkdir(parents=True, exist_ok=False)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "LATEST.txt").write_text(run_id + "\n", encoding="utf-8")

    shards: list[list[dict[str, Any]]] = [[] for _ in range(worker_count)]
    for index, sample in enumerate(samples):
        shards[index % worker_count].append(sample)

    env = os.environ.copy()
    if args.llm:
        env["DEEPSEEK_MODEL"] = args.model
    env["SHOPPING_AGENT_ENABLE_LLM"] = "true" if args.llm else "false"
    processes: list[tuple[int, subprocess.Popen[str], Any, Any, Path]] = []
    started = time.perf_counter()
    for shard_index, shard_samples in enumerate(shards):
        shard_dir = shards_dir / f"shard_{shard_index:02d}"
        shard_dir.mkdir()
        shard_dataset = shard_dir / "dataset.jsonl"
        _write_jsonl(shard_dataset, shard_samples)
        raw_root = shard_dir / "run"
        stdout_handle = (shard_dir / "stdout.log").open("w", encoding="utf-8")
        stderr_handle = (shard_dir / "stderr.log").open("w", encoding="utf-8")
        command = [
            sys.executable,
            str(project_root / "scripts" / "evaluate_with_traces.py"),
            "--llm" if args.llm else "--no-llm",
            "--catalog",
            str(catalog_path),
            "--dataset",
            str(shard_dataset),
            "--output-root",
            str(raw_root),
            "--candidate-limit",
            str(args.candidate_limit),
        ]
        process = subprocess.Popen(
            command,
            cwd=project_root,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
        processes.append((shard_index, process, stdout_handle, stderr_handle, raw_root))
        print(
            f"started shard {shard_index + 1}/{worker_count}: "
            f"samples={len(shard_samples)} pid={process.pid}",
            flush=True,
        )

    pending = {item[0] for item in processes}
    failures: list[str] = []
    while pending:
        for shard_index, process, stdout_handle, stderr_handle, _ in processes:
            if shard_index not in pending:
                continue
            return_code = process.poll()
            if return_code is None:
                continue
            stdout_handle.close()
            stderr_handle.close()
            pending.remove(shard_index)
            print(
                f"finished shard {shard_index + 1}/{worker_count}: exit={return_code} "
                f"remaining={len(pending)}",
                flush=True,
            )
            if return_code != 0:
                failures.append(f"shard_{shard_index:02d}: exit {return_code}")
        if pending:
            time.sleep(2)

    if failures:
        raise SystemExit("; ".join(failures))

    aggregate_sessions: list[dict[str, Any]] = []
    aggregate_turns: list[dict[str, Any]] = []
    aggregate_nodes: list[dict[str, Any]] = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    shard_runs: list[dict[str, Any]] = []
    for shard_index, _, _, _, raw_root in processes:
        run_ref = Path((raw_root / "LATEST.txt").read_text(encoding="utf-8").strip())
        run_path = run_ref if run_ref.is_absolute() else raw_root / run_ref
        shard_summary = json.loads((run_path / "summary.json").read_text(encoding="utf-8"))
        for key in usage:
            usage[key] += int(shard_summary["reported_token_usage"].get(key, 0))
        for filename, target in (
            ("sessions.jsonl", aggregate_sessions),
            ("turns.jsonl", aggregate_turns),
            ("node_traces.jsonl", aggregate_nodes),
        ):
            for row in _load_jsonl(run_path / filename):
                row["aggregate_run_id"] = run_id
                row["shard_index"] = shard_index
                target.append(row)
        shard_runs.append({
            "shard_index": shard_index,
            "run_path": run_path.relative_to(output_dir).as_posix(),
            "summary": shard_summary,
        })

    aggregate_sessions.sort(key=lambda row: str(row["sample_id"]))
    aggregate_turns.sort(key=lambda row: (str(row["sample_id"]), int(row["turn"])))
    aggregate_nodes.sort(
        key=lambda row: (
            str(row["sample_id"]),
            int(row["turn"]),
            int(row["stage_index"]),
        )
    )
    _write_jsonl(output_dir / "sessions.jsonl", aggregate_sessions)
    _write_jsonl(output_dir / "turns.jsonl", aggregate_turns)
    _write_jsonl(output_dir / "node_traces.jsonl", aggregate_nodes)

    summary = _summary(aggregate_sessions, usage)
    summary.update({
        "run_id": run_id,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "workers": worker_count,
        "model": args.model if args.llm else "local_fallback",
        "shard_runs": shard_runs,
    })
    config = {
        "run_id": run_id,
        "llm_enabled": bool(args.llm),
        "provider": "deepseek" if args.llm else "local_fallback",
        "model": args.model if args.llm else "local_fallback",
        "workers": worker_count,
        "catalog": _portable_path(catalog_path, project_root),
        "dataset": _portable_path(dataset_path, project_root),
        "sample_count": len(samples),
        "candidate_limit_per_node": args.candidate_limit,
        "started_at": datetime.now().astimezone().isoformat(),
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "report.md").write_text(_report(summary, config), encoding="utf-8")
    print(json.dumps({**summary, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
