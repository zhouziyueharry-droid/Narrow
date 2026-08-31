"""Reproducible offline LTR experiment; opt-in dependency injection only."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
# Explicit isolation: neither copied .env nor host defaults may turn on paid calls.
os.environ["SHOPPING_AGENT_ENABLE_LLM"] = "false"
os.environ["SHOPPING_DENSE_BACKEND"] = "local"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import lightgbm as lgb
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from evaluator.local_evaluator import evaluate, load_jsonl, materialize_hidden_fields, metric_summary
from shopping_agent.application.service import ShoppingAgent
from shopping_agent.ranking.lambdamart import FEATURE_NAMES, SCHEMA_VERSION, LambdaMARTReranker, feature_matrix
from shopping_agent.ranking.precise import DEFAULT_WEIGHTS, PreciseReranker
from shopping_agent.retrieval.lexical import CatalogIndex


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_splits(synthetic, public, validation_fraction, seed):
    """Hold out official targets, then split all remaining scenarios by target."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must lie between zero and one")
    for name, samples in (("synthetic", synthetic), ("public", public)):
        ids = [sample["sample_id"] for sample in samples]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate sample IDs in {name}")
    public_targets = {s["ground_truth"]["parent_asin"] for s in public}
    eligible = [s for s in synthetic if s["ground_truth"]["parent_asin"] not in public_targets]
    targets = sorted({s["ground_truth"]["parent_asin"] for s in eligible})
    if len(targets) < 2:
        raise ValueError("Need at least two eligible target products")
    random.Random(seed).shuffle(targets)
    n_valid = min(len(targets)-1, max(1, round(len(targets)*validation_fraction)))
    validation_targets = set(targets[:n_valid])
    train = [s for s in eligible if s["ground_truth"]["parent_asin"] not in validation_targets]
    valid = [s for s in eligible if s["ground_truth"]["parent_asin"] in validation_targets]
    test = list(public)
    sets = [{s["ground_truth"]["parent_asin"] for s in group} for group in (train, valid, test)]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert len(train)+len(valid) == len(eligible)
    return train, valid, test


class Recorder:
    def __init__(self, inner, idf):
        self.inner, self.idf = inner, idf
        self.groups = []
        self.sample = None
        self.turn = 0
        self.active_from = 1
        self.capture = True
        self.capture_raw = False
        self.rank_ms = []

    def rank(self, candidates, **kwargs):
        start = time.perf_counter()
        ranked = self.inner.rank(candidates, **kwargs)
        self.rank_ms.append((time.perf_counter() - start) * 1000)
        if self.capture and self.turn >= self.active_from and candidates:
            X, _ = feature_matrix(candidates, idf=self.idf, **kwargs)
            target = self.sample["ground_truth"]["parent_asin"]
            ids = [str(c["parent_asin"]) for c in candidates]
            y = np.array([int(asin == target) for asin in ids], dtype=np.int32)
            group = {
                "X": X, "y": y, "sample_id": self.sample["sample_id"],
                "target": target, "turn": self.turn, "candidate_ids": ids,
                "lexical_ranks": [int(c.get("lexical_rank") or 999999) for c in candidates],
                "query": kwargs["query"], "category": kwargs["category"],
                "constraints": [c.model_dump(mode="json") for c in kwargs["constraints"]],
                "profile": kwargs.get("profile"),
                "previously_recommended": sorted(kwargs.get("previously_recommended") or set()),
            }
            if self.capture_raw:
                group["_candidates"] = [dict(candidate) for candidate in candidates]
                group["_feature_kwargs"] = dict(kwargs)
            self.groups.append(group)
        return ranked


