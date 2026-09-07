# Realistic Hard DeepSeek Full Evaluation

This directory publishes the reviewable evidence for the 24-session realistic hard evaluation run on 2026-08-29.

## Contents

- `analysis_report_zh.md`: full Chinese analysis and recommendations.
- `analysis_report_en.md`: full English analysis and recommendations.
- `metrics_summary.json`: aggregate evaluation, turn, latency, model-usage, and realistic-mode metrics without the large per-turn session payload.
- `manifest.json`: exact branch, evaluation commit, catalog hash, runtime, and model configuration. It records only whether an API key was configured and never contains the key.
- `validation_hard.json`: hard-mode validation result, scenario/persona coverage, Agent-node coverage, and token totals.
- `checksums.sha256`: hashes for the published files in this directory.

## Headline result

- Mode: realistic need-based evaluation; `official_metric_contract=false`.
- Sessions: 24; successes: 19; success rate: 79.17%.
- Executed turns: 151; mean: 6.29.
- Four pressure variants: six sessions each.
- Blocked premature candidate acceptances: 74; accepted while Agent was still asking: 0.
- Agent model: `deepseek-v4-flash` for semantic understanding.
- User verbalizer model: `deepseek-v4-flash` for natural-language realization.
- Retrieval, filtering, reranking, dialogue scheduling, acceptance, and metric calculation: deterministic non-LLM code.
- Simulator tests: 21 passed; Agent tests: 35 passed; both report validators passed.

## Raw evidence policy

The full `realistic.json` contains approximately 18 MB of per-turn Agent traces and is intentionally kept under the gitignored `integration_runs/` directory instead of being committed to repository history. The bilingual local evidence archive contains the raw JSON, JSONL journals, event stream, logs, reports, manifest, validation output, and checksums.

```text
Local raw JSON:
D:\\projects\\tiktok26\\tiktok_project_4\\integration_runs\\realistic_hard_deepseek_full_20260829\\realistic.json
SHA-256: B1CDB20DE8170B67C5B66D08D003133597291C990EC72FC7B85C3964AA46C203

Local evidence archive:
D:\\projects\\tiktok26\\tiktok_project_4\\integration_runs\\realistic_hard_deepseek_full_20260829_bilingual_model_boundary.zip
SHA-256: C76AB954DF27E4FBFA8AC4C5E87A7160C1F874C920700349B49031F238B61B8F
```

The raw files can be shared out of band when detailed trace reproduction is required.
