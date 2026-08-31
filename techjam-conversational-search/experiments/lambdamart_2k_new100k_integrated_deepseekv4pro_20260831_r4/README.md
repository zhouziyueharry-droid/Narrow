# Integrated New100K LambdaMART 2K Training

本目录是合入动态多路检索链路后的 New100K LambdaMART 训练结果。这里只发布训练与离线验证产物；DeepSeek v4 Pro 官方 200 在线测评正在单独运行，完成后另行提交。

## Data and split

- Training sessions: `data/metadata_derived/raw_metadata_clothing_500k_sessions_2000.jsonl` (2,000 rows, 1,536 unique targets)
- Training/validation catalog: `data/metadata_derived/raw_metadata_new100k_agent_catalog.jsonl` (100,000 products)
- Split: 1,621 training sessions / 379 validation sessions, seed `20260830`, validation fraction `0.2`
- Official test set: 200 public sessions, kept out of training and validation; official catalog is loaded only after model freeze
- Session SHA-256: `a3563cb7f78d9b8ea7b4ac41d7219db77c637d3e72b5b8f47b7778cadfeaf35f`
- Training catalog SHA-256: `51d12c525b5d90f22709d58d847db65d1f0290a96cc8af3a60329050cb1508e3`

## Model and runtime

- Ranker: LightGBM LambdaMART (`objective=lambdarank`)
- Features: 13; early stopping selects validation NDCG@1 first, then NDCG@10
- Parameters: `n_estimators=300`, `learning_rate=0.05`, `num_leaves=15`, `max_depth=5`, `min_child_samples=40`, `reg_lambda=5.0`, `lambdarank_truncation_level=13`, deterministic, column-wise, `n_jobs=4`
- Best iteration: `66`
- Runtime: Python 3.12.13, LightGBM 4.7.0, NumPy 2.5.2, scikit-learn 1.9.0, local dense backend
- Training groups: 4,604 groups / 2,929,038 candidate rows; validation: 1,105 groups / 699,147 rows

## LLM boundary

Training and validation were offline. Agent and user verbalizer did not use an LLM; API calls, tokens, and cost were all `0`. The final official-200 online evaluation is separate and uses `deepseek-v4-pro` only after this model is frozen.

## Files in this published bundle

- `config.json`: reproducibility configuration, data hashes, runtime and LLM policy
- `split_manifest.json`: exact train/validation split and target isolation
- `data_summary.json`: grouped candidate counts
- `validation_frozen.json`: frozen-trajectory validation comparison
- `feature_importance.json`: LambdaMART gain importance
- `same_data_linear_weights.json`: same-data linear control
- `model/model.txt`, `model/idf.json`, `model/metadata.json`: frozen model bundle

Large training matrices, candidate group dumps, temporary logs, and online DeepSeek traces are intentionally not included in this commit.

## Verification

The integrated unit-test set passed (`15 passed`), and `git diff --check` reported no whitespace errors. The official online result is not claimed in this directory until its separate run completes.
