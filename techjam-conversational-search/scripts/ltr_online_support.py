"""Opt-in experiment instrumentation. Never imported by the production graph."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid

import numpy as np

from shopping_agent.ranking.lambdamart import FEATURE_NAMES, LambdaMARTReranker, feature_matrix
from shopping_agent.ranking.precise import PreciseReranker


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class OnlineAudit:
    """One sequential agent per process; graph worker threads share its turn context."""
    def __init__(self, directory, model_dir, mode):
        self.directory = Path(directory)
        self.model_dir = Path(model_dir)
        self.mode = mode
        self.context = {}
        self.lock = threading.Lock()
        self.llm_file = (self.directory/"llm_calls.jsonl").open("w", encoding="utf-8")
        self.rank_file = (self.directory/"rank_calls.jsonl").open("w", encoding="utf-8")
        self.tree = LambdaMARTReranker(self.model_dir)
        self.precise = PreciseReranker()
        self.precise.idf = self.tree.idf
        self.linear_weights_path = self.model_dir/"same_data_linear_weights.json"
        if not self.linear_weights_path.exists():
            self.linear_weights_path = self.model_dir.parent/"same_data_linear_weights.json"
        weights = json.loads(self.linear_weights_path.read_text(encoding="utf-8"))
        self.linear = PreciseReranker(weights=weights)
        self.linear.idf = self.tree.idf
        self.inner = {"precise": self.precise, "linear_same_data": self.linear, "lambdamart": self.tree}[mode]
        self._original_create = None

    def config(self):
        return {"mode": self.mode, "model_dir": str(self.model_dir.resolve()),
                "model_sha256": sha256(self.model_dir/"model.txt"),
                "metadata_sha256": sha256(self.model_dir/"metadata.json"),
                "idf_sha256": sha256(self.model_dir/"idf.json"),
                "linear_weights_sha256": sha256(self.linear_weights_path),
                "feature_names": list(FEATURE_NAMES), "candidate_capture": "full",
                "llm_capture": "SDK request and response; authentication excluded",
                "sdk_internal_retry_detail": "SDK-internal HTTP retries are not separate events",
                "training_mode": "offline pretrained; unchanged during online evaluation"}

    def set_context(self, sample_id, turn):
        self.context = {"sample_id": str(sample_id), "turn": int(turn)}

    def _write(self, handle, record):
        data = json.dumps(record, ensure_ascii=False, allow_nan=False)
        # The request whitelist excludes credentials. Also redact accidental echoes.
        secret = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if secret:
            data = data.replace(secret, "[REDACTED]")
        with self.lock:
            handle.write(data+"\n")
            handle.flush()

    def install_llm_capture(self):
        from openai.resources.chat.completions import Completions
        self._original_create = Completions.create
        original = self._original_create
        audit = self

        def create(resource, *args, **kwargs):
            ctx = dict(audit.context)
            call_id = uuid.uuid4().hex
            allowed = ("model", "messages", "temperature", "max_tokens", "response_format", "stream", "extra_body")
            request = {k: kwargs[k] for k in allowed if k in kwargs}
            messages = request.get("messages", [])
            purpose = "dialogue_decision" if any("JSON dialogue decision" in str(m.get("content", "")) for m in messages) else "state_patch"
            base = {**ctx, "call_id": call_id, "purpose": purpose}
            audit._write(audit.llm_file, {**base, "event": "started",
                "started_at": datetime.now(timezone.utc).isoformat(), "request": request})
            started = time.perf_counter()
            try:
                response = original(resource, *args, **kwargs)
            except Exception as exc:
                audit._write(audit.llm_file, {**base, "event": "error",
                    "latency_ms": (time.perf_counter()-started)*1000,
                    "error_type": type(exc).__name__, "error": str(exc),
                    "status_code": getattr(exc, "status_code", None)})
                raise
            audit._write(audit.llm_file, {**base, "event": "completed",
                "latency_ms": (time.perf_counter()-started)*1000,
                "response": response.model_dump(mode="json"),
                "request_id": getattr(response, "_request_id", None)})
            return response
        Completions.create = create

    def rank(self, candidates, **kwargs):
        ctx = dict(self.context)
        started = time.perf_counter()
        ranked = self.inner.rank(candidates, **kwargs)
        rank_ms = (time.perf_counter()-started)*1000
        X, _ = feature_matrix(candidates, idf=self.tree.idf, **kwargs)
        scores = {}
        if len(X):
            for name, weights in (("precise", self.precise.weights), ("linear_same_data", self.linear.weights)):
                scores[name] = (X @ np.array([weights[k] for k in FEATURE_NAMES])).tolist()
            scores["lambdamart"] = self.tree.model.predict(X, num_threads=1).tolist()
        else:
            scores = {name: [] for name in ("precise", "linear_same_data", "lambdamart")}
        self._write(self.rank_file, {**ctx, "ranker": self.mode, "rank_latency_ms": rank_ms,
            "query": kwargs["query"], "category": kwargs["category"],
            "constraints": [c.model_dump(mode="json") for c in kwargs["constraints"]],
            "profile": kwargs.get("profile"), "previously_recommended": sorted(kwargs.get("previously_recommended") or []),
            "feature_names": list(FEATURE_NAMES), "features": X.tolist(),
            "candidate_ids": [c["parent_asin"] for c in candidates],
            "lexical_ranks": [int(c.get("lexical_rank") or 999999) for c in candidates],
            "counterfactual_scores": scores,
            "ranked_ids": [c["parent_asin"] for c in ranked],
            "ranked_scores": [c["reranker_score"] for c in ranked]})
        return ranked

    def close(self):
        if self._original_create is not None:
            from openai.resources.chat.completions import Completions
            Completions.create = self._original_create
        self.llm_file.close()
        self.rank_file.close()
