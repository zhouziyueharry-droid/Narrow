# Stage 1–2 Dynamic Retrieval + DeepSeek Pro Online Evaluation

This is the final online A/B for the stage 1–2 retrieval and conversational
state changes. The run uses all 200 public samples, the same catalog, four
workers, `deepseek-v4-pro`, the local semantic backend and the frozen
LambdaMART model bundle.

## Result versus the archived online baseline

| Metric | Archived LambdaMART Pro | Stage 1–2 Pro | Absolute change |
|---|---:|---:|---:|
| Hit@10 | 0.970000 | **0.985000** | **+0.015000** |
| MRR | 0.511349 | **0.539962** | **+0.028613** |
| MTTC (lower is better) | 2.295000 | **2.060000** | **-0.235000** |
| Efficiency | 0.870500 | **0.894000** | **+0.023500** |
| Technical score | 0.812505 | **0.833289** | **+0.020784** |

Technical score improved by 2.56% relative. This independently confirms the
direction already established by the deterministic offline A/B (0.765944 to
0.832338), while retaining the real model-only understanding and dialogue path.

## Scenario breakdown

| Scenario | Samples | Hit@10 | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 10 | 1.000000 | 0.506111 | 2.100000 |
| browsing | 80 | 0.987500 | 0.516463 | 1.862500 |
| buying | 80 | 1.000000 | 0.569519 | 1.425000 |
| intent override | 30 | 0.933333 | 0.535093 | 4.266667 |

The three misses are `public_0046`, `public_0076` and `public_0144`. None is one
of the archived baseline's six misses (`public_0029`, `public_0066`,
`public_0073`, `public_0096`, `public_0161`, `public_0167`). Because model output
is nondeterministic, this replacement is evidence of aggregate improvement,
not proof that every per-sample difference was caused by retrieval alone.

## Online integrity audit

- 200 sessions and 409 turns were retained; failed turns were not dropped.
- 816 SDK calls completed: 409 state-patch calls and 407 dialogue calls.
- Every completed SDK response reports model `deepseek-v4-pro`.
- Nine turns failed local response validation: two intent outputs and seven
  dialogue outputs. No failed online turn used an offline fallback.
- Agent-reported usage is 1,165,804 tokens (1,044,776 prompt and 121,028
  completion). Raw completed SDK responses report 1,188,993 tokens (1,065,086
  prompt and 123,907 completion); the difference is retained in raw call logs
  for validation-failed turns.
- The run took 703.316 seconds with four workers.
- Authentication headers and API keys are not recorded.

The archived baseline had 453 turns, 904 completed SDK calls, nine invalid
turns and 1,145,176 raw SDK tokens. Stage 1–2 therefore completed conversations
in 44 fewer turns and 88 fewer calls, at the cost of 43,817 additional raw
tokens because the per-call state/facet context is richer.

## Reproduce

```bash
uv sync --extra ltr --extra deepseek --group dev
uv run --env-file .env.example python scripts/evaluate_parallel_with_traces.py \
  --workers 4 \
  --model deepseek-v4-pro \
  --ltr-model-dir models/lambdamart_synthetic_2000 \
  --ltr-ranker lambdamart \
  --candidate-limit 20 \
  --progress-interval 20 \
  --output-root evaluation_runs/stage12_dynamic_online_pro_200
```

The retained successful run is
`evaluation_runs/stage12_dynamic_online_pro_200/20260831_184843_+0800`.
`candidate-limit=20` truncates only the node-trace snapshots; retrieval,
fusion, LambdaMART input and final metrics still use the complete dynamic
candidate pools. The run directory contains the aggregate summary, sessions,
turns, node traces, LLM calls, rank audit, portable trace and four raw shards.
