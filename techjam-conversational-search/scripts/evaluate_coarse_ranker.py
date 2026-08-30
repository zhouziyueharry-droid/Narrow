from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.attributes import AttributeIndex
from shopping_agent.retrieval.coarse import (
    CoarseRanker,
    CoarseRankerConfig,
    CoarseRankRequest,
    RouteWeights,
)
from shopping_agent.retrieval.embedding import SentenceTransformerDenseIndex
from shopping_agent.retrieval.lexical import CatalogIndex
from shopping_agent.retrieval.semantic import LocalDenseIndex


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_cases(path: Path, *, first_turn_only: bool) -> list[dict[str, Any]]:
    records = read_jsonl(path)
    if not first_turn_only:
        return records
    first: dict[str, dict[str, Any]] = {}
    for record in records:
        sample_id = str(record["sample_id"])
        if sample_id not in first or int(record["turn"]) < int(first[sample_id]["turn"]):
            first[sample_id] = record
    return list(first.values())


def retrieval_intent(scenario: str) -> str:
    if scenario == "buying":
        return "buying"
    if scenario in {"browsing", "boundary"}:
        return "browsing"
    return "unknown"


def configurations(base: CoarseRankerConfig) -> dict[str, CoarseRankerConfig]:
    fixed = base.unknown_weights
    return {
        "lexical_only": replace(
            base,
            buying_weights=RouteWeights(1.0, 0.0, 0.0),
            browsing_weights=RouteWeights(1.0, 0.0, 0.0),
            unknown_weights=RouteWeights(1.0, 0.0, 0.0),
            diversity_lambda=1.0,
            category_cap=10_000,
        ),
        "fixed_hybrid": replace(
            base,
            buying_weights=fixed,
            browsing_weights=fixed,
            unknown_weights=fixed,
            diversity_lambda=1.0,
            category_cap=10_000,
        ),
        "dynamic_no_diversity": replace(
            base,
            diversify_browsing=False,
        ),
        "dynamic_with_diversity": replace(base, diversify_browsing=True),
    }


def evaluate(
    ranker: CoarseRanker,
    cases: list[dict[str, Any]],
    *,
    ignore_constraints: bool = False,
) -> dict[str, Any]:
    ranks: list[int | None] = []
    latencies: list[float] = []
    by_scenario: dict[str, list[int | None]] = {}
    for case in cases:
        state = case.get("intent_state") or {}
        constraints = () if ignore_constraints else tuple(
            Constraint.model_validate(item)
            for item in state.get("active_constraints", [])
        )
        request = CoarseRankRequest(
            query=str(state.get("semantic_query") or case.get("user_message") or ""),
            category=str(state.get("category") or ""),
            intent=retrieval_intent(str(case.get("scenario_type") or "")),  # type: ignore[arg-type]
            constraints=constraints,
            limit=100,
        )
        started = time.perf_counter()
        candidates = ranker.rank(request)
        latencies.append((time.perf_counter() - started) * 1000.0)
        ids = [str(item["parent_asin"]) for item in candidates]
        target = str(case["target_parent_asin"])
        rank = ids.index(target) + 1 if target in ids else None
        ranks.append(rank)
        by_scenario.setdefault(str(case.get("scenario_type") or "unknown"), []).append(rank)

    def metrics(values: list[int | None]) -> dict[str, float | int]:
        count = len(values)
        return {
            "count": count,
            "hit_at_10": round(sum(rank is not None and rank <= 10 for rank in values) / count, 6),
            "recall_at_50": round(sum(rank is not None and rank <= 50 for rank in values) / count, 6),
            "recall_at_100": round(sum(rank is not None for rank in values) / count, 6),
            "mrr_at_100": round(statistics.fmean(1.0 / rank if rank else 0.0 for rank in values), 6),
        }

    return {
        **metrics(ranks),
        "latency_ms_mean": round(statistics.fmean(latencies), 3),
        "latency_ms_p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "by_scenario": {name: metrics(values) for name, values in sorted(by_scenario.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate independent coarse-ranking recall")
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog.jsonl"))
    parser.add_argument("--turns", type=Path, required=True)
    parser.add_argument("--backend", choices=("local", "sentence-transformer"), default="local")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--faiss", action="store_true")
    parser.add_argument("--all-turns", action="store_true")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    started = time.perf_counter()
    catalog = CatalogIndex(args.catalog)
    attribute_index = AttributeIndex(catalog)
    if args.backend == "sentence-transformer":
        dense = SentenceTransformerDenseIndex(
            catalog,
            model_name=args.model,
            use_faiss=args.faiss,
        )
    else:
        dense = LocalDenseIndex(catalog)
    startup_seconds = time.perf_counter() - started
    cases = load_cases(args.turns, first_turn_only=not args.all_turns)
    if args.max_cases is not None:
        cases = cases[: max(args.max_cases, 0)]
    base = CoarseRankerConfig()
    results: dict[str, Any] = {
        "backend": args.backend,
        "model": args.model if args.backend == "sentence-transformer" else "hashed-local-fallback",
        "vector_search": "faiss-flat-ip" if args.faiss else "numpy-exact-dot",
        "catalog_count": len(catalog.products),
        "case_count": len(cases),
        "startup_seconds": round(startup_seconds, 3),
        "config": asdict(base),
        "ablations": {},
    }
    for name, config in configurations(base).items():
        print(f"evaluating {name} on {len(cases)} cases...", flush=True)
        ranker = CoarseRanker(catalog, dense, attribute_index, config)
        results["ablations"][name] = evaluate(ranker, cases)
    results["ablations"]["dynamic_without_constraints"] = evaluate(
        CoarseRanker(catalog, dense, attribute_index, base),
        cases,
        ignore_constraints=True,
    )

    payload = json.dumps(results, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
