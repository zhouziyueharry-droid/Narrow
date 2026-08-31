# 队友 B：DeepSeek 会话可靠性 —— 受限 Schema 修复重试

分支：`PartB_impv`（基于 `testing`）。本文说明本次改动的具体内容、依据，以及新增测试的覆盖范围与运行方法。

## 一、问题来源

依据 [最新在线评测报告](lambdamart_online_pro_report.md) 中的记录：

> 9个异常轮次：2次需求解析失败、7次对话输出校验失败。它们保留在评测中，无离线兜底，也未筛掉重跑。

本次改动直接从这次运行（`evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/`）的 `llm_calls.jsonl` 和 `turns.jsonl` 中还原了这 9 条轮次的原始请求/响应，逐条核对了失败原因，而不是凭猜测处理。核对方式：从 `turns.jsonl` 里筛出 `error` 字段非空的行定位到具体的 `sample_id`/`turn`，再用 `sample_id`+`turn`+`purpose` 到 `llm_calls.jsonl` 里取出模型当时的原始返回内容。

### 9 条异常轮次的实际归类

| 类型 | 样本/轮次 | 具体原因 |
|---|---|---|
| 需求解析失败（intent schema） | `public_0166` 第4轮 | `remove_fields` 返回了 `"feature:Rain"`、`"style:Women's-specific last"`，不是 schema 要求的纯字段名 |
| 需求解析失败（intent schema） | `public_0197` 第4轮 | `remove_fields` 返回了 5 条 `"feature: watch band link remover"` 这类"字段名: 说明文字"格式 |
| 对话输出校验失败（dialogue schema） | `public_0010`/`0022`/`0044`/`0054`/`0109`/`0129` 各第1轮 | 用户已经把 `material` 说成"fabric"（软约束、已记录），模型仍然又追问了一次 `material`，触发"不能问已知属性"规则 |
| 对话输出校验失败（dialogue schema） | `public_0029` 第4轮 | `reason` 字段返回 308 个字符，超过 schema 里 300 字符的上限 |

两类失败此前都是"一次不通过就直接终止"，没有任何修复尝试，也没有离线兜底——这是既有的设计（`resolve_semantic_patch`/`decide_dialogue` 失败后直接抛 `RuntimeError`，不会退回 `rule_state_patch`/`choose_question`），本次改动延续了"绝不静默兜底"这一点，只是在"终止之前"补上了一次有限的修复机会。

## 二、具体改动

### 1. `src/shopping_agent/infrastructure/llm/deepseek.py`

- `DeepSeekInvalidResponse` 新增 `kind` 属性，取值 `"intent"` 或 `"dialogue"`，明确标出这次校验失败属于"意图理解"还是"对话策略"哪一侧的 schema，调用方和测试可以直接按这个属性分支，而不是解析 `RuntimeError` 的错误文案字符串。
- `request_state_patch`、`request_dialogue_decision` 各增加**一次**受限的修复重试：模型第一次返回的内容如果解析/校验失败，就把原始请求里完全相同的 system prompt、加上模型刚才那次的原始回复、再加一句固定的修复指令（"这条回复未通过 schema 校验，原因是……；只返回修正后的 JSON，保留所有已经正确的字段，不要加任何解释"）重新发一次，只重试一次，不循环，也不改动任何原有的行为提示词。
  - 如果模型第一次连内容都没返回（比如空 `choices`），说明没有可修的文本，直接判定失败，不浪费这次重试机会。
- 新增 `repair_dialogue_decision`：专门给 `decision.py` 里"JSON 格式合法、但触发了对话策略规则"的情况（追问已知/已声明无偏好的属性、`message` 为空等）做修复重试，因为这类校验只有 `decision.py` 才有上下文（已知属性、已声明无偏好的属性集合）。

### 2. `src/shopping_agent/understanding/state_patch.py`

- 新增 `normalize_raw_state_patch`：不调用模型、纯本地地把 `remove_fields`/`no_preference` 里"字段名: 说明文字"这种格式，按冒号切开取前半段、去空白、转小写，对照合法的 Attribute 集合做匹配；能匹配上就保留纯字段名，匹配不上就丢弃（不去猜测）。这个函数正好能把 `public_0166`、`public_0197` 这两条真实失败样本在**不发起任何 API 调用**的情况下修好，属于确定性最强、成本最低的修复方式，优先于上面的模型修复重试使用。
- **修复了一个真实 bug**：`apply_state_patch` 里，当 `action="replace"` 时，原逻辑会把所有涉及到的字段的旧约束**先整体标记为"已覆盖"（superseded），再把模型新返回的约束加回去**——如果模型在 `replace` 时把没有变化的字段原样又输出了一遍（例如 `public_0096` 第3轮，用户说"忽略我之前的偏好"，模型把没变的 `category`、`feature` 也一起重新吐了出来，只有 `material` 是真正新增的），这些没变的约束就会被错误地记进"覆盖历史"，即便它们从未真正离开过生效状态。修复后：只有真正被替换成不同取值的约束才会被记为"已覆盖"，值没变的约束保持原样、不计入覆盖历史。这是在核对"override / no preference / full reset"这项任务时发现的。

