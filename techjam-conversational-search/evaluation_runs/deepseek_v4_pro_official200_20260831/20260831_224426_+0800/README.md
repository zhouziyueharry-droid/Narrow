# DeepSeek v4 Pro official-200 evaluation

This directory contains the completed TechJam-style official development-set
run using the integrated LambdaMART reranker and `deepseek-v4-pro` for the
agent-side LLM. The dataset is the official 200-session `public_set.jsonl`;
synthetic training and validation sessions were not used as test sessions.

## Result

| Metric | Value |
|---|---:|
| Sessions | 200 |
| Hit@10 | 0.990000 |
| MRR | 0.515437 |
| MTTC | 2.295000 |
| Technical Score | 0.823731 |
| Wall time | 2691.493 s |
| Total reported tokens | 1,338,126 |

The complete human-readable report is in `report.md`; machine-readable
session and turn summaries are in `summary.json`, `sessions.jsonl`, and
`turns.jsonl`.

## Complete traces

The following files preserve the full run trace. The three large JSONL files
are gzip-compressed only for repository transport; decompressing them restores
the original JSONL records byte-for-byte. `trace.json` is the aggregate trace
export used by the trace visualizer.

- `node_traces.jsonl.gz` — every candidate/node checkpoint (compressed from
  the 490,885,378-byte local JSONL).
- `llm_calls.jsonl.gz` — every recorded DeepSeek call.
- `rank_calls.jsonl.gz` — every recorded reranker call.
- `trace.json`, `turns.jsonl`, and `sessions.jsonl` — aggregate exports.

`artifact_manifest.json` records SHA-256 hashes for both the local originals
and the uploaded compressed artifacts. The uncompressed working copies stay
local and are intentionally not committed.

## Reproduction metadata

- `run_config.json` records the catalog, dataset, model, LLM flag, reranker,
  and run timestamp.
- `report.md` includes the per-scenario breakdown and representative turns.
- This run used the DeepSeek API on the agent side; the API key is not stored
  in any artifact. The official test set remains separate from synthetic
  training/validation data.

## Schema note

These files are the native output of `scripts/evaluate_with_traces.py`
(`summary.json`, `sessions.jsonl`, `turns.jsonl`, and trace exports). They are
not the separate unified dual-mode simulator result schema used by
`shopping-simulator-evaluation/scripts/validate_report.py`; that validator is
therefore not claimed as passed for this native trace run.
