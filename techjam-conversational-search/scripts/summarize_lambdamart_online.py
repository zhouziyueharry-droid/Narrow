"""Audit the existing traced evaluator outputs; never call APIs or train models."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent/"scripts")]
from evaluator.trace_export import iter_rows
from validate_smoke_traces import REQUIRED_AGENT_NODES


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def audit(run, expected_ids, expected_model):
    config = json.loads((run/"run_config.json").read_text(encoding="utf-8"))
    sessions = list(iter_rows(run/"sessions.jsonl"))
    turns = list(iter_rows(run/"turns.jsonl"))
    keys = {(t["sample_id"], t["turn"]) for t in turns}
    assert len(keys) == len(turns)
    assert len(sessions) == len(expected_ids)
    assert {s["sample_id"] for s in sessions} == expected_ids
    assert config["model"] == expected_model and config["llm_enabled"]
    assert config["candidate_limit_per_node"] == 0
    by_session = defaultdict(list)
    for t in turns:
        by_session[t["sample_id"]].append(t["turn"])
    for s in sessions:
        assert sorted(by_session[s["sample_id"]]) == list(range(1,s["turn_count"]+1))
    observed = defaultdict(set)
    snapshots = nodes = 0
    for row in iter_rows(run/"node_traces.jsonl"):
        key = row["sample_id"], row["turn"]
        assert key in keys
        observed[key].update(row["nodes"])
        nodes += 1
        for name, value in row["updates"].items():
            if name.endswith("_candidates") and isinstance(value, dict):
                assert value["count"] == len(value["top"]), "Truncated candidate snapshot"
                snapshots += 1
    turn_errors = [t for t in turns if t.get("error")]
    success_keys = {(t["sample_id"],t["turn"]) for t in turns if not t.get("error")}
    assert all(REQUIRED_AGENT_NODES <= observed[k] for k in success_keys), "Missing graph node trace"
    rank_keys = set()
    rank_ms = []
    maximum_candidates = 0
    for row in iter_rows(run/"rank_calls.jsonl"):
        key = row["sample_id"], row["turn"]
        assert key in keys and key not in rank_keys
        rank_keys.add(key)
        n = len(row["candidate_ids"])
        maximum_candidates = max(maximum_candidates,n)
        assert n == len(row["features"]) == len(row["ranked_ids"]) == len(row["ranked_scores"])
        assert len(set(row["candidate_ids"])) == n
        assert set(row["candidate_ids"]) == set(row["ranked_ids"])
        assert all(len(x)==len(row["feature_names"])==13 for x in row["features"])
        assert all(len(v)==n for v in row["counterfactual_scores"].values())
        scores = row["counterfactual_scores"][row["ranker"]]
        indexed = dict(zip(row["candidate_ids"],scores))
        np.testing.assert_allclose(row["ranked_scores"],[indexed[k] for k in row["ranked_ids"]],rtol=1e-10,atol=1e-10)
        assert row["ranked_scores"] == sorted(row["ranked_scores"],reverse=True)
        rank_ms.append(row["rank_latency_ms"])
    assert success_keys <= rank_keys, "Missing ranking input/feature log"
    started, ended = {}, {}
    usage = Counter()
    purposes = defaultdict(set)
    response_models = Counter()
    sdk_errors = []
    for row in iter_rows(run/"llm_calls.jsonl"):
        key = row["sample_id"], row["turn"]
        assert key in keys
        call_id = row["call_id"]
        if row["event"] == "started":
            assert call_id not in started
            started[call_id] = row
            assert row["request"]["model"] == expected_model
            assert not ({"api_key","authorization","extra_headers"} & set(row["request"]))
        else:
            assert call_id in started and call_id not in ended
            ended[call_id] = row
            if row["event"] == "completed":
                resp = row["response"]
                response_models[resp.get("model")] += 1
                assert resp.get("model") == expected_model
                u = resp.get("usage") or {}
                for name in ("prompt_tokens","completion_tokens","total_tokens"):
                    usage[name] += int(u.get(name) or 0)
                purposes[key].add(row["purpose"])
            else:
                sdk_errors.append({"sample_id":key[0],"turn":key[1],"error_type":row.get("error_type")})
    assert started.keys() == ended.keys(), "Unfinished SDK call logs"
    assert usage["total_tokens"] > 0
    assert all({"state_patch","dialogue_decision"} <= purposes[k] for k in success_keys)
    summary = json.loads((run/"summary.json").read_text(encoding="utf-8"))
    report = {"status":"passed", "sessions":len(sessions),"turns":len(turns),
              "node_records":nodes,"full_candidate_snapshots":snapshots,
              "ranking_records":len(rank_keys),"maximum_candidates_per_rank":maximum_candidates,
              "sdk_calls":len(started),"sdk_errors":sdk_errors,"response_models":dict(response_models),
              "raw_sdk_usage":dict(usage),"reported_agent_usage":summary["reported_token_usage"],
              "turn_errors":[{"sample_id":t["sample_id"],"turn":t["turn"],"error":t["error"]} for t in turn_errors],
              "rank_latency_ms":{"median":statistics.median(rank_ms),"p95":float(np.quantile(rank_ms,.95))},
              "note":"Full original candidate snapshots and scores are local JSONL; SDK-internal HTTP retries are not separate events."}
    dump(run/"trace_audit.json",report)
    return summary, sessions, turns, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--model",default="deepseek-v4-pro")
    parser.add_argument("--model-dir", type=Path, default=ROOT/"models/lambdamart_synthetic_2000")
    args = parser.parse_args()
    config = json.loads((args.run/"run_config.json").read_text(encoding="utf-8"))
    assert config["reranker"]["mode"] == "lambdamart"
    original = config["reranker"]["model_sha256"]
    assert hashlib.sha256((args.model_dir/"model.txt").read_bytes()).hexdigest() == original
    expected = {s["sample_id"] for s in iter_rows(ROOT/"data/public_set.jsonl")}
    summary, sessions, turns, report = audit(args.run,expected,args.model)
    report["frozen_model_sha256"] = original
    dump(args.run/"trace_audit.json",report)
    path = args.run/"report.md"
    text = path.read_text(encoding="utf-8").split("\n## Detailed trace audit")[0]
    text += "\n## Detailed trace audit\n\n"
    text += json.dumps(report,ensure_ascii=False,indent=2)
    text += "\n\nFull local records: sessions.jsonl, turns.jsonl, node_traces.jsonl, llm_calls.jsonl, rank_calls.jsonl. "
    text += "trace.json is the existing viewer summary; full LLM requests and candidate features remain in JSONL. "
    text += "The LLM interprets intent and chooses dialogue actions online; simulated users remain local. "
    text += "The offline-trained tree was not retrained or tuned on this test. "
    text += "Only LambdaMART Pro was requested; cancelled duplicate baseline and Flash runs are excluded.\n"
    path.write_text(text,encoding="utf-8")
    print(json.dumps({"score":{k:v for k,v in summary.items() if k!="shard_runs"},"trace_audit":report},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
