"""Fit PreciseReranker's scoring weights from evaluator sessions instead of
hand-guessing them.

Why this exists: PreciseReranker (src/shopping_agent/ranking/precise.py) scores
each candidate as a weighted sum of ~13 explainable features (exact_matches,
term_coverage, rrf_raw, quality, contradictions, ...). Hand-picking those 13
weights by feel plateaus quickly -- see docs/precise_reranker_change_report.md
section 7, where manually tuning one weight up/down stopped changing the
evaluator score at all. Every evaluator session in data/public_set.jsonl
already carries a known target product (ground_truth.parent_asin), which is a
free source of weak supervision: replay the conversation, record every
candidate batch that reaches the reranker, label the one matching the known
target as positive, and fit a classifier. Because PreciseReranker's score is
already `sum(weight_i * feature_i)`, a plain logistic regression's coefficients
plug directly into PreciseReranker(weights=...) -- no change to the ranker
itself, just better numbers.

Usage (from techjam-conversational-search/):

    PYTHONPATH=".:src" python3 scripts/fit_precise_reranker_weights.py \
        --train-slice 100:200 --val-slice 0:100 --C 100 --output fitted_weights.json

This trains on samples[100:200] and validates on the disjoint samples[0:100]
so the reported comparison against FallbackReranker has no data leakage.
--C defaults to 100 (see fit_weights()'s docstring/comment): a grouped 5-fold
CV sweep over the training rows found sklearn's own default (C=1.0) was
noticeably over-regularized for this feature set, and C=100 is what is
currently shipped as PreciseReranker.DEFAULT_WEIGHTS. If you add meaningfully
more training data, re-run a small C sweep rather than assuming 100 is still
optimal -- it was found by search on this specific 100-session slice, not
derived analytically.

Once you're happy with a fit, retrain on the full dataset (--train-slice
0:200, no --val-slice) before shipping it as PreciseReranker's
DEFAULT_WEIGHTS, since more training rows will stabilize the coefficients
further (see the caveat in precise.py's DEFAULT_WEIGHTS docstring about
exact_matches/partial_matches coming out negative even at C=100).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from evaluator.local_evaluator import (  # noqa: E402
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    evaluate,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    normalize_recommendations,
)
from shopping_agent.application.service import ShoppingAgent  # noqa: E402
from shopping_agent.orchestration.graph import build_shopping_graph  # noqa: E402
from shopping_agent.ranking.fallback import FallbackReranker  # noqa: E402
from shopping_agent.ranking.precise import PreciseReranker  # noqa: E402
from shopping_agent.ranking.precise_features import (  # noqa: E402
    build_global_idf,
    extract_batch_features,
)
from shopping_agent.retrieval.lexical import CatalogIndex  # noqa: E402

FEATURE_NAMES = [
    "exact_matches", "partial_matches", "category_match", "term_coverage", "lexical_signal",
    "rrf_raw", "dense_raw", "attribute_raw", "profile_match", "quality", "contradictions",
    "budget_penalty", "novelty_penalty",
]


class _RecordingReranker:
    """Wraps a real ranker so every rank() call's inputs are captured.

    Conversation flow (which follow-up question gets asked, when a session
    stops) still follows the wrapped ranker's real ordering, so this doesn't
    distort the simulated sessions relative to real evaluator runs -- it just
    also logs what the ranker saw on each call.
    """

    def __init__(self, inner):
        self.inner = inner
        self.records: list[dict] = []

    def rank(self, candidates, *, query, category, constraints, profile=None, previously_recommended=None):
        self.records.append(dict(
            candidates=candidates, query=query, category=category, constraints=constraints,
            profile=profile, previously_recommended=previously_recommended,
        ))
        return self.inner.rank(
            candidates, query=query, category=category, constraints=constraints,
            profile=profile, previously_recommended=previously_recommended,
        )


def _parse_slice(spec: str) -> slice:
    start, _, stop = spec.partition(":")
    return slice(int(start) if start else None, int(stop) if stop else None)


def collect_training_rows(
    samples: list[dict],
    catalog_path: str,
    catalog_ids: set[str],
    categories: dict[str, list[str]],
    products: dict[str, dict],
    idf: dict[str, float],
) -> list[tuple[list[float], int]]:
    """Replay each session exactly as evaluator.evaluate() would, but record
    every candidate batch the reranker sees along the way and label each
    candidate by whether it is the session's known target product."""

    recorder = _RecordingReranker(FallbackReranker())
    graph = build_shopping_graph(catalog_path=catalog_path, reranker=recorder)
    agent = ShoppingAgent(graph=graph)
    rows: list[tuple[list[float], int]] = []

    for sample in samples:
        session_id = f"train_{uuid.uuid4().hex}"
        agent.reset(session_id, sample["user_profile"])
        target = str(sample["ground_truth"]["parent_asin"])
        card, behavior = materialize_hidden_fields(sample, products)
        effective = {**sample, "intent_card": card, "behavior": behavior}
        disclosed: set[str] = set()
        boundary_used = False
        override_applied = sample["scenario_type"] != "intent_override"
        user_message = initial_message(effective, coarse_category(categories.get(target, [])), disclosed)

        for turn in range(1, MAX_TURNS + 1):
            before = len(recorder.records)
            try:
                response = agent.respond(session_id, user_message, turn, TOP_K)
            except Exception:
                response = {"message": "", "ask_attribute": None, "recommendations": []}

            for record in recorder.records[before:]:
                features = extract_batch_features(
                    record["candidates"], query=record["query"], category=record["category"],
                    constraints=record["constraints"], profile=record["profile"],
                    previously_recommended=record["previously_recommended"], idf=idf,
                )
                for candidate, feature in zip(record["candidates"], features):
                    label = 1 if str(candidate["parent_asin"]) == target else 0
                    rows.append(([getattr(feature, name) for name in FEATURE_NAMES], label))

            ranked = normalize_recommendations(response.get("recommendations"), catalog_ids)
            if override_applied and target in ranked:
                break
            if turn == MAX_TURNS:
                break
            override = effective.get("behavior", {}).get("override") or {}
            if not override_applied and turn + 1 == int(override.get("turn", 3)):
                override_applied = True
                new_value = str(override.get("new_value", ""))
                if new_value:
                    disclosed.add(new_value)
                user_message = str(override.get("message", "Actually, please ignore my earlier preference."))
            else:
                user_message, boundary_used = customer_reply(
                    effective, response.get("ask_attribute"), disclosed, boundary_used
                )
    return rows


