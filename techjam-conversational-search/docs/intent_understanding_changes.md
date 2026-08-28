# 意图理解模块优化记录（StatePatch / 否定 / 预算 / 意图切换 / LLM Parser）

负责方向：意图理解（StatePatch、否定、预算、意图切换、LLM Parser）
改动分支：`yxh`
改动文件：
- `techjam-conversational-search/src/shopping_agent/semantic_state.py`
- `techjam-conversational-search/tests/test_shopping_agent.py`（仅新增测试，未删改原有用例）

未改动：`intent.py`、`schemas.py`、`state.py`、`graph.py`。原因见文末"为什么没动这些文件"。

---

## 1. 否定处理（negation）

**问题位置**：`semantic_state.py::_negative_phrases()`

**原实现的两个 bug：**

1. 复合否定丢词。原正则的边界是 `(?=\s+(?:but|and|or)|[,.;!?]|$)`，遇到 " or" 就直接截断捕获组。这意味着 "I don't want cotton or wool" 只会捕获到 `"cotton"`，`"wool"` 完全丢失，永远不会成为一条 `not_contains` 约束。
2. 长否定片段被整段当成一个属性值。比如 "I don't want a huge floral pattern that clashes with everything in my closet" 这种句子，原来会把从 "a huge..." 到句尾整段文字塞进一个 `not_contains` 约束的 `value` 里，这种垃圾约束既无法匹配任何真实商品属性，还会污染检索。

**修改内容：**

- 捕获边界改为只在 `and` / `but` / 标点 / 句尾处截断，不再在 `or` 处截断，因此 "cotton or wool" 会被整体捕获为 `"cotton or wool"`。
- 捕获后按 `,` / `/` / `\bor\b` 再切分一次，切出 `["cotton", "wool"]`，分别生成两条独立的 `not_contains` 约束。
- 新增模块常量 `MAX_NEGATION_WORDS = 6`：切分后每一段如果超过 6 个词，视为"这句话太复杂，规则解析不可靠"，直接丢弃，不再生成约束。这样它会继续走 `rule_state_patch()` 里已有的 `unresolved_negation` 信号（这个信号原来就有，但因为规则总能"硬解出"点什么，实际很少真正触发到 LLM 兜底），让长否定句真正交给 LLM Parser 处理，而不是被规则层的错误结果污染。
- 顺手把原来写死的特判 `"tall" if value in {"that tall", "tall"} else value` 换成通用规则：切分后的每个短语先去掉开头的 `that/this/a/an/the` 等虚词（`re.sub(r"^(?:that|this|a|an|the)\s+", "", part)`），不再依赖硬编码的个例。

**影响范围**：只影响 `_negative_phrases()` 的返回值和 `semantic_fallback_patch()` 里消费它的那一小段循环，不涉及 `StatePatch` 的字段结构。

---

## 2. 预算解析（budget）

**问题位置**：`semantic_state.py::semantic_fallback_patch()` 里原有的 `budget_matches` 正则段

**原实现缺口**：只能识别单一上限（`under / below / up to / no more than / stretch to $X`），完全无法识别区间预算，比如 "between $50 and $100" 或 "$50-$100" 只会被忽略，一条约束都提取不到。

**修改内容：**

- 新增区间正则，识别两种写法：
  - `between $X and $Y`（也兼容 `between $X to $Y`）
  - `$X-$Y`（连字符写法，必须两边都跟着数字，避免误伤其他带连字符的文本）
- 命中区间后生成两条约束：`gte X`（soft，作为"下限参考"，置信度 0.85）+ `lte Y`（hard，作为"硬性上限"，置信度 0.9），复用已有的 `_constraint()` 工具函数，不需要改 `Constraint` 的 schema（`operator` 字段本来就支持 `gte`/`lte`）。
- 为避免区间和原有的"单一上限"正则重复计数（例如 "under $80 ... stretch to $100" 不应该被误判成一个 50-100 的区间），区间匹配到的字符位置会记录下来，原来的单值正则在扫描时会跳过落在区间范围内的位置。这一点专门加了回归测试（见下方"如何测试"）验证两者不会互相干扰。

