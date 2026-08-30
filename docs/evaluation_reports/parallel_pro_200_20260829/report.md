# Parallel Traced Evaluation Report

Run: `20260829_232205_+0800`  
Model: `deepseek-v4-pro`  
Workers: `12`  
Samples: `200`

## Score

| Metric | Value |
|---|---:|
| Hit Rate@10 | 0.900000 |
| MRR | 0.335181 |
| MTTC | 3.315000 |
| Efficiency | 0.768500 |
| Technical Score | 0.704254 |
| Prompt tokens | 1488005 |
| Completion tokens | 135630 |
| Total tokens | 1623635 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 10 | 0.900000 | 0.367897 | 3.400000 |
| browsing | 80 | 0.937500 | 0.350575 | 3.000000 |
| buying | 80 | 0.912500 | 0.342728 | 2.700000 |
| intent_override | 30 | 0.766667 | 0.263095 | 5.766667 |

Complete aggregate data is stored in `sessions.jsonl`, `turns.jsonl`,
and `node_traces.jsonl`. Per-worker raw outputs and logs are under `shards/`.
