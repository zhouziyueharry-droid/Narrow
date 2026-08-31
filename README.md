# 对话式购物搜索

`final` 基于 `codex/lambdamart-reranker@0635afa`，接入 `demo@3cabe276` 的前端。
包含购物聊天、三种业务评测和 Trace 查看器。默认本地模式与 Precise 精排；LambdaMART 在设置页显式选择。

## 日常只看这三个入口

| 想做什么 | 入口 |
|---|---|
| 了解项目、找文档 | 当前 README |
| 启动前端、聊天、配置模型 | [前端启动](demo-frontend/README.md) |
| 跑测试、跑评测、找结果文件 | [测试与产物](docs/TESTING.md) |

准备好商品数据后，在仓库根目录启动：

```powershell
.\scripts\run_demo.ps1
```

打开 [购物工作台](http://127.0.0.1:5173)。首次安装、数据路径和故障排查见前端启动文档。
查看已有结果无需调用模型；主动选择 DeepSeek 后的连接测试、聊天和评测会产生 API 费用。

## 文件放在哪里

| 路径（相对仓库根目录） | 用途 |
|---|---|
| `demo-frontend/` | Vue 购物工作台 |
| `techjam-conversational-search/` | Agent、评测器、测试、数据与冻结模型 |
| `user-simulator/` | TechJam / Realistic 模拟用户 |
| `trace-visualizer/` | Trace 查看器 |
| `demo_runs/` | 前端发起的新评测与启动日志，本地生成、不提交 |
| `test_results/` | 代码测试报告，本地生成、不提交 |

最新正式归档是 [20260830_211751_+0800](techjam-conversational-search/evaluation_runs/lambdamart_online_pro_200/lambdamart/20260830_211751_+0800/README.md)：
LambdaMART + DeepSeek Pro，官方公开集 200 条，Hit@10 97.0%。这是既有结果，不代表本轮重新跑分或私有榜单表现。

## 需要改代码时再看

- [后端开发与参考文档](techjam-conversational-search/README.md)：架构、接口、排序、模型训练、比赛规则和数据来源。
- [模拟器说明](user-simulator/README.md)：两种协议、命令行和历史基线的用途。
- [Trace 格式](docs/TRACE_JSON_FORMAT.md)：字段、完整快照与未知状态。

旧交接记录、重复启动/测试手册、早期规格草案和旧整合报告已清理；可从 Git 基线提交 `0635afa` 查阅。
模型来源、数据归属、接口约定和脚本依赖的基线保留在上述参考入口中，不作为日常操作手册。