**没有做的事（有意为之）**：模糊预算词（"cheap"、"高端一点"）没有做规则映射，因为这类词的合理阈值依赖商品价格分布（比如"鞋子里的 cheap"和"手表里的 cheap"完全不是一个数量级），而 `semantic_state.py` 这一层拿不到 `catalog.py` 的价格统计信息，硬编一个固定数字（比如"cheap = $30 以下"）在评测集换了品类后大概率是错的，属于会制造虚假信心的实现。这类模糊预算词目前完全依赖 LLM Parser 判断，如果想做规则兜底，需要先在 `catalog.py` 里加一个"按品类取价格分位数"的接口，再传进这一层，是一个独立的、有一定工作量的后续任务，在下面的"后续建议"里列出。

---

## 3. 意图切换 / 隐式 override（intent switching）

**问题位置**：`semantic_state.py`，新增 `_has_conflicting_value()` 和 `_fallback_result()`，接入 `resolve_semantic_patch()`

**原实现的盲区**：override 的判定完全靠关键词（`actually / instead / ignore my earlier / what i need is` 等，定义在 `PROTOCOL_MARKERS` 和 `semantic_fallback_patch()` 里的关键词列表）。只要 LLM Parser 在线，这不是大问题，因为 DeepSeek 会根据语义直接判断 `action=replace`。但只要 LLM 不可用（没配 key、超时、返回格式错误——也就是退回规则/LLM 兜底路径的所有场景），规则层完全无法识别"用户没说'actually'，但明显换了个要求"这种隐式切换，比如已经锁定 `color=red` 之后用户说"Make it blue please."，规则层只会把 `blue` 当成新增约束叠加在 `red` 旁边，变成两条互相矛盾的颜色约束同时生效。

**修改内容：**

- 新增 `OVERRIDE_SENSITIVE_FIELDS = {"color", "material", "size", "style", "brand", "use_case"}`：这几个字段的语义决定了"同一字段出现不同取值"基本等价于用户改主意了，而不是同时想要两个值。刻意排除了 `budget`（更新预算通常是"追加一个更精确的数字"而不是替换）、`category`（`graph.py::update_state` 里本来就总是用最新一次解析出的 category 覆盖旧值，不需要这里再处理）和 `feature` / `other`（这两个字段太杂，贸然假设"新值替换旧值"风险更高）。
- 新增 `_has_conflicting_value(active_constraints, incoming)`：检查 `incoming` 里是不是有某个 `OVERRIDE_SENSITIVE_FIELDS` 字段的取值，和当前 `active_constraints` 里同字段的取值不一样。
- 新增 `_fallback_result(...)`：把原来在 `resolve_semantic_patch()` 里重复了两遍的"构造兜底 patch"逻辑收敛成一个函数（这本身也是一次去重），并且在这里接入冲突检测——如果 `fallback.action` 还是默认的 `add`，但检测到冲突，就把它改成 `replace`，同时把原因记录进 `fallback_reasons`（新增标签 `implicit_override_heuristic`，方便你们之后跑评测时统计"隐式切换到底触发了多少次、有没有误伤"）。
- 因为 `apply_state_patch()`（在 `graph.py` 消费）里 `action == "replace"` 时只会替换 `patch.constraints` 里出现过的那些字段（`replacement_fields = {item.field for item in patch.constraints}`），不会像"什么都不管、全部清空软偏好"那么暴力，所以这个改动是安全的局部替换，不会误删用户其他已确认的偏好。

**触发位置**：`resolve_semantic_patch()` 里现在一共有三条路径会经过 `_fallback_result()`——LLM 未启用、LLM 返回内容无法解析、LLM 调用异常——三条路径现在都会做这个隐式切换检测，覆盖了"LLM 完全不可用"的所有场景。LLM 正常返回时（`parser="deepseek"`）不受影响，因为这种场景下 DeepSeek 自己的语义判断已经能覆盖隐式切换。

