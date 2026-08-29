# 传统双模式全量测试复盘

## 1. 结论

本次运行成功完成 TechJam 200 个会话和 realistic 100 个会话。所有测试、结果结构校验、逐层轨迹校验和分析阶段均通过；共记录 906 个对话轮次，每轮均覆盖 13 个 Agent 节点，传统模式没有调用外部模型 API。

总体指标与旧传统 baseline 完全一致，但逐轮日志暴露出旧 aggregate baseline 无法观察的交互问题：Agent 的首个澄清问题在 300/300 个会话中都是品牌；253 个成功会话在 Agent 仍在提问时就被模拟器判定接受；67 次模拟用户回答了问题选项之外的真实偏好值。指标复现和真实交互质量必须分开解释。

## 2. 运行身份与完整性

- run id：`traditional_full_20260829_0005`
- 分支：`integration/all-branches-20260828`
- 整合提交：`739cbfd3489d8dbb33f38c9cedb6aa761489837c`
- TechJam 输入：`catalog.jsonl` + `public_set.jsonl`，输入 SHA-256 已记录在 `00_manifest.json`
- 传统配置：Agent LLM 关闭，user verbalizer 使用 template
- 本次进程中 DeepSeek key 状态：未配置；API 调用：0；token：0；费用：0
- 8/8 个运行阶段退出码为 0
- TechJam events：200 started + 200 completed + 0 failed
- realistic events：100 started + 100 completed + 0 failed
- 300 条 session journal 与最终报告中的 scenario id 完全对应
- 906/906 轮轨迹通过；每轮均记录 13 个节点
- 无 `failure.json`，无 trace error，Agent error 为 0，session release error 为 0

## 3. 统一输出结构

两个模式都按照以下结构输出，同时保留逐 session 和逐 turn 证据：

1. `evaluation`
2. `turn_metrics`
3. `latency`
4. `model_usage`
5. `mode_specific_metrics`
6. `sessions`

TechJam 的 `official_metric_contract=true`；realistic 的 `official_metric_contract=false`，后者是 need-based acceptance，不能作为官方 TechJam 分数。

## 4. 最终指标

| 模式 | 会话 | 成功/HitRate@10 | MRR | 平均轮数 | API 调用 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TechJam | 200 | 0.820000 | 0.329188 | 3.825000 | 0 |
| realistic | 100 | 0.970000 | 0.709524 | 1.410000 | 0 |

TechJam 其余官方字段：MTTC `4.005`、efficiency `0.6995`、recommended technical score `0.648656`。这些值与旧 baseline 完全一致。旧 baseline 只有 aggregate Markdown，没有逐 session JSON，因此只能确认总体指标无变化，不能声称不存在逐样本 regression。

### 报告指标本身还需修正的边界

1. 当前 technical score 先使用已经四舍五入到 6 位的 MRR 再计算，得到 `0.648656`；如果直接用 200 个 session 的原始 reciprocal rank 计算、最后统一四舍五入，应为 `0.648657`。差异只有 `1e-6`，但在下一版应消除这次 double rounding。
2. 旧 baseline 没有 session JSON、commit、运行配置或输入 hash。它只能作为 legacy aggregate reference，不能视为严格受控的 A/B 对照。
3. 当前分析没有比较 latency。补充比较后发现，TechJam 的 Agent mean latency 从旧 `215.727 ms` 变为 `106.893 ms`，但 session-wall mean 从 `825.498 ms` 增为 `2903.256 ms`；realistic 的 Agent mean 从 `90.829 ms` 变为 `101.036 ms`，session-wall mean 从 `128.259 ms` 墈为 `617.359 ms`。当前详细 trace 获取和持久化包含在 session wall 中，却没有单独的 `trace_collection_latency`，因此不能把 wall time 上升直接解释为算法变慢。下一版应把 Agent、trace collection、journal serialization 分开计时。
4. realistic 的 `hard_constraint_satisfaction_at_acceptance=1.0` 只描述成功会话被接受时的约束满足情况，不是 100 个会话的全局硬约束成功率；后续报告应同时给出分子、分母和失败会话统计。

## 5. 全量问题计数

| 问题 | TechJam | realistic | 合计 |
| --- | ---: | ---: | ---: |
| 首问固定为品牌 | 200 | 100 | 300 |
| Agent 仍在提问时模拟器接受 | 157 | 96 | 253 |
| 用户答案不在 Agent 给出的三个选项中 | 58 | 9 | 67 |
| 召回层 Top-20 未观察到目标 | 20 | 0 | 20 |
| 融合后 Top-20 丢失目标 | 7 | 0 | 7 |
| 排序层表现不足 | 5 | 0 | 5 |
| realistic 软偏好不足 | 0 | 3 | 3 |
| 推荐过但未被接受 | 2 | 0 | 2 |
| 重复推荐集合 | 7 | 1 | 8 |
| 约束过滤后 Top-20 丢失目标 | 1 | 0 | 1 |
| 响应/Top-K 阶段丢失目标 | 1 | 0 | 1 |

候选轨迹只保存每层 Top-20，因此“未观察到目标”不代表目标绝对不在完整候选集合中。涉及 Top-20 的归因均保留这一置信度边界。

## 6. 真实失败案例 A：错误否定约束导致目标被过滤

场景：TechJam `public_0046`，目标 `B0B42PVX1F`，intent override，最终 10 轮失败。

### 逐层证据

Turn 1 用户说：`I'm looking for Socks & Hosiery Leg Warmers. No Closure closure`

- fallback parser 同时生成了软约束 `contains "No Closure closure"` 和硬约束 `not_contains "Closure closure"`。
- 目标商品出现在 lexical Top-20、attribute Top-20 和 fused Top-20。
- 到 constraint filter 后，目标不再出现在 Top-20，随后也未进入排序和推荐。

