import numpy as np
import pytest

from scripts.mrr_objective import make_mrr_metric, make_mrr_objective, mrr_lambdas


def test_mrr_lambdas_focus_on_top_ranks_and_respect_query_weights():
    labels = np.array([0] * 10 + [1, 0])
    scores = -np.arange(12, dtype=float)
    grad, hess = mrr_lambdas(labels, scores, None, [12])
    assert grad[10] < 0  # Raise the positive from rank 11.
    assert grad[0] > grad[1] > grad[9] > 0
    assert grad[11] == hess[11] == 0  # A swap between ranks 11/12 has zero RR@10 gain.
    assert grad.sum() == pytest.approx(0)
    assert np.isfinite(grad).all() and np.isfinite(hess).all() and (hess >= 0).all()
    weighted = mrr_lambdas(labels, scores, np.full(12, .25), [12])
    np.testing.assert_allclose(weighted[0], grad * .25)
    np.testing.assert_allclose(weighted[1], hess * .25)
    # A single optimizer step must move the positive above the negative.
    g, _ = mrr_lambdas(np.array([0, 1]), np.zeros(2), None, [2])
    assert np.argmax(-g) == 1
    with pytest.raises(ValueError, match="exactly one"):
        mrr_lambdas(np.array([1, 1]), np.zeros(2), None, [2])


def test_top1_bonus_changes_only_first_place_pair_priority():
    labels = np.array([0, 0, 1, 0])
    scores = -np.arange(4, dtype=float)
    base, base_hess = mrr_lambdas(labels, scores, None, [4])
    identical = make_mrr_objective(0)(labels, scores, None, [4])
    np.testing.assert_array_equal(identical[0], base)
    np.testing.assert_array_equal(identical[1], base_hess)
    bonus, hess = make_mrr_objective(.5)(labels, scores, None, [4])
    assert bonus[0] / bonus[1] > base[0] / base[1]
    assert bonus.sum() == pytest.approx(0)
    assert (hess >= 0).all()
    with pytest.raises(ValueError, match="non-negative"):
        make_mrr_objective(-1)


def test_validation_mrr_counts_missing_targets_and_uses_session_weights_and_runtime_ties():
    groups = [
        {"sample_id": "a", "y": [0, 1], "lexical_ranks": [2, 1]},
        {"sample_id": "a", "y": [0, 0], "lexical_ranks": [1, 2]},
        {"sample_id": "b", "y": [0, 1], "lexical_ranks": [1, 2]},
    ]
    result = dict((name, value) for name, value, _ in make_mrr_metric(groups)(
        np.array([0, 1, 0, 0, 0, 1]), np.array([0, 0, 0, 0, 1, 0])))
    assert result == pytest.approx({"mrr_at_10": .5, "hit_at_10": .75, "top1": .25})
    outside = [{"sample_id": "c", "y": [0] * 10 + [1], "lexical_ranks": list(range(11))}]
    assert make_mrr_metric(outside)(np.array(outside[0]["y"]), -np.arange(11))[0][1] == 0


def test_custom_objective_trains_and_roundtrips_with_lightgbm(tmp_path):
    lgb = pytest.importorskip("lightgbm")
    from shopping_agent.ranking.lambdamart import FEATURE_NAMES
    rng = np.random.default_rng(7)
    features = rng.normal(size=(240, len(FEATURE_NAMES)))
    labels = np.zeros(240)
    for start in range(0, 240, 12):
        labels[start + np.argmax(features[start:start + 12, 0])] = 1
    groups = [{"sample_id": str(i), "y": labels[i*12:(i+1)*12],
               "lexical_ranks": list(range(12))} for i in range(20)]
    model = lgb.LGBMRanker(objective=make_mrr_objective(.5), metric="None", n_estimators=30,
                          num_leaves=4, min_child_samples=5, verbosity=-1, n_jobs=1)
    model.fit(features, labels, group=[12]*20, eval_set=[(features, labels)],
              eval_group=[[12]*20], eval_metric=make_mrr_metric(groups),
              feature_name=list(FEATURE_NAMES))
    predictions = model.booster_.predict(features, num_threads=1)
    assert make_mrr_metric(groups)(labels, predictions)[0][1] > .85
    model.booster_.save_model(str(tmp_path / "model.txt"))
    loaded = lgb.Booster(model_file=str(tmp_path / "model.txt"))
    np.testing.assert_allclose(loaded.predict(features, num_threads=1), predictions)


def test_cached_features_reject_out_of_split_sessions_and_wrong_targets(tmp_path, monkeypatch):
    import json
    for key in ("SHOPPING_AGENT_ENABLE_LLM", "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        monkeypatch.setenv(key, "false")
    monkeypatch.setenv("SHOPPING_DENSE_BACKEND", "local")
    from scripts.experiment_lambdamart import load_groups
    from shopping_agent.ranking.lambdamart import FEATURE_NAMES
    np.savez(tmp_path / "training.npz", X=np.zeros((2, len(FEATURE_NAMES))), y=[1, 0], group=[2])
    path = tmp_path / "training_groups.json"
    item = {"sample_id": "synthetic_a", "target": "A", "candidate_ids": ["A", "B"]}
    path.write_text(json.dumps([item]), encoding="utf-8")
    samples = [{"sample_id": "synthetic_a", "ground_truth": {"parent_asin": "A"}}]
    assert load_groups(tmp_path, "training", samples)[0]["y"].tolist() == [1, 0]
    with pytest.raises(ValueError, match="outside"):
        load_groups(tmp_path, "training", [])
    item["candidate_ids"] = ["B", "A"]
    path.write_text(json.dumps([item]), encoding="utf-8")
    with pytest.raises(ValueError, match="labels"):
        load_groups(tmp_path, "training", samples)
