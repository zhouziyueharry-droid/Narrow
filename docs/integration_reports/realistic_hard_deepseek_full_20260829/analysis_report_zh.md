# Realistic Hard DeepSeek 完整评测报告

## 运行信息

- 运行编号：`realistic_hard_deepseek_full_20260829`
- 测试分支：`test/realistic-hard-20260829`
- 评测提交：`06795c29b36af012995217d35a4c562ae6891d88`
- 拉取的 `origin/main`：`8f4f392407c47c46be5c528069f088218ffbea97`
- 模型：Shopping Agent 与用户语言化模块均使用 `deepseek-v4-flash`
- 运行时间：2026-08-29 17:15:40 至 17:22:18，新加坡时间，共 398.5 秒
- 本次为基于真实需求的 realistic 评测，`official_metric_contract=false`，不能作为官方 TechJam 分数。

## 模型使用与非 LLM 边界

本次运行不是“所有组件都由 LLM 驱动”。DeepSeek 只参与两项语言任务，检索和判分仍由确定性代码完成。

| 组件 | 是否使用 LLM | 本次模型或实现 | 具体作用 |
| --- | --- | --- | --- |
| Shopping Agent 的 `understand_user` | 是 | `deepseek-v4-flash` | 将用户自然语言解析为结构化 `StatePatch`，包括意图、类别、约束、撤销与覆盖信息 |
| Simulator 用户语言化模块 | 是 | `deepseek-v4-flash` | 将 simulator 已决定的结构化用户 dialogue act 改写为自然语言；它不决定用户目标或是否接受 |
| Agent 本地规则解析与失败回退 | 否 | Python 确定性规则 | 提供规则信号，并在 LLM 不可用或输出无效时生成本地解析结果 |
| Catalog 检索、候选融合与约束过滤 | 否 | 本地确定性检索代码 | 从 50,000 商品目录中召回、合并并过滤候选商品 |
| Fallback reranking、追问策略和响应模板 | 否 | 本地确定性代码 | 对候选排序、选择待询问属性并生成 Agent 响应框架 |
| Simulator 目标、persona、偏好覆盖和预算放宽 | 否 | 固定 seed 和场景规则 | 决定模拟用户真实需求及其随轮次发生的变化 |
| Acceptance checker | 否 | 硬约束和软偏好规则 | 判断推荐商品是否满足全部硬约束和至少 2 个软偏好 |
| Evaluator 指标计算 | 否 | 确定性 Python 公式 | 计算 success rate、MRR、轮次、延迟、token 和模式特定指标 |

Agent 的 DeepSeek 路径只负责语义理解，不直接从商品目录中选择最终商品，也不参与最终评分。本次 151 个 Agent 响应均报告了模型 token，用量为 128,583 tokens；Agent 合同不报告独立 API 调用次数，因此该字段保持为 `null`，不能推测为 151 次。用户语言化模块明确完成 151 次 DeepSeek API 调用，用量为 33,823 tokens，fallback 为 0。Evaluator 判分过程没有调用 LLM。

作为对照，TechJam 官方模式使用确定性 template 生成模拟用户消息，用户侧不使用 LLM；官方 evaluator 同样不使用 LLM。TechJam 模式下只有参赛 Shopping Agent 可以在启用配置后使用 DeepSeek。

## 难度设计

`realistic_hard` 预设包含 24 个由商品目录确定性生成的会话、8 种用户人格、最多 8 轮对话、至少 3 个软偏好，以及至少满足 2 个软偏好的接受条件。初始预算只比种子商品价格高 2%，用户第一轮只透露商品类别。当 Agent 仍在提出澄清问题时，即使推荐列表中已经出现满足需求的商品，simulator 也不会让用户提前接受。

四种压力场景各包含 6 个会话：

1. `hidden_preferences`：用户逐步透露隐藏偏好。
2. `preference_override`：用户中途改变或撤销先前偏好。
3. `budget_relaxation`：用户在第 4 轮以后放宽原本严格的预算。
4. `override_and_relaxation`：同时发生偏好变化和预算放宽。

## 评测结果