Turn 3 用户说：`For that, what matters is: wool; 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester.`

- 文本没有表达“不想要 wool”，但 parser 生成了硬约束 `material not_contains "Wool"`。
- 目标再次在 lexical、dense、attribute 和 fused Top-20 中出现，过滤后再次消失。

Turn 8 用户说：`Those options are not quite right yet. Ask me about one specific attribute.`

- parser 又把一般性的否定反馈误解析成硬约束 `feature not_contains "quite right yet"`。

### 根因判断

这是可观察到的否定词作用域错误：规则把商品字段中的字面短语 `No Closure` 和普通对话反馈中的 `not quite right` 当成商品排除条件。由于目标在融合层 Top-20 中明确出现、在过滤层 Top-20 中消失，过滤阶段问题有直接证据；但轨迹仅保留 Top-20，所以整体诊断置信度仍按 low 记录。

### 给算法同学的行动项

1. 否定解析必须绑定语义作用域，不能只靠 `no/not/without + 后续短语` 的正则。
2. TechJam 的结构化字段值应作为字面属性处理；`No Closure closure` 不能再二次解释为自然语言否定。
3. 增加三条回归测试：`No Closure closure`、含 `Merino Wool` 的成分串、`not quite right` 的对话反馈。

## 7. 真实失败案例 B：Agent 没有理解自己刚问的品牌答案

场景：realistic `realistic_0006_B01LG9U9UY`，目标需求为 Women、预算不超过 `$97.90`，软偏好 brand=`Adoretex`、feature=`Oxford Nylon`，至少满足一个软偏好；最终 10 轮失败。

### 逐轮证据

1. Turn 1：Agent 首问品牌，候选为 `generic / 55carat / uloveido`。
2. Turn 2：模拟用户明确回答 `I'd prefer the brand Adoretex.`。
3. `understand_user` 使用 fallback parser，但返回 `no_structured_signal`；parsed constraints 为空，`update_state` 也为空。
4. Agent 随后继续问 style、material、color、use_case，却始终没有记住 `Adoretex`。
5. Turn 6 到 Turn 10 的 Top-3 推荐持续为 `B09WDGKBY7 / B09MKQ84JV / B09W53L858`，用户多次要求更多选项，集合仍基本不变。
6. 最终最佳候选满足 2/2 硬约束，但软偏好命中 0/1，因 `best_candidate_below_acceptance_threshold` 失败。

### 根因判断

传统 fallback parser 没有基于当前 `ask_attribute=brand` 解析任意品牌回答，也没有通用品牌抽取。Agent 虽然生成了问题，却没有把问题上下文用于理解下一句答案。之后“更多选项”没有触发分页、去重或多样性机制，导致对话停滞。

### 给算法同学的行动项

1. 把上一轮 `ask_attribute` 作为下一轮解析的强上下文：问 brand 后，`Adoretex` 即使不在展示的三个选项内，也应解析成品牌约束。
2. 不要把展示的三个 option 当作封闭枚举；真实用户会给出 option 外答案。
3. 对 `REQUEST_MORE_OPTIONS` 增加结果游标、已展示集合去重和多样性重排。

## 8. 可疑成功案例：检索成功不等于对话完成

场景：TechJam `public_0001`。第一轮目标商品位于推荐第 7 名，因此按官方 Hit@10 合法计为成功；但同一条 Agent 响应还在问 `Which brand do you prefer?`，模拟器立即接受并结束。

这种情况在 TechJam 出现 157 次，在 realistic 出现 96 次。当前执行顺序是先检查推荐是否满足目标，再决定用户要不要回答 Agent 的问题。因此：

- 对 TechJam，Hit@10 指标本身仍有效。
- 对 realistic，0.97 success rate 很可能高估了真实对话完成度。
- 后续应同时报告 `retrieval_hit`、`need_satisfied` 和 `conversation_completed`，不要用一个 success 字段混合三种含义。

## 9. 修复优先级和下一轮测试门槛

### P0：理解层

- 修复否定词作用域。
- 利用上一轮 `ask_attribute` 解析自由文本答案。
- 为上述两个真实失败案例增加固定回归测试。

### P1：交互与评测语义

- realistic 模式中，Agent 明确提问时应优先回答问题；除非 Agent 同时明确给出可接受的最终选择提示，否则不要立即结束会话。
- 将 official retrieval metric 与 conversational success 分开。

### P1：问题策略

- 当前 `coverage × normalized entropy` 对高覆盖、高基数的品牌天然有利，导致 300/300 首问品牌。
- 在信息增益中加入问题成本或基数惩罚，并优先测试 use case、style、material、budget 等需求属性；只有存在品牌信号时才优先问品牌。

### P2：推荐多样性

- 用户请求更多选项时，不能重复同一 Top-K；至少记录并排除已展示集合。

下一轮修复后必须重新跑相同 200 + 100 数据，并至少满足：测试与 schema 全通过、API 使用符合所选模式、无 trace/release error、两条真实失败案例不再复现，同时继续单独报告官方 TechJam 指标和 realistic 对话指标。

## 10. 证据入口

- 自动生成的完整逐轮报告：`final_report.md`
- 机器可读分析：`analysis.json`
- 全体问题明细：`comparisons/session_findings.jsonl`
- TechJam 结果与逐会话 journal：`results/techjam.json`、`results/techjam.sessions.jsonl`
- realistic 结果与逐会话 journal：`results/realistic.json`、`results/realistic.sessions.jsonl`
- 每阶段命令、耗时与退出码：`stages.json`
- 运行环境、提交和输入哈希：`00_manifest.json`
- 全部产物哈希：`checksums.sha256`