class AuditedAgent:
    def __init__(self, real, recorder):
        self.real, self.recorder = real, recorder
        self.errors = []
        self.sid = None

    def reset(self, sid, profile):
        self.sid = sid
        self.real.reset(sid, profile)

    def respond(self, sid, message, turn, top_k):
        self.recorder.turn = turn
        try:
            result = self.real.respond(sid, message, turn, top_k)
            usage = result.get("usage", {})
            if usage.get("prompt_tokens", 0) or usage.get("completion_tokens", 0):
                raise RuntimeError("Unexpected LLM token usage in offline experiment")
            return result
        except Exception as exc:
            self.errors.append(repr(exc))
            raise


def run_sessions(proxy, recorder, samples, products, stage):
    catalog_ids = set(products)
    categories = {key: value.get("categories", []) for key, value in products.items()}
    sessions = []
    started = time.perf_counter()
    for i, sample in enumerate(samples, 1):
        recorder.sample = sample
        _, behavior = materialize_hidden_fields(sample, products)
        recorder.active_from = int(behavior.get("override", {}).get("turn", 3)) if sample["scenario_type"] == "intent_override" else 1
        try:
            result = evaluate(proxy, [sample], catalog_ids, categories, products)
            if proxy.errors:
                raise RuntimeError(f"Evaluator caught application errors: {proxy.errors}")
            sessions += result["sessions"]
        finally:
            if proxy.sid:
                proxy.real.release_session(proxy.sid)
        if i % 20 == 0 or i == len(samples):
            print(f"{stage}: {i}/{len(samples)}, {time.perf_counter()-started:.1f}s", flush=True)
    overall = metric_summary(sessions)
    efficiency = max(0, min(1, (11-overall["mttc"])/10))
    return {**overall, "efficiency": efficiency,
            "recommended_technical_score": .5*overall["hit_rate_at_10"]+.3*overall["mrr"]+.2*efficiency,
            "wall_seconds": time.perf_counter()-started, "sessions": sessions}


def pack(groups):
    # All-negative queries have no ranking pairs; never inject missing targets.
    active = [g for g in groups if int(g["y"].sum()) > 0 and len(g["y"]) > 1]
    if not active:
        raise ValueError("No usable ranking groups")
    counts = Counter(g["sample_id"] for g in active)
    X = np.concatenate([g["X"] for g in active])
    y = np.concatenate([g["y"] for g in active])
    sizes = np.array([len(g["y"]) for g in active], dtype=np.int32)
    weights = np.concatenate([np.full(len(g["y"]), 1/counts[g["sample_id"]]) for g in active])
    assert int(sizes.sum()) == len(X) == len(y)
    return X, y, sizes, weights, active


def summarize_groups(groups):
    return {"groups": len(groups), "rows": sum(len(g["y"]) for g in groups),
            "groups_with_target": sum(bool(g["y"].sum()) for g in groups),
            "sessions_with_groups": len({g["sample_id"] for g in groups})}


def save_groups(directory, name, groups):
    X = np.concatenate([g["X"] for g in groups])
    y = np.concatenate([g["y"] for g in groups])
    sizes = np.array([len(g["y"]) for g in groups])
    np.savez_compressed(directory / f"{name}.npz", X=X, y=y, group=sizes)
    dump(directory / f"{name}_groups.json", [
        {k:v for k,v in g.items() if k not in {"X", "y"} and not k.startswith("_")}
        for g in groups
    ])


def frozen_metrics(groups, score_fn, *, idf=None):
    outcomes = []
    for group in groups:
        matrix = group["X"]
        if idf is not None:
            matrix, _ = feature_matrix(
                group["_candidates"], idf=idf, **group["_feature_kwargs"]
            )
        scores = score_fn(matrix)
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), group["lexical_ranks"][i]))
        rank = next((j for j,i in enumerate(order, 1) if group["y"][i]), None)
        outcomes.append({"sample_id": group["sample_id"], "turn": group["turn"], "rank": rank,
                         "hit_at_10": bool(rank and rank <= 10),
                         "reciprocal_rank": 1/rank if rank else 0,
                         "ndcg_at_10": 1/math.log2(rank+1) if rank and rank <= 10 else 0})
    # Every session gets equal weight, despite differing dialogue lengths.
    by_session = defaultdict(list)
    for outcome in outcomes:
        by_session[outcome["sample_id"]].append(outcome)
    return {key: statistics.mean(statistics.mean(x[key] for x in rows) for rows in by_session.values())
            for key in ("hit_at_10", "reciprocal_rank", "ndcg_at_10")} | {"turn_results": outcomes}


