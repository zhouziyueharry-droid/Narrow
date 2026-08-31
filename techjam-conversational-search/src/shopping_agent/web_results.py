"""Translate final's existing evaluation artifacts for the imported Vue UI."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluator.trace_export import STAGES, diagnosis, iter_rows, snapshot_stage


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def product(row: dict) -> dict:
    return {"parent_asin": row.get("parent_asin", ""), "title": row.get("title", ""),
            "brand": (row.get("details") or {}).get("Brand") or row.get("store"),
            "price": row.get("price"), "rating": row.get("average_rating"),
            "rating_number": row.get("rating_number"),
            "categories": row.get("categories") or [], "features": row.get("features") or []}


def result_payload(run: Path, job: dict, products: dict) -> dict:
    native = job["mode"] == "native"
    summary = read_json(run/("summary.json" if native else "result.json"), {})
    raw = list(iter_rows(run/"sessions.jsonl"))
    grouped = defaultdict(list)
    if native:
        for turn in iter_rows(run/"turns.jsonl"):
            grouped[turn["sample_id"]].append(turn)
    sessions = []
    for row in raw:
        sid = row["sample_id"]
        target = row.get("target_parent_asin") if native else (row.get("goal_snapshot") or {}).get("target_product_id")
        conversation = []
        for turn in grouped[sid] if native else row.get("conversation", []):
            if native:
                response = turn.get("agent_response") or {}
                conversation.append({"turn": turn["turn"], "user": turn["user_message"],
                    "assistant": response.get("message", ""), "ask_attribute": response.get("ask_attribute"),
                    "recommendations": turn.get("recommended_parent_asins", []),
                    "target_rank": turn.get("target_rank"), "latency_ms": turn.get("latency_ms"),
                    "usage": response.get("usage", {}), "intent": turn.get("intent_state", {}),
                    "error": turn.get("error")})
            else:
                state = {}
                for node in turn.get("agent_layer_trace", []):
                    state.update(node.get("updates", {}))
                conversation.append({k: v for k, v in turn.items() if k not in {"agent_layer_trace"}} | {
                    "latency_ms": turn.get("agent_latency_ms"), "usage": turn.get("reported_token_usage", {}),
                    "intent": {k: state[k] for k in ("semantic_query", "active_constraints", "intent_summary") if k in state}})
        sessions.append({"id": sid, "sample_id": sid, "scenario": row.get("scenario_type", "realistic"),
            "hit": bool(row.get("hit")), "success": bool(row.get("hit")),
            "first_hit_turn": row.get("first_hit_turn"), "best_rank": row.get("best_rank"),
            "turn_count": row.get("turn_count", row.get("turns", len(conversation))),
            "target_parent_asin": target, "target": product(row["target_product"]) if row.get("target_product") else products.get(target),
            "goal": row.get("goal_snapshot"), "persona": row.get("persona"), "acceptance": row.get("acceptance"),
            "errors": row.get("errors", row.get("agent_errors", [])), "conversation": conversation})
    return {"mode": job["mode"], "metrics": {k: v for k, v in summary.items() if k != "sessions"},
            "sessions": sessions, "partial": job["status"] != "completed",
            "completed_sessions": len(sessions), "total_sessions": job["config"]["count"]}


def simulator_trace(run: Path, job: dict, products: dict) -> dict:
    """Use saved snapshots only; truncated pools retain the existing unknown state."""
    output = []
    for row in iter_rows(run/"sessions.jsonl"):
        conversation = row.get("conversation", [])
        target = (row.get("goal_snapshot") or {}).get("target_product_id") or row.get("accepted_product_id")
        if not target:
            recommendations = conversation[-1].get("recommendations", []) if conversation else []
            target = recommendations[0] if recommendations else ""
        turns = []
        for turn in conversation:
            state = {}
            for node in turn.get("agent_layer_trace", []):
                state.update(node.get("updates", {}))
            stages = [snapshot_stage(name, label, state.get(key), target) for name, label, key in STAGES]
            recs = turn.get("recommendations", [])
            stages.append(snapshot_stage("response", "最终 Top 10", {
                "count": len(recs), "top": [{"parent_asin": asin} for asin in recs]}, target))
            # final's simulator does not record per-turn official override gates.
            # Do not infer a scored hit from an earlier recommendation.
            code, reason = diagnosis(stages, True)
            if job["mode"] == "simulator-techjam":
                code, reason = "unknown", "模拟器未记录逐轮评测门控；节点排名仅表示保存的候选快照"
            turns.append({"turn": turn["turn"], "userMessage": turn.get("user", ""),
                "agentMessage": turn.get("assistant", ""), "recommendedAsins": recs,
                "semanticQuery": state.get("semantic_query", ""), "constraints": state.get("active_constraints", []),
                "evaluationActive": True, "relaxed": bool(state.get("constraints_relaxed")),
                "latencyMs": turn.get("agent_latency_ms", 0), "diagnosis": code, "reason": reason, "stages": stages})
        selected = products.get(target, {})
        output.append({"sampleId": row["sample_id"], "scenario": row.get("scenario_type", "realistic"),
            "hit": bool(row["hit"]), "firstHitTurn": row.get("first_hit_turn"), "bestRank": row.get("best_rank"),
            "diagnosis": "hit" if row["hit"] else "unknown", "diagnosisReason": "依据模拟器会话结果；排名只取自保存的快照",
            "target": {"parentAsin": target, "title": selected.get("title", ""),
                "category": " / ".join(selected.get("categories", [])), "price": selected.get("price"), "rating": selected.get("rating")},
            "turns": turns})
    metrics = read_json(run/"result.json", {}).get("evaluation", {})
    return {"schema": "shopping-agent.trace", "schemaVersion": 1,
        "diagnosticMode": "agent" if job["mode"] == "simulator-realistic" else "target",
        "run": {"id": job["id"], "model": job["config"]["model"], "workers": 1,
            "sampleCount": len(output), "hitRate": metrics.get("hit_rate_at_10", metrics.get("success_rate", 0)),
            "mrr": metrics.get("mrr", 0), "technicalScore": metrics.get("recommended_technical_score", 0),
            "diagnosisCounts": dict(Counter(s["diagnosis"] for s in output))}, "sessions": output}