def fit_weights(rows: list[tuple[list[float], int]], C: float = 100.0) -> dict[str, float]:
    import numpy as np
    from sklearn.linear_model import LogisticRegression

    X = np.array([row[0] for row in rows], dtype=float)
    y = np.array([row[1] for row in rows], dtype=int)
    # class_weight="balanced" matters a lot here: positives are a tiny fraction
    # of rows (one true target per candidate batch of dozens to hundreds).
    #
    # C defaults to 100 (much looser than sklearn's default C=1.0), not 1.0.
    # A grouped 5-fold CV sweep over C in [1, 3, 10, 30, 100] showed held-out
    # classification AUC kept climbing as C increased instead of the expected
    # U-shape (0.9245 at C=1.0 -> 0.939 at C=30, still rising at C=100), and
    # C=100 validated on the disjoint [0:100] holdout beat both the official
    # baseline and the earlier C=1.0 fit by a wider, more bootstrap-robust
    # margin. See docs/precise_reranker_change_report.md and the comment
    # above PreciseReranker.DEFAULT_WEIGHTS in ranking/precise.py for the full
    # numbers. Re-run the CV sweep before trusting C=100 blindly on a
    # meaningfully different training slice -- the optimum was found by
    # search on this specific 100-session slice, not derived analytically.
    model = LogisticRegression(max_iter=3000, class_weight="balanced", C=C)
    model.fit(X, y)
    return dict(zip(FEATURE_NAMES, model.coef_[0].tolist()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--train-slice", default="100:200", help="python slice syntax, e.g. 100:200")
    parser.add_argument("--val-slice", default="0:100", help="python slice syntax, or empty to skip validation")
    parser.add_argument("--output", default="fitted_weights.json")
    parser.add_argument("--C", type=float, default=100.0, help="logistic regression inverse regularization strength (see fit_weights() docstring/comment)")
    parser.add_argument(
        "--extra-dataset", default=None,
        help=(
            "Optional path to additional scenarios in the same jsonl shape as --dataset "
            "(e.g. generated by scripts/generate_synthetic_scenarios.py), appended to the "
            "training slice only -- never to validation, to avoid ever validating on "
            "self-generated data. See docs/precise_reranker_change_report.md for why naive "
            "random-target synthetic data made the fit worse, and what filter fixed it."
        ),
    )
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)
    full_catalog = CatalogIndex(args.catalog)
    idf = build_global_idf(full_catalog.products)

    train_samples = samples[_parse_slice(args.train_slice)]
    if args.extra_dataset:
        extra_samples = load_jsonl(args.extra_dataset)
        print(f"adding {len(extra_samples)} extra training scenarios from {args.extra_dataset}", flush=True)
        train_samples = list(train_samples) + extra_samples
    print(f"collecting training rows from {len(train_samples)} sessions...", flush=True)
    rows = collect_training_rows(train_samples, args.catalog, catalog_ids, categories, products, idf)
    print(f"collected {len(rows)} rows, positives={sum(r[1] for r in rows)}", flush=True)

    weights = fit_weights(rows, C=args.C)
    print("fitted weights:", json.dumps(weights, indent=2), flush=True)
    Path(args.output).write_text(json.dumps(weights, indent=2) + "\n", encoding="utf-8")

    if args.val_slice:
        val_samples = samples[_parse_slice(args.val_slice)]
        print(f"\nvalidating on {len(val_samples)} held-out sessions...", flush=True)
        for name, reranker in [
            ("FallbackReranker", FallbackReranker()),
            ("PreciseReranker (fitted)", PreciseReranker(weights=weights, catalog_products=full_catalog.products)),
        ]:
            graph = build_shopping_graph(catalog_path=args.catalog, reranker=reranker)
            agent = ShoppingAgent(graph=graph)
            result = evaluate(agent, val_samples, catalog_ids, categories, products)
            summary = {k: v for k, v in result.items() if k not in ("sessions", "scenario_metrics")}
            print(name, json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