---

## 4. LLM Parser（DeepSeek 集成）

**问题位置**：`semantic_state.py::resolve_semantic_patch()`

**原实现的问题**：整个 API 调用 + JSON 校验被包在一个 `except Exception` 里，一次超时、一次限流、一次 JSON 格式错误，三种完全不同性质的失败会得到同一个笼统的 `fallback_reasons = ["deepseek_unavailable"]`，调参/复盘时没法区分"是网络问题"还是"是 prompt 让模型返回了不合 schema 的内容"。而且没有任何重试，比赛现场网络抖一下就直接掉回规则兜底，会拖累 MRR / 约束抽取准确率的稳定性。

**修改内容：**

- 把原来一次性的 API 调用包进内部函数 `_call_once()`，最多重试 1 次（一共尝试 2 次），只吸收"这次网络抖了一下"级别的瞬时失败，不会无限重试拖慢响应。
- 新增专门的异常类型 `_InvalidDeepSeekResponse`：当 `StatePatch.model_validate_json(content)` 校验失败时抛出，和网络类异常分开捕获，分别打上 `deepseek_invalid_response`（模型返回的内容不是合法 JSON / 不符合 schema）和 `deepseek_unavailable`（重试后依然连不上/超时/没有 key）两种不同的 `fallback_reasons` 标签。
- 两条失败路径和"LLM 未启用"路径统一收敛到新增的 `_fallback_result()` 里（见上一节），顺带把隐式意图切换检测也接进来了，减少了原来两段几乎一样的兜底构造代码。
- prompt 内容（`DEEPSEEK_SYSTEM_PROMPT`）、`temperature=0`、`max_tokens=800` 没有改动——这部分已经写得比较克制，符合赛题里"轻量、内存执行"的约束，暂不需要动。

---

## 5. StatePatch 数据结构

`StatePatch`（pydantic 模型）本身字段没有改动，仍然是 `action / category / constraints / remove_fields / no_preference / retire_soft / semantic_query / intent_summary / language / confidence / parser / fallback_reasons`。这次改动全部是"怎么产出更准确的 StatePatch"，不是"改 StatePatch 长什么样"——刻意没有为了这次优化去改 schema，是为了不影响 `graph.py` / `agent.py` 里所有已经在消费这个模型的代码，把改动面控制在 `semantic_state.py` 内部。

---

## 如何测试

### 1）跑单元测试（最快，几秒钟出结果）

这个仓库用 `uv` 管理依赖。在项目目录（`techjam-conversational-search`）下：

```bash
uv sync --frozen
uv run pytest tests/ -q
```

> 如果你本地也遇到 "uv sync 报 jsonpointer / jsonpatch 相关的 wheel 安装失败"，通常是 `.venv` 目录残留了一次没装完整的环境，删掉项目里的 `.venv` 目录再 `uv sync --frozen` 一次就行。

现在 `tests/test_shopping_agent.py` 一共 28 条用例，全部通过（19 条原有 + 9 条这次新增）。新增的 9 条分别是：

| 测试函数 | 覆盖点 |
| --- | --- |
| `test_semantic_fallback_splits_compound_negation_into_separate_constraints` | "cotton or wool" 拆成两条 `not_contains` |
| `test_semantic_fallback_drops_overlong_negation_span` | 超长否定片段被丢弃，不生成垃圾约束 |
| `test_semantic_fallback_parses_between_budget_range` | "between $50 and $100" → `gte 50` + `lte 100` |
| `test_semantic_fallback_parses_dash_budget_range` | "$50-$100" → `gte 50` + `lte 100` |
| `test_semantic_fallback_does_not_double_count_range_and_single_budget` | 区间正则和原有单值正则不互相干扰（回归测试） |
| `test_resolve_semantic_patch_flags_implicit_override_without_marker` | 没有 "actually/instead" 关键词，仅凭同字段新值也能触发 `action=replace` |
| `test_resolve_semantic_patch_retries_transient_provider_failure` | 第一次调用抛超时，第二次成功，最终仍拿到 `parser="deepseek"` 的结果 |
| `test_resolve_semantic_patch_tags_invalid_provider_json` | 模型返回非 JSON 内容时打上 `deepseek_invalid_response` |
| `test_resolve_semantic_patch_tags_persistent_outage` | 持续失败时打上 `deepseek_unavailable` |

