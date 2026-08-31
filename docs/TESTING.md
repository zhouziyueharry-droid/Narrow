# 测试与产物

[返回项目首页](../README.md) · [启动前端](../demo-frontend/README.md)

本文是测试的统一入口。以下路径和 PowerShell 命令均以**仓库根目录**为起点。

| 目的 | 怎么做 | 去哪里看 |
|---|---|---|
| 检查代码是否正常 | 下方「代码测试」 | 终端通过/失败，`test_results/` |
| 测试 Agent 的购物效果 | 工作台的评测页 | 工作台运行历史，`demo_runs/<运行 ID>/` |
| 查看保留的最新正式结果 | 工作台运行历史中的只读归档 | 下方「最新正式归档」 |

代码测试不产生 Hit@10；业务评测才会运行购物会话并计算相应指标。只查看归档或运行本地测试不会产生模型费用。

## 代码测试

需要 Python 3.12、uv、Node.js 22.13 或更高的兼容版本。首次安装依赖；已经通过启动脚本安装过则跳过：

```powershell
uv sync --project techjam-conversational-search --extra web --extra ltr --extra deepseek --group dev --cache-dir .uv-cache
npm --prefix demo-frontend ci --cache .npm-cache --no-audit --no-fund
npm --prefix trace-visualizer ci --cache .npm-cache --no-audit --no-fund
```

按顺序执行下面三项。它们使用测试数据和受控模型响应，不需要真实 catalog 或 API 密钥，不发起付费评测。
每次覆盖同名报告，只保留最近一次代码测试结果；任何一项失败都要先查看对应报告。

```powershell
New-Item -ItemType Directory -Force test_results | Out-Null

# 后端（含 HTTP 适配）与模拟器，复用同一个 Python 环境
.\run_local_python.ps1 -m pytest -c pyproject.toml tests ../user-simulator/tests `
  -o "pythonpath=. src ../user-simulator/src" -q -p no:cacheprovider `
  --basetemp .pytest-run-regression --junitxml=../test_results/python.xml

# Vue 页面与交互
npm --prefix demo-frontend test -- --reporter=default --reporter=junit --outputFile=../test_results/frontend.xml

# Trace 文件格式与异常输入
node --experimental-strip-types --test --test-reporter=tap `
  --test-reporter-destination=test_results/trace.tap `
  trace-visualizer/scripts/tests/trace-format.test.mjs
```

| 报告 | 内容 |
|---|---|
| `test_results/python.xml` | 后端与模拟器的测试用例、失败详情，JUnit XML |
| `test_results/frontend.xml` | Vue 测试结果，JUnit XML |
| `test_results/trace.tap` | Trace 格式测试结果，TAP 文本 |

修改前端后再检查构建，不需要启动 API：

```powershell
npm --prefix demo-frontend run build
npm --prefix trace-visualizer run build
```

构建输出分别在两个前端目录的 `dist/`；它们是应用构建文件，不是评测报告。

## 业务评测：从前端发起

1. 按[前端启动说明](../demo-frontend/README.md)启动，打开工作台的评测页。
2. 选择模式、样本数、provider 和精排。初次验证可用本地模式、1 条样本；需要 LambdaMART 时显式选择。
3. 点击运行，在运行历史查看进度、汇总、会话和 Trace。失败时先看该运行的 `worker.log`。

| 模式 | 实际执行入口 | 结果含义 |
|---|---|---|
| Native | `techjam-conversational-search/scripts/evaluate_with_traces.py` | 现有官方公开集评测器，指定商品命中与技术分 |
| TechJam | `user_simulator.cli run --preset techjam` | 模拟器按官方协议计算指定商品命中与技术分 |
| Realistic | `user_simulator.cli run --preset realistic` | 基于需求约束的成功率；不是官方技术分，不能混算 |

默认本地 provider 和模板用户措辞不调用付费模型。选择 DeepSeek provider 或 Realistic 的 DeepSeek 用户措辞会调用外部 API。
三种模式的样本上限分别为 200 / 200 / 100；同一服务同时只运行一个评测。

## 前端评测产物：`demo_runs/`

