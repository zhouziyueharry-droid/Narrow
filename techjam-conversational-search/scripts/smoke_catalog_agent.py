"""Run one deterministic offline evaluator session against an explicit catalog."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ["SHOPPING_AGENT_ENABLE_LLM"] = "false"
os.environ["SHOPPING_DENSE_BACKEND"] = "local"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from evaluator.local_evaluator import evaluate, load_jsonl
from shopping_agent.application.service import ShoppingAgent
from shopping_agent.retrieval.lexical import CatalogIndex


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    samples = load_jsonl(args.sessions)
    sample = [samples[args.index]]
    started = time.perf_counter()
    catalog = CatalogIndex(args.catalog)
    identifiers = set(catalog.products)
    categories = {identifier: product.get("categories", []) for identifier, product in catalog.products.items()}
    products = catalog.products
    evaluator_index_seconds = time.perf_counter() - started
    agent = ShoppingAgent(args.catalog, catalog_index=catalog)
    agent_initialization_seconds = time.perf_counter() - started - evaluator_index_seconds
    session_started = time.perf_counter()
    result = evaluate(agent, sample, identifiers, categories, products)
    agent.release_session(sample[0]["sample_id"])
    row = result["sessions"][0]
    usage = row.get("usage") or row.get("model_usage") or {}
    if usage.get("prompt_tokens", 0) or usage.get("completion_tokens", 0):
        raise RuntimeError("unexpected LLM token usage")
    print(json.dumps({
        "status": "ok", "sample_id": row["sample_id"], "catalog_rows": len(identifiers),
        "startup": {"evaluator_index_seconds": round(evaluator_index_seconds, 6),
                    "agent_initialization_seconds": round(agent_initialization_seconds, 6)},
        "session": {"wall_seconds": round(time.perf_counter() - session_started, 6),
                    "hit": row["hit"], "first_hit_turn": row["first_hit_turn"],
                    "mttc_contribution": row["first_hit_turn"] if row["first_hit_turn"] is not None else 11},
        "model_usage": {"llm_calls": 0, "tokens": 0, "cost": 0},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
