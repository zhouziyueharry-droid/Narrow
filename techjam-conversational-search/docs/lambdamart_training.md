# LambdaMART 精排序模型训练说明

本文说明实验分支 `codex/lambdamart-reranker` 中的 LambdaMART 模型如何训练、验证、冻结并接入在线评测。它描述的是已经产出模型哈希 `d4243775f26f8fc5b651becd0100d6a69d232401b73b7371f1c9e0bc4f72b79a` 的那一次训练，不是新的训练计划。

该模型只替换精排序器：粗召回、RRF 融合、硬约束过滤、对话状态和默认 `PreciseReranker` 都保持原样。模型的输入是每轮粗排后的候选商品及当轮已知需求，输出只用于把这些候选重新排序；它不读取隐藏目标商品、需求卡或用户模拟器的内部答案。`parent_asin` 只用于判断商品是否已在本会话推荐过，从而生成 `novelty_penalty`，不作为可学习的商品 ID 特征。

## 训练目标

问题被建模为 listwise learning-to-rank，而不是“判断单个商品是否相关”的二分类：同一次对话、同一轮、同一份候选列表构成一个 group。模型学习在 group 内让目标商品排在前面。

标签来自本地评测模拟器：该轮候选中与场景 `ground_truth.parent_asin` 相同的商品标为 `1`，其余候选标为 `0`。这是“能否找回指定商品”的二元弱监督；零标签表示“不是本场景指定 ASIN”，并不等于该商品对真实用户完全无关。因此本模型不应被解释为购买概率或通用相关性模型。

为了避免人为制造正例：

- 只记录真实召回、融合和过滤后进入精排的候选；未召回目标不会补入候选列表。
- 只有目标存在且 group 至少有两个候选时，才进入 LambdaRank 训练；没有排序对的全负 group 丢弃。
- `intent_override` 场景只从改意图轮开始记录，改意图之前不拿之后的目标商品监督模型。
- 每个有效 group 的样本权重为 `1 / 该会话有效 group 数`，让长对话不会因为产生更多轮次而支配训练。

## 数据、隔离与切分

输入是用户提供的 `synthetic_scenarios_2000.jsonl`（2,000 个合成场景、571 个目标商品）以及固定的官方 `data/public_set.jsonl`（200 个场景）。商品目录始终是完整的 50,000 商品 catalog；排除的是监督样本中的目标，不是从 catalog 删除测试商品。

切分先收集官方 200 条中出现的目标 ASIN，把合成数据中目标属于该集合的 418 条场景全部移除。余下场景按 **目标商品** 而不是按行随机切分，因此同一商品的不同场景不会横跨训练、验证和正式测试。使用随机种子 `20260830`，验证比例为 20%。

| 集合 | 场景数 | 独立目标商品 | 用途 |
|---|---:|---:|---|
| 训练 | 1,291 | 368 | 拟合树模型和同数据线性对照 |
| 验证 | 291 | 92 | NDCG@10 早停 |
| 官方测试 | 200 | 200 | 最终离线报告，不参与调参 |

训练时由旧 `PreciseReranker` 驱动完整的离线对话和候选产生流程，再由记录器保存各轮候选和特征。这意味着新模型的监督目标与官方测试目标隔离，但候选生成轨迹来自旧精排器。旧 Precise 权重早先使用过完整合成数据，可能见过官方目标商品；所以不能把整个端到端系统称为完全测试隔离，隔离结论仅适用于这次树模型和同数据线性模型的训练样本。

本次训练产生了：训练集 3,587 个 group、1,749,029 行候选，其中 2,650 个 group 含目标；验证集 781 个 group、385,343 行候选，其中 576 个 group 含目标。

## 特征

特征顺序固定为 schema version `1`，模型加载时会校验名称和顺序。所有特征都来自当前候选、当前 query、当前 category/constraints、用户 profile 和推荐历史。

| 特征 | 含义 |
|---|---|
| `exact_matches` | 商品明确满足的约束数；含符合预算的情况。 |
| `partial_matches` | 对未精确匹配约束的词项覆盖比例。 |
| `category_match` | 请求 category 是否作为规范化短语出现在商品文本中。 |
| `term_coverage` | query 词在商品文本中的 IDF 加权覆盖率。 |
| `lexical_signal` | `1 / lexical_rank`。 |
| `rrf_raw` | 上游 RRF 融合原始分数。 |
| `dense_raw` | 稠密召回的原始分数。 |
| `attribute_raw` | 属性索引召回的原始分数。 |
| `profile_match` | 用户偏好标签对商品文本的 IDF 加权覆盖率。 |
| `quality` | 平滑后的商品评分，使用 4.0、权重 20 的先验后除以 5。 |
| `contradictions` | 商品明确属性与软约束冲突的次数。 |
| `budget_penalty` | 价格超出或低于预算的归一化惩罚。 |
| `novelty_penalty` | 本会话此前已推荐过时为 1。 |

