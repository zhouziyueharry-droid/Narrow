# Realistic simulator evaluation

Schema version: `1.0`

## Evaluation

| Metric | Value |
|---|---:|
| `benchmark` | catalog_generated_realistic |
| `official_metric_contract` | no |
| `sample_count` | 100 |
| `successful_sessions` | 97 |
| `success_rate` | 0.97 |
| `mrr` | 0.709524 |

## Turn metrics

| Metric | Value |
|---|---:|
| `max_turns` | 10 |
| `session_count` | 100 |
| `total_executed_turns` | 141 |
| `mean_executed_turns` | 1.41 |
| `median_executed_turns` | 1 |
| `successful_session_mean_turns` | 1.14433 |
| `unsuccessful_session_mean_turns` | 10 |

| Turn | Executed sessions | First hits |
|---:|---:|---:|
| 1 | 91 | 91 |
| 2 | 3 | 3 |
| 3 | 1 | 1 |
| 4 | 1 | 1 |
| 5 | 0 | 0 |
| 6 | 0 | 0 |
| 7 | 1 | 1 |
| 8 | 0 | 0 |
| 9 | 0 | 0 |
| 10 | 3 | 0 |

## Latency

Clock: `time.perf_counter`; unit: `milliseconds`.

| Component | Count | Total | Mean | P50 | P95 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Agent | 141 | 14246.025 | 101.036 | 92.784 | 129.932 | 365.025 | 473.079 |
| User generation | 141 | 1.312 | 0.009 | 0.008 | 0.011 | 0.063 | 0.124 |
| Session wall | 100 | 61735.903 | 617.359 | 159.353 | 1160.031 | 11129.176 | 12153.314 |

## Model usage

| Component | Provider/model | Calls | API calls | Prompt tokens | Completion tokens | Total tokens | Errors/fallbacks | Estimated cost (USD) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Agent | local/N/A | 141 | 0 | 0 | 0 | 0 | 0 | 0 |
| User verbalizer | template/none | 141 | 0 | 0 | 0 | 0 | 0 | 0 |
| Combined | — | — | 0 | 0 | 0 | 0 | — | 0 |

Agent cost status: `not_applicable_no_api_usage`; verbalizer cost status: `not_applicable_no_api_usage`.

## Mode-specific metrics

| Metric | Value |
|---|---:|
| `acceptance` | need_based |
| `hard_constraint_satisfaction_at_acceptance` | 1 |
| `mean_soft_matches_at_acceptance` | 1.525773 |
| `override_events` | 1 |
| `relaxation_events` | 0 |

| Persona | Sessions |
|---|---:|
| bargain_hunter | 13 |
| brand_loyalist | 13 |
| casual_browser | 13 |
| decisive_buyer | 13 |
| expert_shopper | 12 |
| indecisive_shopper | 12 |
| novice_shopper | 12 |
| picky_shopper | 12 |
