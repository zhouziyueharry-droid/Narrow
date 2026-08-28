# TechJam simulator evaluation

Schema version: `1.0`

## Evaluation

| Metric | Value |
|---|---:|
| `benchmark` | techjam |
| `official_metric_contract` | yes |
| `sample_count` | 200 |
| `hit_rate_at_10` | 0.82 |
| `mrr` | 0.329188 |
| `mttc` | 4.005 |
| `efficiency` | 0.6995 |
| `recommended_technical_score` | 0.648656 |

## Turn metrics

| Metric | Value |
|---|---:|
| `max_turns` | 10 |
| `session_count` | 200 |
| `total_executed_turns` | 765 |
| `mean_executed_turns` | 3.825 |
| `median_executed_turns` | 3 |
| `successful_session_mean_turns` | 2.469512 |
| `unsuccessful_session_mean_turns` | 10 |

| Turn | Executed sessions | First hits |
|---:|---:|---:|
| 1 | 75 | 75 |
| 2 | 19 | 19 |
| 3 | 28 | 28 |
| 4 | 22 | 22 |
| 5 | 10 | 10 |
| 6 | 5 | 5 |
| 7 | 1 | 1 |
| 8 | 3 | 3 |
| 9 | 1 | 1 |
| 10 | 36 | 0 |

## Latency

Clock: `time.perf_counter`; unit: `milliseconds`.

| Component | Count | Total | Mean | P50 | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Agent | 765 | 165030.953 | 215.727 | 193.376 | 336.041 | 1151.917 | 1363.96 |
| User generation | 765 | 0.215 | 0 | 0 | 0.001 | 0.001 | 0.034 |
| Session wall | 200 | 165099.625 | 825.498 | 447.719 | 2746.119 | 3424.331 | 3632.745 |

## Model usage

| Component | Provider/model | Calls | API calls | Prompt tokens | Completion tokens | Total tokens | Errors/fallbacks | Estimated cost (USD) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Agent | local/N/A | 765 | 0 | 0 | 0 | 0 | 0 | 0 |
| User verbalizer | template/none | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Combined | — | — | 0 | 0 | 0 | 0 | — | 0 |

Agent cost status: `not_applicable_no_api_usage`; verbalizer cost status: `not_applicable_no_api_usage`.

## Mode-specific metrics

| Metric | Value |
|---|---:|
| `target_match` | exact_parent_asin |
| `miss_turn_value` | 11 |

| Scenario | N | Hit Rate@10 | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 10 | 0.7 | 0.297778 | 4.7 |
| browsing | 80 | 0.8 | 0.338046 | 4.1125 |
| buying | 80 | 0.85 | 0.313874 | 3.2625 |
| intent_override | 30 | 0.833333 | 0.356878 | 5.466667 |