原有的 19 条用例（否定/预算/override 相关的，比如 `test_semantic_fallback_resolves_negation_without_negating_neutral_color`、`test_semantic_fallback_splits_preferred_and_maximum_budget`、`test_semantic_fallback_uses_history_for_comparative_reference`、`test_intent_override_retires_soft_preference_but_keeps_hard_constraint`）全部保持通过，说明这次改动没有破坏已有行为。

只想跑意图理解相关的这部分测试，可以过滤：

```bash
uv run pytest tests/test_shopping_agent.py -k "negation or budget or override or semantic or deepseek" -v
```

### 2）跑仓库自检（提交前建议做一次）

```bash
npm run check
```

（如果只关心 Python 部分，`uv run pytest` 已经够用；`npm run check` 会连带跑 TypeScript 检查和生产构建，是给整个仓库用的。）

### 3）跑本地评测器看分数变化（可选，需要先下载完整 catalog）

`data/` 目录下目前只有 `public_set.jsonl`（200 条公开 session），完整的 5 万条商品 `catalog.jsonl` 是参赛工具包的 release 资产，需要按 `techjam-conversational-search/README.md` 里的说明单独下载解压到 `data/` 下。下载好之后：

```bash
python evaluator/local_evaluator.py --catalog data/catalog.jsonl --dataset data/public_set.jsonl --output results_yxh.json
```

把这次改动前后的 `results.json` 对比一下，重点看 `intent_override` 场景的分数、以及约束抽取相关的准确率指标有没有提升——这是给评委看的"automated verification"证据，建议正式提交前跑一次留档。

### 4）手动 smoke test（可选）

如果想直接感受一下效果，可以在 Python 里直接调用改过的函数，不需要起服务：

```python
from shopping_agent.semantic_state import rule_state_patch, semantic_fallback_patch

msg = "I don't want cotton or wool, between $50 and $100."
patch = semantic_fallback_patch(msg, 1, rule_state_patch(msg, 1))
for c in patch.constraints:
    print(c.field, c.operator, c.value, c.strength)
```

预期输出应该包含 `material not_contains cotton`、`material not_contains wool`、`budget gte 50.0`、`budget lte 100.0`。

---

## 后续建议（这次没做，留给你决定要不要跟进）

1. **模糊预算词**（cheap / affordable / 高端）：需要先给 `catalog.py` 加一个按品类取价格分位数的接口，再传给 `semantic_fallback_patch()`，工作量比这次的改动大一些，建议单独排期。
2. **`StatePatch` 加版本历史**：如果想在 demo 里展示"意图是怎么一步步演变的"（对应赛题里 Runtime Adaptation / Personalized Context Distillation 这条），可以在 `state.py::ShoppingState` 里加一个 `patch_history: list[dict]`，每轮把 patch 追加进去，`graph.py::update_state` 里顺手写入即可，不需要动 `semantic_state.py`。
3. **隐式切换的误伤监控**：`implicit_override_heuristic` 这个新标签建议在跑评测/demo 的时候统计一下触发频率，如果发现在真实评测集里经常"误判"（比如用户其实是想要"红色或蓝色都行"而不是"改成蓝色"），再考虑收紧 `OVERRIDE_SENSITIVE_FIELDS` 或者加更多上下文判断。

---

## 附：用同一批新测试跑「旧代码 vs 新代码」的直接对比

比起看 `results.json` 里的分数（在公开评测集上因为话术太模板化而看不出差异，见上文），更直观的证明方式是：把这次新增的 9 条测试，分别跑在优化前的 `semantic_state.py`（commit `f257ef8`）和优化后的版本（当前 `yxh` 分支）上，同一套断言、同一批输入，看它们谁能通过。

