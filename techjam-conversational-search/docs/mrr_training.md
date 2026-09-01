# MRR-oriented LambdaMART experiment

The experiment now defaults to `--ranking-objective mrr`, and early stopping
always selects the tree count by session-weighted frozen-turn MRR@10 on the
synthetic target-disjoint validation split. `--ranking-objective ndcg` remains
available as a control, but it uses the same MRR@10 model-selection metric.

Training groups use deterministic hard-negative mining: keep the known target,
the 20 negatives scored highest by the current PreciseReranker weights, and 10
seeded random negatives for coverage. Override with `--hard-negatives` and
`--random-negatives`. Validation candidates are never mined or truncated.

Runtime feature schema v2 adds title/category signals plus confidence-weighted
constraint satisfaction, hard-constraint violations, unknown evidence, budget
status, and material/color/size/brand match features. Because the feature order
changed, v1 bundles and feature caches are intentionally rejected; collect v2
features and retrain before deployment.

The new objective is a pairwise logistic surrogate with pair weights
`abs(U(rank_positive) - U(rank_negative))`, where
`U(r) = RR@10(r) + top1_bonus * I(r == 1)` and `RR@10(r) = 1/r`
inside the first ten results and zero outside. The original experiment uses
`top1_bonus=0`; the following rounds use 0.5 and 1. It supports the existing
single-target binary labels. Query lambdas are normalized, then weighted so
each training session has equal influence. This directly changes training
gradients; it is not just a change to a reported score. RR is discrete, so this
is a surrogate rather than an exact differentiable MRR loss.

Early stopping uses session-weighted **frozen-turn MRR@10** on the synthetic
validation set. Missing-target validation groups contribute zero; targets are
never added to candidate lists. Ties use the runtime lexical-rank tie break.
This validation proxy is not the official end-to-end dialogue MRR: changing a
ranker can change future dialogue and the first successful turn.

Tree count is selected on synthetic validation, and each bundle is frozen
before its official evaluation. At the user's explicit request, the official
200 is then used to compare at most three loss rounds and retain the best
observed weights. It is consequently a development/selection set, not an
unbiased holdout. MRR improvement is not guaranteed and may trade off against
Hit@10. No public labels are used for gradients or early stopping.

## Data selected by the user

Use `data/synthetic_scenarios_2000.jsonl`, generated from the current 50,000-row
`data/catalog.jsonl`. All 571 distinct target products exist in that catalog.
No 100,000-product catalog is required. The deployed r4 model metadata refers
to a different experiment; that provenance must not be confused with the
dataset the user selected here.

The existing strict target-holdout policy excludes 418 synthetic sessions
whose targets also appear in the official 200. The eligible 1582 sessions
split into 1291 training and 291 validation sessions. Official samples are
never used for fitting or early stopping. Therefore this is a same-data loss
comparison between the newly trained NDCG and MRR models, but comparison with
the deployed r4 also includes a training-data change.

The optional `--feature-cache` reuses historical training/validation candidate
lists only after checking the catalog hash, feature source hash, full data and
split, frozen IDF, group dimensions, candidate IDs, and target labels. It
never loads official test features. This avoids repeating expensive feature
collection and records the historical collector provenance explicitly.

## Run

From `techjam-conversational-search`, using the existing Python environment:

```powershell
.venv\Scripts\python.exe scripts\experiment_lambdamart.py `
  --synthetic data/synthetic_scenarios_2000.jsonl `
  --catalog data/catalog.jsonl `
  --ranking-objective mrr --hard-negatives 20 --random-negatives 10 --train-only `
  --output evaluation_runs/lambdamart_mrr_synthetic2000
```

Use a distinct output directory for the `--ranking-objective ndcg` control.
Both runs are offline. `--train-only` prevents official test trajectories;
official target IDs are read solely to enforce separation. Models and the
same-data linear audit control are written under the experiment output.

For rounds 2 and 3, add `--mrr-top1-bonus 0.5` and `--mrr-top1-bonus 1`,
respectively, with separate output directories. The learner, 13 features,
seed, learning rate, tree capacity, regularization, training rows, validation
rows, and plain-MRR early-stopping rule stay fixed across these three rounds.
Training starts from the same initialization each time; retained bundles are
independent ensembles, not cumulative additions to the previous model.

Evaluate the frozen bundles with the user-selected Flash model, local dense
backend, and four workers per run. Re-evaluate the original bundle with Flash
as well; the earlier Pro scores are not a like-for-like baseline:

```powershell
.venv\Scripts\python.exe scripts\evaluate_parallel_with_traces.py `
  --catalog data/catalog.jsonl --dataset data/test/users.jsonl `
  --ltr-model-dir evaluation_runs/lambdamart_mrr_synthetic2000/model `
  --ltr-ranker lambdamart --model deepseek-v4-flash --workers 4 `
  --output-root evaluation_runs/mrr_flash_official_200
```

This second command makes paid API calls using the existing environment
configuration. All three training runs have completed. Frozen bundles,
checksums, fixed parameters, and the selection rule are preserved in
`models/loss_search_20260901/manifest.json`. Flash evaluations are recorded
under `evaluation_runs/loss_flash_20260901/`.

Final scores, bundle selection, and limitations are recorded in
[the three-round Flash comparison](mrr_loss_search_20260901.md).

Checks: `python -m pytest tests/unit/test_mrr_objective.py tests/unit/test_lambdamart.py`.
They cover top-rank pair weighting, no cross-query weights, missing-target
validation, ties, the cutoff, and a real LightGBM training/save/load roundtrip.

For the full backend/simulator checks, set both `DEEPSEEK_MODEL` and
`LLM_MODEL` to `deepseek-v4-flash` in the test process. The simulator gives
`LLM_MODEL` priority; unrelated local settings otherwise affect its default
model contract test. No production behavior was changed to accommodate that
test. The full suite passes 184 checks with these explicit settings.

LightGBM's custom-objective interface is documented at
https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRanker.html.
