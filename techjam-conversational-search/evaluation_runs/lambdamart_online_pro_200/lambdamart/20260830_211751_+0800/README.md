# LambdaMART + DeepSeek Pro: official 200, 2026-08-30

Completed run: **194/200 (97%) Hit@10**, MRR 0.511349, MTTC 2.295, TechnicalScore 0.812505.

- `trace.json`: portable summary for the existing trace visualizer.
- `sessions.jsonl`, `turns.jsonl`: all 200 sessions and 453 turns, including errors.
- `node_traces.jsonl.gz`, `llm_calls.jsonl.gz`, `rank_calls.jsonl.gz`: complete aggregate raw logs, losslessly compressed. No candidate snapshots or LLM messages were trimmed.
- `summary.json`, `run_config.json`, `trace_audit.json`, `report.md`: metrics, configuration and audit.
- `shards/*/run/*/run_config.json`: original per-worker provenance, including fingerprints. Duplicate shard trace files are intentionally omitted.
- `artifact_manifest.json`: SHA256 and sizes for published files and decompressed originals. Original machine paths in logs are provenance, not portable checkout paths.

Only the completed LambdaMART Pro run is published. Cancelled Flash and duplicate baseline runs, local secrets, caches and training data are excluded. Historical baseline figures are references, not a fresh controlled A/B.

## Read the full logs

Run from this directory with Python (standard library only). Existing local originals are left unchanged:

```python
import gzip
import shutil
from pathlib import Path
for archive in Path('.').glob('*.jsonl.gz'):
    target = archive.with_suffix('')
    if target.exists():
        continue
    with gzip.open(archive, 'rb') as source, target.open('wb') as output:
        shutil.copyfileobj(source, output)
```

The audit script expects decompressed JSONL files and never calls LLM APIs. It now uses `models/lambdamart_synthetic_2000` directly and checks its model hash against this run's recorded configuration; `--model-dir` can select another matching bundle. The same-data linear control weights are retained inside the model bundle for online instrumentation. No old evaluation directory or summary is required. Running the audit rewrites `report.md` and `trace_audit.json`, so use a copy of this archive to preserve the published manifest hashes. This is setup documentation, not an instruction to rerun the paid evaluation.

To inspect the run, load `trace.json` in the existing trace visualizer, or copy it to `trace-visualizer/public/trace-lambdamart-pro-20260830-211751.json` and open `/?data=trace-lambdamart-pro-20260830-211751.json`.