def paired_bootstrap(baseline, candidate, seed):
    a = {r["sample_id"]: r for r in baseline["sessions"]}
    b = {r["sample_id"]: r for r in candidate["sessions"]}
    assert a.keys() == b.keys()
    def score(r):
        eff = (11 - (r["first_hit_turn"] if r["first_hit_turn"] is not None else 11))/10
        return .5*int(r["hit"])+.3*r["reciprocal_rank"]+.2*eff
    diffs = np.array([score(b[sid])-score(a[sid]) for sid in sorted(a)])
    rng = np.random.default_rng(seed)
    estimates = rng.choice(diffs, size=(5000, len(diffs)), replace=True).mean(axis=1)
    return {"difference": float(diffs.mean()), "ci95": np.quantile(estimates, [.025, .975]).tolist(),
            "candidate_only_hits": sum(b[s]["hit"] and not a[s]["hit"] for s in a),
            "baseline_only_hits": sum(a[s]["hit"] and not b[s]["hit"] for s in a)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", type=Path, default=ROOT.parent/"synthetic_scenarios_2000.jsonl")
    parser.add_argument("--catalog", type=Path, default=ROOT/"data/catalog.jsonl",
                        help="Training/validation catalog used to build the frozen model IDF")
    parser.add_argument("--test-catalog", type=Path,
                        help="Official test catalog loaded only after the model is frozen")
    parser.add_argument("--comparison-model-dir", type=Path,
                        default=ROOT/"models/lambdamart_synthetic_2000",
                        help="Optional previous LambdaMART bundle for public-200 A/B")
    parser.add_argument("--limit-train", type=int, default=0)
    parser.add_argument("--limit-validation", type=int, default=0)
    parser.add_argument("--limit-test", type=int, default=0)
    parser.add_argument("--validation-fraction", type=float, default=.2)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog_path = args.catalog.resolve()
    test_catalog_path = (args.test_catalog or args.catalog).resolve()
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    synthetic = load_jsonl(args.synthetic)
    public = load_jsonl(ROOT/"data/public_set.jsonl")
    train, valid, test = choose_splits(synthetic, public, args.validation_fraction, args.seed)
    if args.limit_train:
        train = train[:args.limit_train]
    if args.limit_validation:
        valid = valid[:args.limit_validation]
    if args.limit_test:
        test = test[:args.limit_test]
    excluded_ids = sorted(set(s["sample_id"] for s in synthetic) -
                          set(s["sample_id"] for s in train+valid))
    split_summary = {name: {"sessions": len(samples),
                           "unique_targets": len({s["ground_truth"]["parent_asin"] for s in samples}),
                           "scenarios": dict(Counter(s["scenario_type"] for s in samples))}
                     for name, samples in (("train", train), ("validation", valid), ("test", test))}
    split_summary["excluded_synthetic_sessions"] = len(excluded_ids)
    dump(out/"split_manifest.json", {"seed": args.seed, "train": train, "validation": valid, "test": test,
         "excluded_synthetic_ids": excluded_ids, "summary": split_summary,
         "policy": "All scenarios retained after excluding official target ASINs; synthetic split grouped by target; entire official test set untouched."})
    print("Split: "+json.dumps(split_summary), flush=True)
    config = {"offline": True, "llm_calls": 0, "llm_tokens": 0, "llm_cost": 0,
              "agent_llm": "not_used", "user_verbalizer_llm": "not_used",
              "runtime": {"python": sys.version, "platform": platform.platform(),
                          "lightgbm": lgb.__version__, "numpy": np.__version__,
                          "scikit_learn": sklearn.__version__, "dense_backend": "local"},
              "feature_names": list(FEATURE_NAMES),
              "synthetic_path": str(args.synthetic.resolve()), "synthetic_sha256": digest(args.synthetic),
              "public_sha256": digest(ROOT/"data/public_set.jsonl"),
              "training_catalog_path": str(catalog_path),
              "training_catalog_sha256": digest(catalog_path),
              "test_catalog_path": str(test_catalog_path),
              "feature_source_sha256": digest(ROOT/"src/shopping_agent/ranking/precise_features.py"),
              "script_sha256": digest(Path(__file__)), "selection_seed": args.seed,
              "selection_metric": "validation NDCG@1 first, NDCG@10 second; no official-test model selection",
              "label_policy": "Known simulator target=1, others=0; weak target labels, NOT graded semantic relevance.",
              "baseline_collection_policy": "Current PreciseReranker trajectories, all candidate rows, no pre-override target supervision."}
    dump(out/"config.json", config)
    print("Building training catalog and frozen corpus IDF...", flush=True)
    catalog = CatalogIndex(catalog_path)
    missing = {s["ground_truth"]["parent_asin"] for s in train+valid} - set(catalog.products)
    if missing:
        raise ValueError(f"Missing training/validation catalog targets: {sorted(missing)}")
    public_targets = {s["ground_truth"]["parent_asin"] for s in public}
    leaked_public_targets = public_targets & set(catalog.products)
    if catalog_path != test_catalog_path and leaked_public_targets:
        raise ValueError(
            f"Training catalog contains {len(leaked_public_targets)} official test targets"
        )
    precise = PreciseReranker(catalog_products=catalog.products)
    recorder = Recorder(precise, precise.idf)
    agent = ShoppingAgent(catalog_path, reranker=recorder, catalog_index=catalog)
    proxy = AuditedAgent(agent, recorder)
    collection = run_sessions(proxy, recorder, train, catalog.products, "collect training")
    dump(out/"training_collection_sessions.json", collection)
    training = recorder.groups
    save_groups(out, "training", training)
    recorder.groups = []
    collection = run_sessions(proxy, recorder, valid, catalog.products, "collect validation")
    dump(out/"validation_collection_sessions.json", collection)
    validation = recorder.groups
    recorder.groups = []
    save_groups(out, "validation", validation)
    X, y, group, sample_weight, train_active = pack(training)
    VX, vy, vgroup, _, valid_active = pack(validation)
    data_summary = {"training": summarize_groups(training), "validation": summarize_groups(validation)}
    dump(out/"data_summary.json", data_summary)
    print("Training LambdaRank on grouped candidate lists: "+json.dumps(data_summary), flush=True)
    model = lgb.LGBMRanker(
        objective="lambdarank", metric="ndcg", n_estimators=300, learning_rate=.05,
        num_leaves=15, max_depth=5, min_child_samples=40, reg_lambda=5.,
        random_state=args.seed, n_jobs=4, verbosity=-1,
        deterministic=True, force_col_wise=True, lambdarank_truncation_level=13,
    )
    model.fit(X, y, group=group, sample_weight=sample_weight,
              eval_set=[(VX, vy)], eval_group=[vgroup], eval_at=[1, 10],
              feature_name=list(FEATURE_NAMES),
              callbacks=[lgb.early_stopping(30, first_metric_only=True, verbose=False)])
    model_dir = out/"model"
    model_dir.mkdir()
    model.booster_.save_model(str(model_dir/"model.txt"))
    dump(model_dir/"idf.json", precise.idf)
    metadata = {**config, "schema_version": SCHEMA_VERSION,
                "best_iteration": int(model.best_iteration_), "parameters": model.get_params(),
                "train_sessions": len(train), "validation_sessions": len(valid),
                "data_summary": data_summary}
    dump(model_dir/"metadata.json", metadata)
    tree = LambdaMARTReranker(model_dir, num_threads=1)
    np.testing.assert_allclose(tree.model.predict(VX[:500], num_threads=1),
                               model.booster_.predict(VX[:500], num_threads=1), rtol=1e-12, atol=1e-12)
    # Same-data linear control distinguishes architecture effects from training data size.
    print("Training same-data linear control...", flush=True)
    with threadpool_limits(limits=4):
        linear = LogisticRegression(C=100, class_weight="balanced", max_iter=3000)
        linear.fit(X, y, sample_weight=sample_weight)
    linear_weights = dict(zip(FEATURE_NAMES, linear.coef_[0].tolist()))
    dump(out/"same_data_linear_weights.json", linear_weights)
    linear_ranker = PreciseReranker(weights=linear_weights)
    linear_ranker.idf = precise.idf
    weights = np.array([DEFAULT_WEIGHTS[n] for n in FEATURE_NAMES])
    score_fns = {"precise": lambda x: x@weights,
                 "linear_same_data": lambda x: x@linear.coef_[0],
                 "lambdamart": lambda x: tree.model.predict(x, num_threads=1)}
    validation_frozen = {name:frozen_metrics(validation, fn) for name,fn in score_fns.items()}
    dump(out/"validation_frozen.json", validation_frozen)
    importance = sorted(zip(FEATURE_NAMES, model.booster_.feature_importance(importance_type="gain").tolist()),
                        key=lambda pair: -pair[1])
    dump(out/"feature_importance.json", importance)
    # Model fixed before the official catalog or any official test trajectory is loaded.
    model_hash = digest(model_dir/"model.txt")
    del proxy, agent, catalog, X, y, group, sample_weight, VX, vy, vgroup
    gc.collect()

    print("Model frozen; loading isolated official test catalog...", flush=True)
    test_catalog = CatalogIndex(test_catalog_path)
    missing_test = {s["ground_truth"]["parent_asin"] for s in test} - set(test_catalog.products)
    if missing_test:
        raise ValueError(f"Missing official test catalog targets: {sorted(missing_test)}")
    test_precise = PreciseReranker(catalog_products=test_catalog.products)
    test_recorder = Recorder(test_precise, test_precise.idf)
    test_recorder.capture_raw = True
    test_agent = ShoppingAgent(test_catalog_path, reranker=test_recorder, catalog_index=test_catalog)
    test_proxy = AuditedAgent(test_agent, test_recorder)
    test_rankers = [("precise", test_precise)]
    old_tree = None
    comparison_dir = args.comparison_model_dir.resolve() if args.comparison_model_dir else None
    if comparison_dir and (comparison_dir/"model.txt").exists():
        old_tree = LambdaMARTReranker(comparison_dir, num_threads=1)
        test_rankers.append(("old_lambdamart", old_tree))
    test_rankers.extend([("linear_same_data", linear_ranker), ("lambdamart", tree)])

    results, latency = {}, {}
    for name, ranker in test_rankers:
        test_recorder.inner = ranker
        test_recorder.idf = ranker.idf
        test_recorder.capture = name == "precise"
        test_recorder.groups, test_recorder.rank_ms = [], []
        results[name] = run_sessions(test_proxy, test_recorder, test, test_catalog.products, "test "+name)
        latency[name] = {"rank_calls": len(test_recorder.rank_ms),
                         "median_ms": statistics.median(test_recorder.rank_ms),
                         "p95_ms": float(np.quantile(test_recorder.rank_ms, .95))}
        dump(out/(name+"_sessions.json"), results[name])
        if name == "precise":
            test_frozen = test_recorder.groups
    assert digest(model_dir/"model.txt") == model_hash
    save_groups(out, "test_frozen", test_frozen)
    frozen = {
        "precise": frozen_metrics(test_frozen, score_fns["precise"], idf=test_precise.idf),
        "linear_same_data": frozen_metrics(test_frozen, score_fns["linear_same_data"], idf=precise.idf),
        "lambdamart": frozen_metrics(test_frozen, score_fns["lambdamart"], idf=tree.idf),
    }
    if old_tree is not None:
        frozen["old_lambdamart"] = frozen_metrics(
            test_frozen,
            lambda x: old_tree.model.predict(x, num_threads=1),
            idf=old_tree.idf,
        )
    dump(out/"test_frozen_metrics.json", frozen)
    summary = {name:{k:v for k,v in result.items() if k != "sessions"} for name,result in results.items()}
    summary.update({"split": split_summary, "latency": latency, "best_iteration": model.best_iteration_, "data": data_summary,
                    "training_catalog_sha256": digest(catalog_path),
                    "test_catalog_sha256": digest(test_catalog_path),
                    "official_targets_in_training_catalog": len(leaked_public_targets),
                    "paired_lambdamart_vs_precise": paired_bootstrap(results["precise"], results["lambdamart"], args.seed),
                    "paired_lambdamart_vs_same_data_linear": paired_bootstrap(results["linear_same_data"], results["lambdamart"], args.seed),
                    "default_changed": False, "model_sha256": model_hash})
    if "old_lambdamart" in results:
        old_result, new_result = results["old_lambdamart"], results["lambdamart"]
        summary["paired_lambdamart_vs_old_lambdamart"] = paired_bootstrap(old_result, new_result, args.seed)
        summary["acceptance_vs_old_lambdamart"] = {
            "mrr_delta": new_result["mrr"] - old_result["mrr"],
            "mrr_delta_at_least_0_02": new_result["mrr"] - old_result["mrr"] >= .02,
            "hit_at_10_delta": new_result["hit_rate_at_10"] - old_result["hit_rate_at_10"],
            "hit_at_10_not_lower_by_more_than_0_005": new_result["hit_rate_at_10"] - old_result["hit_rate_at_10"] >= -.005,
            "technical_score_delta": new_result["recommended_technical_score"] - old_result["recommended_technical_score"],
            "technical_score_improved": new_result["recommended_technical_score"] > old_result["recommended_technical_score"],
        }
        acceptance = summary["acceptance_vs_old_lambdamart"]
        acceptance["recommended_merge"] = all((
            acceptance["mrr_delta_at_least_0_02"],
            acceptance["hit_at_10_not_lower_by_more_than_0_005"],
            acceptance["technical_score_improved"],
        ))
    dump(out/"summary.json", summary)
    lines = ["# New100K / 2K LambdaMART 训练与官方200条隔离测试", "",
             "独立分支实验，默认仍为 PreciseReranker。Agent 和 user verbalizer 均未调用 LLM；API calls/tokens/cost 均为 0。",
             f"训练 {len(train)} 条合成会话，验证 {len(valid)} 条合成会话，测试 {len(test)} 条正式会话。",
             f"训练 catalog SHA256: `{summary['training_catalog_sha256']}`；官方测试 catalog SHA256: `{summary['test_catalog_sha256']}`。",
             f"训练商品库中的官方200目标数：{summary['official_targets_in_training_catalog']}。训练期不加载官方测试商品库；模型冻结后才加载官方50K。",
             "训练/验证目标商品互斥，并排除全部官方样本目标；同一会话不跨集合。同一请求轮次的候选列表是一个训练 group。",
             "复用原 13 个特征，IDF 随模型冻结，重排全部候选。只用模拟目标的二元弱标签，未假定其他候选都语义不相关。",
             "训练样本由原 PreciseReranker 驱动完整离线对话产生；不在候选池的目标不会被偷偷补入；改意图前轮次不标作目标正例。",
             "同时比较当前 Precise、旧 LambdaMART、同数据线性模型和新 LambdaMART。",
             "参数固定一组，轮数只由合成验证集的 NDCG@1/NDCG@10 早停确定，优先 Rank 1；官方200没有用于选模型。", "",
             "| 精排 | Hit@10 | MRR | MTTC | TechnicalScore | 精排中位延迟(ms) |",
             "|---|---:|---:|---:|---:|---:|"]
    for name in results:
        r=results[name]
        lines.append(f"| {name} | {r['hit_rate_at_10']:.3f} | {r['mrr']:.4f} | {r['mttc']:.2f} | {r['recommended_technical_score']:.4f} | {latency[name]['median_ms']:.2f} |")
    if "acceptance_vs_old_lambdamart" in summary:
        lines += ["", "## 验收结论", "",
                  "```json", json.dumps(summary["acceptance_vs_old_lambdamart"], ensure_ascii=False, indent=2), "```"]
    lines += ["", "## 相同候选、相同对话状态上的比较", "",
              "取原精排的测试轨迹，固定每轮候选和特征，只替换打分。按会话等权平均每轮指标；不是完整会话命中率。",
              "| 精排 | 冻结轮次 Hit@10 | 冻结轮次 RR | NDCG@10 |", "|---|---:|---:|---:|"]
    for name,r in frozen.items():
        lines.append(f"| {name} | {r['hit_at_10']:.4f} | {r['reciprocal_rank']:.4f} | {r['ndcg_at_10']:.4f} |")
    lines += ["", "## 限制", "",
              "- 官方200条全部测试，保留原场景比例；这是本地模拟器评测，不等于线上真实用户效果或私有榜单成绩。",
              "- 全部离线，不能和之前的在线 DeepSeek 分数直接对比。",
              "- 新树模型和同数据线性模型的训练 catalog/IDF 均排除了全部官方200目标；旧模型仅作为历史对照。",
              "- 缺少分级相关性标签和真实点击/购买反馈；算法替换不会解决标签歧义或上游误解析。",
              "- 置信区间按会话配对自助抽样；模型未因此自动切换为默认。", "",
              "配对比较："+json.dumps(summary["paired_lambdamart_vs_precise"], ensure_ascii=False),
              "", "重要特征（gain）："+json.dumps(importance[:6], ensure_ascii=False),
              "", "模型在 model/；训练分组与候选ID在 *_groups.json；特征和标签在 *.npz；完整结果在 *_sessions.json。"]
    (out/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    english = ["# New100K / 2K LambdaMART Training and Isolated Official-200 Test", "",
               "This branch-only experiment keeps PreciseReranker as the default. Neither the Agent nor the user verbalizer used an LLM; API calls, tokens, and cost are all zero.",
               f"Training sessions: {len(train)}; validation sessions: {len(valid)}; official test sessions: {len(test)}.",
               f"Training catalog SHA256: `{summary['training_catalog_sha256']}`.",
               f"Official test catalog SHA256: `{summary['test_catalog_sha256']}`.",
               f"Official targets present in the training catalog: {summary['official_targets_in_training_catalog']}.",
               "The official 50K catalog is loaded only after the model and training IDF are frozen. Early stopping evaluates NDCG@1 first and NDCG@10 second.", "",
               "| Ranker | Hit@10 | MRR | MTTC | Technical Score | Median rerank latency (ms) |",
               "|---|---:|---:|---:|---:|---:|"]
    for name in results:
        result = results[name]
        english.append(f"| {name} | {result['hit_rate_at_10']:.3f} | {result['mrr']:.4f} | {result['mttc']:.2f} | {result['recommended_technical_score']:.4f} | {latency[name]['median_ms']:.2f} |")
    if "acceptance_vs_old_lambdamart" in summary:
        english += ["", "## Acceptance decision", "", "```json",
                    json.dumps(summary["acceptance_vs_old_lambdamart"], ensure_ascii=False, indent=2), "```"]
    english += ["", "The official 200 remains a local public benchmark, not evidence of private-leaderboard or real-user performance.",
                "The experiment JSON files use the LambdaMART experiment schema rather than the unified simulator-report schema; no unified-schema validator pass is claimed."]
    (out/"report_en.md").write_text("\n".join(english)+"\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
