# 用户模拟器

日常评测使用工作台；[启动](../demo-frontend/README.md)和[测试与产物](../docs/TESTING.md)是统一操作入口。
本页只说明模拟器职责及直接调用方式。

## 两种协议

用户目标、画像和策略先产生结构化对话动作，再由模板或可选 LLM 转成自然语言。
LLM 只负责用户措辞，不决定目标、状态切换、接受、意图覆盖或约束放宽。

| 模式 | 场景来源 | 成功标准 |
|---|---|---|
| `techjam` | 官方场景与用户画像 | 指定 `parent_asin`，含意图覆盖门控；官方式 Hit@10、MRR、MTTC 和技术分 |
| `realistic` | 从 catalog 确定性生成需求目标 | 硬约束及配置的软约束匹配，报告需求满足成功率 |

TechJam 固定使用模板措辞。Realistic 可选 DeepSeek 措辞，调用失败回退模板并计数；
这与 Agent 在线理解失败不回退本地规则是两个不同边界。
隐藏目标、需求卡和未披露约束始终留在模拟器；两种模式的指标分别报告，不混合计分。

## 开发者直接调用

复用 Agent 的环境，不另建 `user-simulator/.venv`。先按统一测试入口安装依赖，再从仓库根目录执行：

```powershell
uv run --project techjam-conversational-search --extra web --extra ltr --extra deepseek `
  --with-editable user-simulator --group dev --cache-dir .uv-cache `
  python -m user_simulator.cli run --preset techjam `
  --catalog-path techjam-conversational-search/data/catalog.jsonl `
  --sessions-path techjam-conversational-search/data/public_set.jsonl `
  --agent-class shopping_agent.agent:ShoppingAgent --limit 10 `
  --output integration_runs/manual-techjam/result.json `
  --report-output integration_runs/manual-techjam/report.md
```

换成 `--preset realistic` 使用需求模式；同样显式指定另一个输出目录。
上述直接调用使用 Agent 默认精排，工作台选择的 LambdaMART 设置不会影响独立 CLI。
工作台还会传入 `--session-output` 和 `--event-output` 保存流式记录，并用适配层选择精排。
可编辑配置在 [`configs/techjam_benchmark.yaml`](configs/techjam_benchmark.yaml) 和 [`configs/realistic.yaml`](configs/realistic.yaml)。

独立 CLI 未传路径时默认寻找 `data/raw/techjam/`；这不是 final 的商品目录位置，所以示例显式传路径。
不传 `--output` 时写 `runs/techjam.json` 或 `runs/realistic.json`，日常应使用上面的明确输出目录。

## 报告结构

`result.json` 的顶层为 `schema_version`、`mode`、`evaluation`、`turn_metrics`、`latency`、
`model_usage`、`mode_specific_metrics`、`sessions`。
MTTC 未命中按第 11 轮计分，但 `turn_metrics` 单独记录实际执行轮数。
未报告的调用数和未知价格保持 `null`，不会补造费用。`--report-output` 输出对应 Markdown 报告。

## 为什么还保留两份历史基线

[`baseline-techjam-200.md`](docs/results/baseline-techjam-200.md) 和
[`baseline-realistic-100.md`](docs/results/baseline-realistic-100.md) 是历史汇总参考，**不是最新运行，也不需要重新执行**。
[`analyze_evaluation_results.py`](../scripts/analyze_evaluation_results.py) 会实际读取这两个文件并记录 SHA256，
供高级集成审计比较，所以保留原文与原路径；不保留另一套完整历史日志。

早期 `TECHNICAL_SPEC_v0.1.md` 草案已移除，当前行为以本页、代码及测试为准。
原始 Amazon/TechJam 大数据不提交，数据责任见 [DATA_ATTRIBUTION.md](../techjam-conversational-search/DATA_ATTRIBUTION.md)。