运行 ID 采用 `<模式>_<随机 ID>`，与运行历史条目对应；`job.json` 记录创建时间、配置、状态和进度。
新运行不会覆盖正式归档，退出或重启前端也不会自动删除结果。

```text
demo_runs/
  server-logs/                         启动脚本的三个服务日志
  native_<ID>/
    job.json                          运行配置与状态
    worker.log                        评测进程输出与错误
    evaluation/
      LATEST.txt                      本次任务实际结果目录
      <时间戳>/
        summary.json                  先看：汇总分数
        report.md                     先看：可读评测报告
        trace.json                    导入 Trace 查看器
        sessions.jsonl                逐会话结果
        turns.jsonl                   逐轮对话、推荐和耗时
        node_traces.jsonl             全量节点与候选快照
        run_config.json               数据与执行配置
  simulator-techjam_<ID>/              Realistic 同样结构，前缀不同
    job.json
    worker.log
    result.json                       汇总与会话明细
    report.md                         可读评测报告
    sessions.jsonl                    逐会话流式结果
    events.jsonl                      逐轮事件与已保存快照
```

Native 使用 LambdaMART 时还会记录精排与 LLM 调用审计文件，具体以该次运行配置为准。
模拟器 Trace 由接口根据已有结果生成，**不额外保存 `trace.json`，也不重跑排序**；
缺失的官方逐轮门控或不完整快照标记为未知。Realistic 的观察商品不是官方隐藏目标。
字段解释见 [Trace 格式](TRACE_JSON_FORMAT.md)。

## 最新正式归档（只读）

指针：[evaluation_runs/LATEST.txt](../techjam-conversational-search/evaluation_runs/LATEST.txt)。
其中路径相对于 `techjam-conversational-search/`，当前固定指向：

```text
techjam-conversational-search/evaluation_runs/
  lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/
```

| 想看什么 | 文件 |
|---|---|
| 分数、异常、六条未命中的解释 | [在线评测报告](../techjam-conversational-search/docs/lambdamart_online_pro_report.md) |
| 归档文件清单与解压方法 | [归档 README](../techjam-conversational-search/evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/README.md) |
| 当次评测器生成的原始报告 | [归档 report.md](../techjam-conversational-search/evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/report.md) |
| 可视化 | 归档内 `trace.json`，或直接从工作台运行历史打开 Trace |
| 原始证据 | `sessions.jsonl`、`turns.jsonl` 与三个 `*.jsonl.gz` |
| 完整性 | `artifact_manifest.json` 的 SHA256 与 `trace_audit.json` |

这是已完成的 LambdaMART + Pro 官方公开集 200 条归档（194 条命中、453 轮）。
界面禁止删除；不要直接在原目录重写报告或解压后提交大文件。需要重新审计时先复制到本地临时目录。
其他旧完整运行已从 final 清理，可在 Git 历史中查阅。

## 需要命令行批量评测时

下列命令会跑完整公开集、调用 DeepSeek API 并产生费用；不是代码测试。先配置 Agent 目录的 `.env` 与 catalog。
显式使用新的输出根目录，避免改写正式归档的 `LATEST.txt`：

```powershell
.\run_local_python.ps1 scripts/evaluate_parallel_with_traces.py `
  --model deepseek-v4-pro --workers 4 --candidate-limit 0 `
  --ltr-ranker lambdamart --ltr-model-dir models/lambdamart_synthetic_2000 `
  --output-root evaluation_runs/manual_pro
```

结果位于 `techjam-conversational-search/evaluation_runs/manual_pro/<时间戳>/`；
该目录自己的 `LATEST.txt` 指向新运行。CLI 结果不自动登记到工作台，直接导入其 `trace.json` 查看。
`--candidate-limit 0` 保存完整候选证据；截断后缺失的目标不能被当作确定未召回。

仓库还保留高级工具 `scripts/run_test_trace_frontend.ps1` 与 `scripts/run_integration_audit.ps1`，仅用于旧工作流兼容。
前者不带 `-TestsOnly` 时默认执行付费评测；后者输出到 `integration_runs/`。日常操作使用本文和工作台即可。
模拟器的两份历史基线仍被分析脚本读取，详见[用途说明](../user-simulator/README.md)，不代表最新结果。
