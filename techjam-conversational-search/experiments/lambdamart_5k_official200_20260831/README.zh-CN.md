# LambdaMART 5K / 官方 200 条实验

本目录是 SLURM job `32991` 的精简可审计实验包。作业在 CCDS TC2 上以 `State=COMPLETED`、`ExitCode=0` 正常结束，总用时 `01:18:55`。模型使用 4,003 条合成会话训练、997 条合成会话做早停验证，最后只在官方 200 条 TechJam public set 上测试一次。

结论是：5K LambdaMART 明显优于当前 Precise 基线，但没有超过之前的无泄漏 2K LambdaMART 实验。因此本次没有修改默认精排器，`default_changed=false`。

## 官方 200 条结果

| 精排器 | Hit@10 | MRR | MTTC | Technical Score | 精排中位延迟 | 精排 P95 延迟 |
|---|---:|---:|---:|---:|---:|---:|
| Precise | 0.875 | 0.4119 | 3.695 | 0.7072 | 40.68 ms | 65.28 ms |
| 同数据线性模型 | 0.910 | 0.4319 | 3.450 | 0.7356 | 40.76 ms | 64.97 ms |
| LambdaMART 5K | 0.900 | 0.4629 | 3.030 | 0.7483 | 42.74 ms | 66.74 ms |

相对 Precise，5K LambdaMART 的逐会话配对 Technical Score 估计提高 `0.04112`，95% bootstrap 区间为 `[0.01173, 0.07085]`。相对同数据线性模型提高 `0.01271`，但区间 `[-0.01479, 0.03993]` 跨过 0，不能据此认定优势稳定。

## 2K 与 5K 对比

| LambdaMART 实验 | 训练 / 验证会话 | Hit@10 | MRR | MTTC | Technical Score | 冻结 NDCG@10 | 最佳迭代 | 精排中位延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 之前的 2K 来源实验 | 1,291 / 291 | 0.920 | 0.4781 | 2.875 | 0.7659 | 0.4911 | 167 | 18.13 ms |
| 本次 5K 实验 | 4,003 / 997 | 0.900 | 0.4629 | 3.030 | 0.7483 | 0.4851 | 85 | 42.74 ms |
| 5K 减 2K | +2,712 / +706 | -0.020 | -0.0152 | +0.155 | -0.0176 | -0.0060 | -82 | +24.61 ms |

两次延迟来自不同运行环境，跨实验的延迟差只能作为记录，不能直接认定代码性能回退。在 job `32991` 内部，LambdaMART 相对 Precise 的单次精排中位延迟增加约 `2.06 ms`。

增加合成会话没有提高官方 200 条得分。5K 数据仍围绕 482 个合格目标商品重复生成，主要增加的是轨迹数量，而不是目标商品多样性；二元弱标签也只把 simulator 指定目标标为正例，不等于人工分级相关性。当前证据不足以替换之前模型或修改默认配置。

## 固定候选诊断

以下结果固定候选列表和对话状态，只替换精排得分；它是逐轮诊断，不是完整会话 Hit@10。

| 数据 / 精排器 | 冻结 Hit@10 | Reciprocal Rank | NDCG@10 |
|---|---:|---:|---:|
| 验证集 / Precise | 0.6631 | 0.3454 | 0.4106 |
| 验证集 / 同数据线性 | 0.6699 | 0.3546 | 0.4193 |
| 验证集 / LambdaMART 5K | 0.8406 | 0.5520 | 0.6176 |
| 官方 200 / Precise | 0.6011 | 0.3091 | 0.3674 |
| 官方 200 / 同数据线性 | 0.6252 | 0.3188 | 0.3815 |
| 官方 200 / LambdaMART 5K | 0.6940 | 0.4305 | 0.4851 |

## 数据隔离与复现信息

- 50,000 商品 catalog：SHA256 `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`。
- 5,000 条合成会话：482 个合格目标，SHA256 `25d8d48411a08dee2f35295498a84e6b5edde1fef116db1e89bfe43a1dfd8973`。
- 官方 public set：200 条会话 / 200 个目标，SHA256 `571359a8a69014c43fc30d39c996c4a28e875dccc249dffc707358757beb16c0`。
- 合成数据与官方目标重叠行数：`0`。
- 训练集：4,003 会话、386 个唯一目标、11,625 groups、5,676,583 个候选行。
- 验证集：997 会话、96 个唯一目标、2,431 groups、1,193,734 个候选行。
- 训练与验证目标重叠：`0`；两者都排除了全部官方目标。
- 模型 SHA256：`28e34799afe98b5894ea432beb5e8c3af8cff62a49b3ea2e86ad4135c91f254f`。

模型复用原有 13 个精排特征。按 gain 排名前五的是 `term_coverage`、`quality`、`rrf_raw`、`category_match` 和 `attribute_raw`。

## 运行环境与模型调用

- 节点：`TC2N01`；纯 CPU；申请 6 CPUs / 24 GiB；峰值 RSS 约 2.93 GiB。
- Python 3.12.14；LightGBM 4.7.0；最佳迭代数 85。
- Agent LLM：关闭，`SHOPPING_AGENT_ENABLE_LLM=false`。
- 用户表达生成：离线确定性 simulator 模板，不使用 LLM。
- Dense backend：本地模式，`SHOPPING_DENSE_BACKEND=local`。
- LangSmith / LangChain tracing：关闭。
- API calls=0，prompt tokens=0，completion tokens=0，estimated cost=0，cost status=`not_applicable_no_api_usage`。
- 代码发现任何 prompt/completion token 使用都会直接终止实验。

stderr 唯一内容是 LightGBM 4.7.0 对 `eval_set` 的弃用提醒，不影响本次完成状态和产物完整性；后续维护可改用 `eval_X`、`eval_y`。

## 文件说明

- `summary.json`：官方 200 核心指标、数据拆分、延迟、配对比较和模型哈希。
- `report.md`：TC2 原始自动报告。
- `comparison_2k_vs_5k.json`：2K 与 5K 的机器可读对比。
- `model/`：可部署模型、冻结 IDF 和模型元数据。
- `test_frozen_metrics.json`、`validation_frozen.json`：固定候选逐轮诊断。
- `*_sessions.json`：三个精排器的 200 条会话级结果。
- `training_collection_sessions.json`、`validation_collection_sessions.json`：精简采集记录；大型候选矩阵没有提交。
- `split_manifest.json`：会话及目标拆分审计。
- `logs/`：完整 SLURM stdout/stderr。
- `SHA256SUMS`：除自身以外全部实验文件的 SHA256。

## 验证口径

这些 JSON 使用 `scripts/experiment_lambdamart.py` 的离线 LTR 实验结构，不具备统一 simulator report 所要求的顶层 `evaluation`、`turn_metrics`、`latency`、`model_usage`、`mode_specific_metrics`、`sessions`。因此不会把它们伪装成通过 `shopping-simulator-evaluation` validator；本次分别验证 JSON 可解析性、会话数量、哈希、单元测试和 Git whitespace。

本结果属于离线本地 simulator 测试，不代表私有榜单成绩，也不代表真实用户环境效果。
