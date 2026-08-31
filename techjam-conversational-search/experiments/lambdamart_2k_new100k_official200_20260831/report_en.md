# New100K / 2K LambdaMART Training and Isolated Official-200 Test

This branch-only experiment keeps PreciseReranker as the default. Neither the Agent nor the user verbalizer used an LLM; API calls, tokens, and cost are all zero.
Training sessions: 1570; validation sessions: 430; official test sessions: 200.
Training catalog SHA256: `51d12c525b5d90f22709d58d847db65d1f0290a96cc8af3a60329050cb1508e3`.
Official test catalog SHA256: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`.
Official targets present in the training catalog: 0.
The official 50K catalog is loaded only after the model and training IDF are frozen. Early stopping evaluates NDCG@1 first and NDCG@10 second.

| Ranker | Hit@10 | MRR | MTTC | Technical Score | Median rerank latency (ms) |
|---|---:|---:|---:|---:|---:|
| precise | 0.875 | 0.4119 | 3.69 | 0.7072 | 26.12 |
| old_lambdamart | 0.920 | 0.4781 | 2.88 | 0.7659 | 30.31 |
| linear_same_data | 0.900 | 0.4211 | 3.52 | 0.7260 | 26.48 |
| lambdamart | 0.920 | 0.5330 | 2.85 | 0.7828 | 28.37 |

## Acceptance decision

```json
{
  "mrr_delta": 0.054871,
  "mrr_delta_at_least_0_02": true,
  "hit_at_10_delta": 0.0,
  "hit_at_10_not_lower_by_more_than_0_005": true,
  "technical_score_delta": 0.01686130000000008,
  "technical_score_improved": true,
  "recommended_merge": true
}
```

The official 200 remains a local public benchmark, not evidence of private-leaderboard or real-user performance.
The experiment JSON files use the LambdaMART experiment schema rather than the unified simulator-report schema; no unified-schema validator pass is claimed.