- 会话总数 24；成功 19；失败 5；成功率 **79.17%**。
- 实际执行 151 轮；平均 6.29 轮；中位数 6.5 轮；5 个失败会话都运行到 8 轮上限。
- 基于需求的 MRR 为 0.7167；接受时硬约束满足率为 100%；接受时平均满足 2.42 个软偏好。
- 共有 74 次候选商品满足接受条件，但因为 Agent 仍在追问而被阻止提前接受。
- Agent 仍在追问时被错误接受的次数为 0。
- 发生 12 次偏好覆盖和 12 次预算放宽。
- Agent 平均延迟 1,289 毫秒，P95 为 1,747 毫秒，最大 2,748 毫秒。
- 用户语言化模块平均延迟 683 毫秒，P95 为 1,003 毫秒，最大 1,756 毫秒。
- Agent 完成 151 次响应，151 次均报告 token，用量 128,583 tokens，错误数为 0。
- 用户语言化模块完成 151 次 API 调用，用量 33,823 tokens，fallback 次数为 0。
- 合计报告 162,406 tokens。由于没有提供明确的价格来源，费用保持为 `null`，没有推算成本。

### 按压力场景划分

| 场景 | 成功数 | 成功率 | 平均轮数 |
| --- | ---: | ---: | ---: |
| 隐藏偏好 | 4/6 | 66.7% | 6.50 |
| 中途改变偏好 | 6/6 | 100.0% | 5.83 |
| 放宽预算 | 4/6 | 66.7% | 6.50 |
| 改变偏好并放宽预算 | 5/6 | 83.3% | 6.33 |

### 按用户人格划分

小样本中表现最弱的是 `bargain_hunter`（1/3）和 `decisive_buyer`（1/3）。`brand_loyalist`、`casual_browser`、`expert_shopper`、`novice_shopper` 与 `picky_shopper` 均为 3/3。每种人格只有 3 个会话，因此这些数字只适合故障诊断，不能视为稳定的总体表现估计。

## 真实失败案例

会话 `realistic_0001_B0949GR8H9` 的需求是 Jewelry Box，预算上限 8.15，品牌偏好 LETURE，颜色偏好白色，材质偏好与皮革相关。尽管目标商品在第 2 轮曾经排在第 3 位，会话最终仍在第 8 轮失败。

实际对话流程和分层原因如下：

1. Agent 询问品牌，用户只回答 `LETURE.`。
2. `understand_user` 返回 `action=no_preference` 和 `no_structured_signal`，没有把这个简短回答绑定到 Agent 上一轮提出的品牌问题。
3. Agent 随后询问 style，用户回答没有偏好。下一轮的 `understand_user` 却删除了之前的 `color`，没有把“无偏好”正确作用于当前的 `style`。
4. Agent 询问预算，用户只回答 `8.15.`。解析器再次返回 `no_structured_signal`，导致预算约束丢失。
5. Agent 停止追问以后，目标商品已经不在前五名，simulator 因此正确拒绝了推荐结果。

这个问题主要是**上下文简短回答解析缺陷**，而不是商品不存在或 simulator 接受逻辑错误。品牌名、纯数字和“没有偏好”之类的回答，必须先与 Agent 保存的上一轮待回答问题绑定，再进入语义解析和状态更新。这个案例也证明了逐层记录的价值：如果只看最终成功或失败，很容易把问题错误归因于检索层。

## 建议 Agent 侧改进

1. 将 `pending_question.attribute` 传入 `understand_user`；或者在调用 LLM 解析器之前，以确定性规则把简短回答绑定到上一轮询问的属性。
2. 当上一轮询问预算时，将纯数字回答解析为 `budget_max`，币种从商品目录或当前会话继承。
3. 将“没有偏好”严格作用于当前待回答属性，不能猜测并删除已经提供的字段，例如 `color`。
4. 为品牌问题后的 `LETURE.`、预算问题后的 `8.15.`，以及 style 问题后的 `I don't have a preference.` 添加回归测试。
5. 用户明确拒绝推荐后，应增加检索恢复策略；如果状态没有更新，仅重复“closest matches”不会产生新的检索证据。

## 验证与证据文件

- 高难模式验证器已通过：24 个会话、四种压力场景、全部人格、13 个必需 Agent 节点、真实 API 使用和接受门控均通过检查。
- 统一报告 schema 验证通过。
- simulator 测试 21 项全部通过。
- Agent 测试 35 项全部通过。
- `realistic.json` 保存完整结果和逐轮 Agent trace。
- `realistic.sessions.jsonl` 保存可恢复的逐会话记录；`realistic.events.jsonl` 保存运行进度事件。
- `realistic.md` 是自动生成的指标报告；全部测试和验证日志位于 `logs/`。
- `00_manifest.json` 固定了准确的 commit、商品目录哈希、模型配置和运行环境，并且没有暴露 API key。