`term_coverage` 和 `profile_match` 使用由全部 catalog 预先计算的 IDF 表，而非当前候选集上的局部统计。该 IDF 与模型一同冻结为 `idf.json`。商品文本由 title、categories、features、details、store 组成。原始召回分数不按每批候选重新归一化，避免同一模型分数随候选批次变化。

## 算法与参数

训练库为 LightGBM 4.7.0 的 `LGBMRanker`，目标函数是 `lambdarank`，评估指标是 `ndcg`。参数在开始官方测试前固定：

```text
objective=lambdarank          metric=ndcg
n_estimators=300              learning_rate=0.05
num_leaves=15                 max_depth=5
min_child_samples=40          reg_lambda=5.0
lambdarank_truncation_level=13
random_state=20260830         deterministic=true
force_col_wise=true           n_jobs=4
```

在合成验证集上以 `NDCG@10` 早停，patience 为 30，得到 `best_iteration = 167`。正式 200 条测试没有参与特征选择、参数选择或树数选择。训练结束后，将刚拟合的 booster 与重新加载后的 `LambdaMARTReranker` 在验证矩阵前 500 行逐元素比对预测值，容差为 `1e-12`。

同时以相同的训练行、标签、候选特征和会话权重训练 `LogisticRegression(C=100, class_weight=balanced, max_iter=3000)`。这是“同数据线性”控制组，用于区分训练数据变化与树模型表达能力；它不是线上默认排序器。

## 产物和防错检查

原训练输出目录为 `evaluation_runs/lambdamart_synthetic_2000_official_200/`，已从 final 清理，不是当前可用入口。
无需恢复旧训练目录即可加载已提交的冻结包 `models/lambdamart_synthetic_2000/`：

| 文件 | 用途 |
|---|---|
| `model.txt` | LightGBM booster。 |
| `idf.json` | 训练时的全目录 IDF。 |
| `metadata.json` | 特征 schema、参数、数据摘要、输入文件哈希和最佳迭代数。 |
| `same_data_linear_weights.json` | 同数据线性对照权重，供详细审计使用，不是默认精排。 |

运行时会拒绝 schema version、特征顺序、IDF 或预测形状不匹配的模型。模型输出是相对排序 margin，不是概率。若分数相同，则以较小的 lexical rank 打破平局。

## 离线验证结果

对官方 200 条的完整离线模拟评测结果如下。三种精排均从各自的完整对话轨迹运行；LambdaMART 的结果是训练完成并冻结后得到的。

| 精排 | Hit@10 | MRR | MTTC | TechnicalScore | 精排中位耗时 |
|---|---:|---:|---:|---:|---:|
| 原 Precise | 87.5% | 0.4119 | 3.695 | 0.7072 | 16.45 ms |
| 同数据线性 | 91.0% | 0.4388 | 3.430 | 0.7381 | 16.40 ms |
| LambdaMART | 92.0% | 0.4781 | 2.875 | 0.7659 | 18.13 ms |

在固定旧 Precise 的候选和对话状态、仅替换打分的冻结对照中，LambdaMART 的每会话平均轮次 Hit@10 / RR / NDCG@10 为 `0.7347 / 0.4227 / 0.4911`，高于 Precise 的 `0.6011 / 0.3091 / 0.3674`。对完整会话 TechnicalScore 的配对自助法比较中，LambdaMART 相对同数据线性高 `0.02789`，95% 区间为 `[0.00559, 0.05173]`；这是该本地评测上的估计，不等于真实用户或私有榜单收益。

## 复现训练

训练不调用 LLM、不开启远程追踪，并强制使用本地稠密检索。需要准备被忽略的 `data/catalog.jsonl`，以及与本次相同、SHA-256 为 `5948baae33053d13a0506c9a895d0857cdd5b26fbe247bd18437ece21769f7af` 的合成数据文件。

在工作区根目录执行：

```powershell
.\run_local_python.ps1 scripts/experiment_lambdamart.py `
  --synthetic data/synthetic_scenarios_2000.jsonl `
  --output evaluation_runs/lambdamart_synthetic_2000_official_200_reproduced
```

输出目录必须是新目录，脚本会拒绝覆盖已有结果。完成后应检查 `model/metadata.json` 中的 catalog、public data、特征源码和训练脚本哈希；不同依赖版本或数据版本不会保证得到相同的 `model.txt`。

## 在线使用边界

线上评测加载的是已冻结的模型，LLM 只参与需求理解和对话决策。运行时需显式指定 `--ltr-ranker lambdamart` 和 `--ltr-model-dir`；默认值仍是 `PreciseReranker`。本次在线 Pro 结果、完整 trace 与审计方法见 [lambdamart_online_pro_report.md](lambdamart_online_pro_report.md)。

模型不会解决上游没有召回、对话没有获得区分信息或目标本身未在候选池中的问题。它的责任边界是：在已经进入精排的候选里学习排序。
