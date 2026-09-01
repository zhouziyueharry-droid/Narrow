"""Opt-in LambdaMART ranker. The production default remains PreciseReranker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shopping_agent.ranking.precise_features import extract_batch_features

FEATURE_NAMES = (
    "exact_matches", "partial_matches", "category_match", "term_coverage",
    "lexical_signal", "rrf_raw", "dense_raw", "attribute_raw", "profile_match",
    "quality", "contradictions", "budget_penalty", "novelty_penalty",
    "title_phrase_match", "title_term_coverage", "category_hierarchy_match",
    "constraint_satisfaction", "hard_constraint_satisfied",
    "hard_constraint_violations", "constraint_unknown", "budget_satisfied",
    "budget_unknown", "material_match", "color_match", "size_match", "brand_match",
)
SCHEMA_VERSION = 2


def feature_matrix(candidates, *, query, category, constraints, profile=None,
                   previously_recommended=None, idf=None):
    import numpy as np
    features = extract_batch_features(
        candidates, query=query, category=category, constraints=constraints,
        profile=profile, previously_recommended=previously_recommended, idf=idf,
    )
    matrix = np.asarray([[getattr(f, name) for name in FEATURE_NAMES] for f in features],
                        dtype=np.float64).reshape((-1, len(FEATURE_NAMES)))
    if not np.isfinite(matrix).all():
        raise ValueError("Ranking features contain non-finite values")
    return matrix, features


class LambdaMARTReranker:
    """Load a versioned model bundle; score ALL supplied candidates.

    Bundle IDF is frozen at training time. Scores are ranking margins, not
    probabilities. No target identifiers, labels, or hidden intent cards enter
    this class. Importing the module does not require LightGBM.
    """

    def __init__(self, model_dir: str | Path, *, num_threads: int = 1) -> None:
        if num_threads < 1:
            raise ValueError("num_threads must be positive")
        self.model_dir = Path(model_dir)
        metadata = json.loads((self.model_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported ranking feature schema version")
        if metadata.get("feature_names") != list(FEATURE_NAMES):
            raise ValueError("Model feature order does not match runtime")
        self.idf = json.loads((self.model_dir / "idf.json").read_text(encoding="utf-8"))
        if not isinstance(self.idf, dict) or not self.idf:
            raise ValueError("Model bundle must include the training IDF table")
        try:
            import lightgbm as lgb
        except ImportError as exc:
            raise RuntimeError("Install experiment dependencies: uv sync --extra ltr --group dev") from exc
        self.model = lgb.Booster(model_file=str(self.model_dir / "model.txt"))
        if self.model.feature_name() != list(FEATURE_NAMES):
            raise ValueError("Booster feature order does not match runtime")
        self.num_threads = num_threads
        self.metadata = metadata

    def rank(self, candidates, *, query, category, constraints, profile=None,
             previously_recommended=None) -> list[dict[str, Any]]:
        if not candidates:
            return []
        import numpy as np
        matrix, features = feature_matrix(
            candidates, query=query, category=category, constraints=constraints,
            profile=profile, previously_recommended=previously_recommended, idf=self.idf,
        )
        scores = np.asarray(self.model.predict(matrix, num_threads=self.num_threads))
        if scores.shape != (len(candidates),) or not np.isfinite(scores).all():
            raise ValueError("Invalid LambdaMART prediction shape or values")
        ranked = [
            {**candidate, "reranker_score": float(score),
             "reranker_explanation": ["lambdamart", *feature.explanations]}
            for candidate, score, feature in zip(candidates, scores, features)
        ]
        return sorted(ranked, key=lambda p: (
            -p["reranker_score"], int(p.get("lexical_rank") or 999999),
        ))