### 3. `src/shopping_agent/dialogue/decision.py`

- 新增 `_truncate_text_fields`：在做 pydantic 校验之前，把 `message`（上限 1000 字符）、`reason`（上限 300 字符）按 schema 限制本地截断，做法与 `state_patch.py` 里已有的 `semantic_query`/`intent_summary` 截断逻辑保持一致。`reason` 只是内部日志用的机读理由、不会展示给用户，截断不影响用户体验；`public_0029` 那条 308 字符的失败样本靠这一步本地就能修好，不需要额外调模型。
- 新增 `_validate_dialogue_decision`：把"schema 校验"和"不能追问已知/已声明无偏好的属性""`message` 不能为空"这两条业务规则合并成一个统一的校验函数，返回 `(decision, None)` 或 `(None, 错误信息)`，不抛异常。
- `decide_dialogue` 改为：先校验一次；不通过就调用 `repair_dialogue_decision` 做**唯一一次**修复重试，再校验一次；还不通过就明确抛出 `DeepSeekInvalidResponse(kind="dialogue")`，外层照旧包装成 `RuntimeError("Online dialogue failed ...")`，绝不退回到 `choose_question` 这类离线启发式逻辑。

## 三、未改动的部分（刻意保持范围克制）

- 没有改动 `understanding/prompts.py`、`dialogue/prompts.py` 里的行为提示词——任务要求"不要大改 prompt，只处理确定性的 schema 问题"，本次所有修复都是靠本地归一化/截断 + 一次性的"修复指令"重试，没有重写任何业务提示词。
- `state_patch.py` 里 `validate_state_patch` 对"同一取值同时出现 contains 和 not_contains"这种矛盾约束的报错（`Online intent contains contradictory constraints`）没有纳入本次修复范围：这是模型自身的语义矛盾，不是格式问题，9 条真实失败样本里也没有出现这种情况，强行本地修复容易猜错意图，因此保留原有的直接报错行为。

## 四、新增/修改的测试

全部位于 `tests/` 目录，均可离线运行（mock 掉 `openai` 客户端，不产生真实 API 调用/费用）。

| 文件 | 内容 |
|---|---|
| `tests/unit/test_state_patch_schema_repair.py` | `normalize_raw_state_patch` 单元测试；`apply_state_patch` 的 override/no_preference/full_reset 行为验证（含 `public_0096` 场景复现）；12 条 `remove_fields` 归一化的参数化冒烟测试（含 `public_0166`、`public_0197` 真实数据） |
| `tests/unit/test_dialogue_decision_schema_repair.py` | `_truncate_text_fields`、`_validate_dialogue_decision` 单元测试；14 条本地校验结果的参数化冒烟测试（含 6 条"追问已知属性"+ `public_0029` 真实数据）；`decide_dialogue` 端到端修复重试编排测试（成功修复 / 本地截断无需调用模型 / 修复仍失败必须报错且不回退离线逻辑） |
| `tests/unit/test_deepseek_repair_retry.py` | `request_state_patch`/`request_dialogue_decision`/`repair_dialogue_decision` 的重试机制本身：证明只多调用一次、无内容时跳过修复、`kind` 分类正确、修复仍失败时抛出的异常类型与 `kind` |
| `tests/integration/test_demo_session_continuity.py` | 验证同一进程内、同一个 `runtime.agent` 实例跨多轮请求保持会话状态（约束逐轮累积、两个并发会话互不串扰、删除会话后状态被释放） |
| `tests/regression/test_agent_behavior.py`（新增 2 条） | 修复重试成功时绝不触发本地解析器；修复重试仍失败时依旧报错、`kind == "intent"`，同样绝不触发本地解析器 |

冒烟测试合计约 35 条参数化用例（含全部 9 条真实异常轮次数据 + 若干合成边界场景，如空列表、大小写混用、多字段同时出错、已声明无偏好属性被追问等），满足"每改一次至少对应单测和 10-20 条 smoke test"的要求。

### 运行方法

```bash
cd techjam-conversational-search
uv sync --extra web --extra deepseek --extra ltr --group dev
uv run pytest tests/unit/test_state_patch_schema_repair.py \
              tests/unit/test_dialogue_decision_schema_repair.py \
              tests/unit/test_deepseek_repair_retry.py \
              tests/integration/test_demo_session_continuity.py \
              tests/regression/test_agent_behavior.py -q
```

### 运行结果

本次改动完成后，跑了仓库现有的**全部** 145 条测试（含改动涉及的模块以外的既有测试），全部通过，没有引入回归：

```
145 passed in 2.98s
```

## 五、提交记录

- 分支：`PartB_impv`（基于 `testing` 创建）
- 单个 commit：`Part B: bounded schema repair retry for online DeepSeek turns`
- 涉及文件：4 个源码文件（`decision.py`、`schemas.py`、`deepseek.py`、`state_patch.py`）+ 4 个新测试文件 + 1 个既有测试文件的追加
- 尚未 push 到远程，也未与 `testing`/`main` 合并
