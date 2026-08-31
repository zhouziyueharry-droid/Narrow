# LambdaMART 5K data-scaling experiment

This experiment keeps the 2K LambdaMART feature schema, model parameters,
official 50K catalog, and official 200-session final test fixed. It changes
only the amount and construction of non-official synthetic training data.

## Dataset

- file: `data/synthetic_scenarios_5000.jsonl`
- rows: 5,000
- unique eligible targets: 482
- target repetitions: 10 or 11 scenarios per target
- generation seed: `20260831`
- split seed: `20260830`
- official public target overlap: zero
- missing official-catalog targets: zero
- SHA-256: `25d8d48411a08dee2f35295498a84e6b5edde1fef116db1e89bfe43a1dfd8973`

The scenario distribution is an exact 25x scaling of the public 200-session
distribution: 2,000 Buying, 2,000 Browsing, 750 Intent Override, and 250
Boundary. Targets satisfy the same price, feature-count, and review-count
filters used by the earlier generator. All official public-set targets are
removed before target scheduling.

Target-grouped splitting produces 4,003 training sessions over 386 targets and
997 validation sessions over 96 targets. The official 200 sessions remain a
separate final test; train, validation, and official test target sets are
pairwise disjoint.

## Controlled comparison

Compare the frozen 2K baseline with this 5K run using:

- validation NDCG@10 and best iteration;
- official Hit@10, MRR, MTTC, Efficiency, and Technical Score;
- same-candidate frozen Hit@10, reciprocal rank, and NDCG@10;
- paired bootstrap intervals;
- rank-call median/P95 latency;
- feature importance and model SHA-256.

The official 200 test must not be used for parameter selection. The run is
offline, disables LLM calls and remote tracing, and does not change the default
production reranker.

## TC2 execution

Submit `scripts/run_lambdamart_5k_tc2.slurm` from the staged repository root.
The current LightGBM configuration is deterministic CPU training (`n_jobs=4`),
so the job requests CPU and memory but no GPU. This avoids occupying an L40S
for a workload that does not use CUDA.
