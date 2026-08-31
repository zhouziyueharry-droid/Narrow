# Part B 未修复 Bug 对成绩影响分析

**日期 / Date:** 2026-09-01  
**代码分支 / Code branch:** `PartB_impv` (`cff3c07`)  
**对照运行 / Reference run:** LambdaMART + `deepseek-v4-pro`, official 200, run `20260830_211751_+0800`  
**修复后运行 / Fixed run:** LambdaMART + `deepseek-v4-flash`, official 200, 4 workers, run `20260831_235643_+0800`

## 1. 结论 / Conclusion

Part B 修复前的 schema/policy bug **确实会影响评测轨迹**：错误轮次会中断当轮的在线意图解析或对话决策，可能跳过一次状态更新、追问或推荐，并因此影响后续命中轮次、MRR 和 MTTC。

但是，现有记录不能证明这些 bug 单独造成了旧成绩的全部损失。修复前的 9 个异常样本中，8 个样本在后续轮次仍然命中目标，只有 `public_0029` 最终未命中。因此：

- 对最终 Hit@10，按样本最终结果观察，最多只有这 1 个样本（200 条中的 0.5 个百分点）存在直接可见的命中机会；不能声称 9 个错误等于 9 个 miss。
- 对 MRR/MTTC，错误轮次仍可能造成延迟命中或改变状态，所以影响可能存在，但没有同模型、同代码、同请求条件下的反事实重跑，无法给出精确因果增量。
- 修复后的 Flash 结果不能作为严格 A/B 证明，因为同时更换了 LLM（Pro → Flash）、代码和并行运行条件。

## 2. 修复前的实证证据 / Evidence before the fix

来源：`docs/lambdamart_online_pro_report.md` 及其完整 `turns.jsonl`、`sessions.jsonl`。

修复前运行结果：

| 指标 | 未修复 Part B / Pro |
|---|---:|
| Samples | 200 |
| Hit@10 | 0.970 (194/200) |
| MRR | 0.511349 |
| MTTC | 2.295 |
| Technical Score | 0.812505 |
| 异常轮次 | 9 |

9 个异常轮次分为：

| 类型 | 数量 | 具体问题 | 修复方式 |
|---|---:|---|---|
| Intent schema | 2 | `remove_fields` 返回 `field: explanation`，不是纯字段名 | 本地确定性归一化；必要时一次 repair |
| Dialogue policy/schema | 6 | 已知 `material` 仍被重复追问 | 一次受限 dialogue repair |
| Dialogue schema | 1 | `reason` 超过 300 字符 | 本地截断 |

逐样本最终结果：

- `public_0010`, `0022`, `0044`, `0054`, `0109`, `0129`：当轮 dialogue 失败，但后续仍命中。
- `public_0166`, `public_0197`：当轮 intent 失败，但后续仍命中。
- `public_0029`：第 4 轮 dialogue 校验失败，最终未命中；报告同时显示目标在精排中最好为第 24 名，因此不能证明“未命中完全由该 bug 造成”。

这说明旧 runner 会保留错误并继续推进后续轮次，而不是把错误样本全部直接判为失败。错误仍然会改变该轮的有效轨迹：该轮没有正常的决策/状态结果，也没有对应的精排输入。

## 3. 修复后的运行观察 / Observation after the fix

修复后 Flash 四 worker 运行：

| 指标 | Flash + Part B |
|---|---:|
| Hit@10 | 0.965 |
| MRR | 0.522030 |
| MTTC | 2.595 |
| Technical Score | 0.807209 |
| 最终 turn error | 0 |
| Workers | 4 |

与未修复 Pro 运行相比，Hit@10 和 Technical Score 略低，但 MRR 更高、MTTC 更差。这个结果**不能解释为修复导致成绩下降**，因为模型、代码版本和运行并发同时变化；LLM 输出本身也不是严格确定的。

本轮 `llm_calls.jsonl` 没有单独的 `purpose=repair` 字段，因此只能确认最终没有 turn error，不能从日志可靠统计实际触发了多少次 repair 调用。

## 4. 影响判断 / Impact assessment

### 可以确认的影响

1. 错误轮次没有正常产出对应的在线决策，造成轨迹缺口。
2. 意图解析错误可能使约束无法及时进入状态；对话校验错误可能使追问或推荐延迟一个或多个轮次。
3. 因此 MRR、MTTC、逐轮延迟和 token 使用会受到影响，即使最终 Hit@10 没有变化。
4. `public_0029` 是一个可能同时受 schema 错误和排序质量影响的样本，不能只归咎于其中一项。

### 目前不能确认的内容

1. 不能从旧 trace 直接计算“如果当轮修复成功，Technical Score 会增加多少”。
2. 不能把 9 个异常轮次直接换算为 9 个失败会话。
3. 不能用 Flash 修复后成绩与 Pro 未修复成绩做纯粹因果比较。

## 5. 建议的严格验证 / Recommended controlled validation

若要得到可发表的因果结论，应固定以下条件，只改变 Part B 修复开关：

1. 同一 commit 基线、同一 catalog、同一 official 200、同一 LLM model。
2. 使用相同的请求顺序和并发度；最好保存并复用请求快照，减少 LLM 非确定性。
3. 运行 `repair_off` 与 `repair_on` 两组，各至少重复 3 次。
4. 比较 Hit@10、MRR、MTTC、Technical Score、错误轮次数、首命中轮次、每轮 latency 和 token。
5. 对 9 个历史异常样本逐条报告：是否修复、是否恢复精排、是否改变最终命中及首命中轮次。
6. 为 repair 调用增加显式日志字段（例如 `purpose=state_patch_repair` / `dialogue_repair`），避免只能通过总调用数推断。

## 6. 报告完整性 / Reporting integrity

本报告引用的修复前数据和修复后原始 trace 均保留在本地。修复后本轮的 `summary.json` 是旧版 aggregate schema，缺少统一 evaluator 所需的 `evaluation`、`turn_metrics`、`latency`、`model_usage`、`mode_specific_metrics`、`sessions` 顶层字段，因此统一 validator 对该文件返回 schema 不通过；这属于输出格式问题，不应伪称为 validator 通过。

完整修复后运行目录：

`evaluation_runs/parallel_deepseek_v4_flash_partb_official200_20260831/20260831_235643_+0800/`

修复前运行目录：

`evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/`

---

# English summary

The pre-fix Part B bugs did affect evaluation trajectories: a failed online intent or dialogue validation removed the normal result for that turn and could delay state updates, recommendations, and first hit. However, the evidence does not support attributing the entire old score to these bugs. Of the nine affected samples, eight eventually hit the target and one (`public_0029`) missed; therefore the observed direct Hit@10 opportunity is at most one sample (0.5 percentage point), while MRR/MTTC may still have been affected by delayed or altered trajectories.

The post-fix Flash run had zero final turn errors, but it is not a controlled A/B against the old Pro run because the model, code, and execution conditions changed. A controlled same-model repair-on/off experiment with repeated runs and explicit repair-purpose logging is required for a causal estimate.
