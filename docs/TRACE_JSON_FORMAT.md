# 评测与前端共用的 Trace JSON v1

[测试与产物入口](TESTING.md) · [前端启动](../demo-frontend/README.md)

本文供修改导出器或查看器时参考。Native 的 `scripts/evaluate_with_traces.py` 与
`scripts/evaluate_parallel_with_traces.py` 成功结束后，自动在运行目录生成 **`trace.json`**。
模拟器由工作台接口读取已有结果生成 Trace，不额外写此文件。

## 后续评测的记录约定

默认 `--candidate-limit 0`：完整记录每个阶段的候选列表及排序，不再只记录前 20 个。单进程、并行评测、服务 Trace 接口和一键脚本均采用此默认值。正数上限仅用于显式要求的截断调试，会打印警告；`run_config.json` 记录 `candidate_capture=full/limited`。

完整候选保存在原始 `node_traces.jsonl`，导出器逐行提取目标商品在完整候选池中的排名、分数和是否存在，写入紧凑的前端 `trace.json`。因此前端可以显示第 21 名、第 500 名之后的真实排名，而不必加载全部商品明细。旧运行缺失的数据仍标记未知，不伪造补齐。

## 使用

1. 在工作台运行历史打开该次运行的 Trace；或从[产物目录](TESTING.md)找到 Native 的 `trace.json`。
2. 手动导入时打开 Trace 前端，点击顶部 **选择 Trace JSON**。
3. 选择文件，即可查看评分、样本、对话、目标在各阶段的排名与节点更新摘要。

文件只在浏览器本地读取，不会上传；无需复制到 `public`、启动模型或重新请求 LLM。前端兼容原有 `diagnostics.json`、BGE 快照诊断文件和 `?data=<public 内文件名>.json` 入口。文件损坏或格式不支持会显示提示，并保留当前已经打开的结果。

工作台深链使用 `?runId=...&session=...&turn=...` 从本机 API 读取已保存证据；它不重跑检索或排序。
模拟器缺失官方逐轮门控时不推断精确流失原因。Realistic 使用已接受或最后推荐的商品作观察对象，
`diagnosticMode=agent` 与 `successRate` 表示需求模式，不能解读为官方隐藏目标的技术分。

## 旧运行补导出

在 `techjam-conversational-search` 目录执行：

```powershell
.\.venv\Scripts\python.exe scripts/export_trace.py --run-dir "已有运行目录"
```

默认写入该运行目录的 `trace.json`；也可用 `--output "其他路径.json"`。支持单进程日志、完成后的聚合日志和中断运行的 shard 日志。完整聚合文件优先，不依赖原机器上的 shard 绝对路径。

`summary.json` 只有评分，`results.json` 通常不含节点日志，不能凭空转换成完整 Trace；补导出需要 `run_config.json`、`sessions.jsonl`、`turns.jsonl` 和节点日志（或对应的 shards）。

## 格式约定

```json
{
  "schema": "shopping-agent.trace",
  "schemaVersion": 1,
  "run": {
    "id": "20260830_120828_+0800",
    "model": "deepseek-v4-pro",
    "workers": 6,
    "sampleCount": 200,
    "expectedSampleCount": 200,
    "partial": false,
    "snapshotMode": true,
    "hitRate": 0.955,
    "mrr": 0.460115,
    "mttc": 2.68,
    "technicalScore": 0.781934,
    "diagnosisCounts": {"hit": 191, "unknown": 9}
  },
  "sessions": ["此处为样本对象，结构见下表"]
}
```

上面只是结构示意（diagnosisCounts 非实测诊断分布），不要把此示例当成可导入的完整评测文件。

| 层级 | 主要字段 |
|---|---|
| `sessions[]` | `sampleId`、`scenario`、`hit`、`firstHitTurn`、`bestRank`、`target`、`diagnosis`、`diagnosisReason`、`turns` |
| `turns[]` | `turn`、`userMessage`、`agentMessage`、`recommendedAsins`、`semanticQuery`、`constraints`、`evaluationActive`、`latencyMs`、`error`、`stages`、`nodeTrace` |
| `stages[]` | 按 lexical / dense / attribute / fusion / filter / rerank / response 排列；包含 `count`、`targetRank`、`status`、`snapshotLimit`、`signal` |
| `nodeTrace[]` | `names`、`step`、`createdAt`、`updates`；保留全部已记录节点，候选池更新精简为目标商品证据，避免嵌入整个商品池 |

- `status=present`：目标在已保存的快照内，`targetRank` 是快照中的实际排名。
- `status=absent`：已保存完整候选池且没有目标。
- `status=unknown`：快照不足或该阶段未执行，不能判断目标是否存在。
- checkpoint 更新是差量；导出器按样本和轮次恢复未变化的状态，失败轮次不会冒用上一轮未执行阶段的候选。
- 新粗排可能在融合内部过滤，因此“粗排融合”阶段缺失目标不直接归因于 RRF 截断。
- 部分运行只对已完成会话计算指标，并显式标注 `partial` 与未完成数量。
- `nodeTrace` 是展示用摘要。全量原始候选快照继续留在 `node_traces.jsonl`，不通过前端文件扩散 API 配置或本机路径。
- 前端拒绝未知协议版本、损坏 JSON、重复样本和错误嵌套结构；最大文件为 100 MB。

导出实现：`techjam-conversational-search/evaluator/trace_export.py`。前端类型和校验：`trace-visualizer/lib/trace.ts`。无版本字段的旧 diagnostics 按旧结构兼容。