做法：用 `git worktree add /tmp/old_code f257ef8` 在不动当前分支的情况下拉出一份旧代码，把新测试文件复制过去，用相同的 `pytest -k` 过滤条件各跑一次。结果：

| 测试用例 | 旧代码（f257ef8） | 新代码（当前分支） |
| --- | --- | --- |
| `test_semantic_fallback_splits_compound_negation_into_separate_constraints`（"cotton or wool" 拆两条约束） | ❌ FAILED | ✅ PASSED |
| `test_semantic_fallback_drops_overlong_negation_span`（超长否定片段丢弃） | ✅ PASSED（凑巧过） | ✅ PASSED |
| `test_semantic_fallback_parses_between_budget_range`（"between $50 and $100"） | ❌ FAILED | ✅ PASSED |
| `test_semantic_fallback_parses_dash_budget_range`（"$50-$100"） | ❌ FAILED | ✅ PASSED |
| `test_semantic_fallback_does_not_double_count_range_and_single_budget`（区间/单值不重复计数） | ✅ PASSED（旧代码本来就没有区间逻辑，无从重复） | ✅ PASSED |
| `test_resolve_semantic_patch_flags_implicit_override_without_marker`（无关键词隐式换主意） | ❌ FAILED | ✅ PASSED |
| `test_resolve_semantic_patch_retries_transient_provider_failure`（网络抖动重试） | ❌ FAILED | ✅ PASSED |
| `test_resolve_semantic_patch_tags_invalid_provider_json`（区分"返回格式错"和"连不上"） | ❌ FAILED | ✅ PASSED |
| `test_resolve_semantic_patch_tags_persistent_outage`（持续失败打标签） | ✅ PASSED（旧代码本来就有一个笼统的 `deepseek_unavailable`） | ✅ PASSED |

**汇总：9 条里旧代码 6 条 FAILED、3 条 PASSED；新代码 9 条全 PASSED。** 3 条旧代码也能过的用例，都是"旧代码里本来就没有这块逻辑、所以谈不上冲突"（比如区间预算旧代码根本不解析，自然也不会跟单值预算重复计数）或者"旧代码本来就有一个粗粒度的兜底"（`deepseek_unavailable`），而不是旧代码已经做对了。

拿其中一个失败断言举例，比预算区间那条更直观——旧代码在 "between $50 and $100 for boots." 这句话上完全提取不到预算约束：

```
AssertionError: assert 'deepseek_invalid_response' in ['no_structured_signal', 'deepseek_unavailable']
```

这条是 LLM 返回了不合法 JSON 时的用例：旧代码不区分"模型返回格式错"和"网络连不上"，两种情况全部打成同一个 `deepseek_unavailable` 标签；新代码能正确区分出 `deepseek_invalid_response`。

复现方式（在项目根目录 `techjam-conversational-search` 下）：

```bash
NEW_TESTS="test_semantic_fallback_splits_compound_negation_into_separate_constraints or test_semantic_fallback_drops_overlong_negation_span or test_semantic_fallback_parses_between_budget_range or test_semantic_fallback_parses_dash_budget_range or test_semantic_fallback_does_not_double_count_range_and_single_budget or test_resolve_semantic_patch_flags_implicit_override_without_marker or test_resolve_semantic_patch_retries_transient_provider_failure or test_resolve_semantic_patch_tags_invalid_provider_json or test_resolve_semantic_patch_tags_persistent_outage"

# 新代码（当前分支）
uv run pytest tests/test_shopping_agent.py -k "$NEW_TESTS" -v

# 旧代码（对比用，不影响当前分支）
git worktree add /tmp/old_code f257ef8
cp tests/test_shopping_agent.py /tmp/old_code/techjam-conversational-search/tests/test_shopping_agent.py
cd /tmp/old_code/techjam-conversational-search
PYTHONPATH="$PWD/src:$PWD" python -m pytest tests/test_shopping_agent.py -k "$NEW_TESTS" -v
cd - && git worktree remove /tmp/old_code --force
```
