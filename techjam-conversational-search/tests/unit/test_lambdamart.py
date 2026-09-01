import json

import numpy as np
import pytest

from shopping_agent.ranking.lambdamart import (
    FEATURE_NAMES, SCHEMA_VERSION, LambdaMARTReranker, feature_matrix,
)
from shopping_agent.domain.schemas import Constraint


def test_feature_order_and_repeat_history_are_preserved():
    candidates = [{"parent_asin": "A", "title": "black running shoes", "rrf_score": .04},
                  {"parent_asin": "B", "title": "red coat", "rrf_score": .02}]
    matrix, _ = feature_matrix(candidates, query="black running shoes", category="shoes",
                              constraints=[Constraint(field="color", value="black")],
                              previously_recommended={"A"}, idf={"black": 2, "running": 2, "shoes": 2})
    assert matrix.shape == (2, len(FEATURE_NAMES))
    assert matrix[:, FEATURE_NAMES.index("rrf_raw")] == pytest.approx([.04, .02])
    assert matrix[:, FEATURE_NAMES.index("novelty_penalty")].tolist() == [1, 0]
    assert matrix[0, FEATURE_NAMES.index("term_coverage")] > matrix[1, FEATURE_NAMES.index("term_coverage")]


def test_constraint_features_distinguish_satisfied_violated_and_unknown():
    candidates = [
        {"parent_asin": "A", "title": "black cotton running shoes", "categories": ["Shoes"],
         "price": 80, "rrf_score": .04},
        {"parent_asin": "B", "title": "red leather running shoes", "categories": ["Shoes"],
         "price": 130, "rrf_score": .03},
    ]
    constraints = [
        Constraint(field="color", value="black", strength="hard", confidence=.8),
        Constraint(field="material", value="cotton", confidence=1),
        Constraint(field="budget", operator="lte", value=100, strength="hard", confidence=1),
        Constraint(field="size", value="size 12", confidence=.5),
    ]
    matrix, features = feature_matrix(
        candidates, query="black cotton", category="Shoes", constraints=constraints,
        idf={"black": 2, "cotton": 2},
    )
    good, bad = features
    assert good.title_phrase_match == 1
    assert good.category_hierarchy_match == 1
    assert good.constraint_satisfaction == pytest.approx(2.8)
    assert good.hard_constraint_satisfied == pytest.approx(1.8)
    assert good.budget_satisfied == 1
    assert good.color_match == pytest.approx(.8)
    assert good.material_match == 1
    assert good.constraint_unknown == pytest.approx(.5)
    assert bad.hard_constraint_violations == pytest.approx(1.8)
    assert bad.budget_penalty == pytest.approx(.3)
    assert matrix.shape[1] == len(FEATURE_NAMES)


def test_hard_negative_mining_keeps_target_and_baseline_top20_deterministically():
    pytest.importorskip("lightgbm")
    from scripts.experiment_lambdamart import mine_hard_negatives
    X = np.zeros((30, len(FEATURE_NAMES)))
    X[:, FEATURE_NAMES.index("rrf_raw")] = np.arange(30)
    y = np.zeros(30, dtype=np.int32)
    y[5] = 1
    group = {"X": X, "y": y, "sample_id": "s1", "turn": 2,
             "candidate_ids": [str(i) for i in range(30)],
             "lexical_ranks": list(range(1, 31))}
    first = mine_hard_negatives(group, hard_negative_k=20, random_negative_k=3, seed=42)
    second = mine_hard_negatives(group, hard_negative_k=20, random_negative_k=3, seed=42)
    assert first["candidate_ids"] == second["candidate_ids"]
    assert "5" in first["candidate_ids"]
    assert set(map(str, range(10, 30))) <= set(first["candidate_ids"])
    assert first["mining"] == {"source_rows": 30, "kept_rows": 24,
                                "hard_negatives": 20, "random_negatives": 3}


def test_schema_mismatch_fails_before_model_load(tmp_path):
    (tmp_path / "metadata.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, "feature_names": list(reversed(FEATURE_NAMES))}
    ), encoding="utf-8")
    with pytest.raises(ValueError, match="feature order"):
        LambdaMARTReranker(tmp_path)


def test_real_model_roundtrip_and_entire_candidate_pool(tmp_path):
    lgb = pytest.importorskip("lightgbm")
    candidates = [{"parent_asin": str(i), "title": "shoe", "rrf_score": i / 200}
                  for i in range(150)]
    matrix, _ = feature_matrix(candidates, query="shoe", category="", constraints=[], idf={"shoe": 1})
    labels = np.asarray([int(i >= 140) for i in range(150)])
    model = lgb.LGBMRanker(n_estimators=10, num_leaves=4, min_child_samples=2, verbosity=-1, n_jobs=1)
    model.fit(matrix, labels, group=[150], feature_name=list(FEATURE_NAMES))
    model.booster_.save_model(str(tmp_path / "model.txt"))
    (tmp_path / "metadata.json").write_text(json.dumps(
        {"schema_version": SCHEMA_VERSION, "feature_names": list(FEATURE_NAMES)}
    ), encoding="utf-8")
    (tmp_path / "idf.json").write_text('{"shoe": 1}', encoding="utf-8")
    ranker = LambdaMARTReranker(tmp_path)
    ranked = ranker.rank(candidates, query="shoe", category="", constraints=[])
    assert len(ranked) == 150
    assert {p["parent_asin"] for p in ranked} == {p["parent_asin"] for p in candidates}
    assert int(ranked[0]["parent_asin"]) >= 140
    by_id = {p["parent_asin"]: p["reranker_score"] for p in ranked}
    assert [by_id[str(i)] for i in range(150)] == pytest.approx(model.booster_.predict(matrix, num_threads=1).tolist())
    assert all("reranker_score" not in p for p in candidates)
    assert ranker.rank([], query="", category="", constraints=[]) == []


def test_experiment_split_holds_out_official_targets_and_keeps_scenario_groups(monkeypatch):
    pytest.importorskip("lightgbm")
    for name, value in {"SHOPPING_AGENT_ENABLE_LLM": "false", "SHOPPING_DENSE_BACKEND": "local",
                        "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"}.items():
        monkeypatch.setenv(name, value)
    from scripts.experiment_lambdamart import choose_splits
    def sample(sid, target):
        return {"sample_id": sid, "ground_truth": {"parent_asin": target}}
    synthetic = [sample("a1", "A"), sample("a2", "A"), sample("b1", "B"),
                 sample("c1", "C"), sample("p1", "PUBLIC")]
    public = [sample("test1", "PUBLIC"), sample("test2", "OTHER")]
    train, valid, test = choose_splits(synthetic, public, .34, 42)
    assert test == public
    assert len(train)+len(valid) == 4
    train_targets = {s["ground_truth"]["parent_asin"] for s in train}
    valid_targets = {s["ground_truth"]["parent_asin"] for s in valid}
    assert train_targets.isdisjoint(valid_targets)
    assert "PUBLIC" not in train_targets | valid_targets
    assert (sum(s["ground_truth"]["parent_asin"] == "A" for s in train),
            sum(s["ground_truth"]["parent_asin"] == "A" for s in valid)) in {(2, 0), (0, 2)}
    assert choose_splits(synthetic, public, .34, 42) == (train, valid, test)
