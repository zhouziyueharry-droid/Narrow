# Shopping Agent 后端

日常使用从[项目首页](../README.md)进入：启动见[前端文档](../demo-frontend/README.md)，测试与结果见[统一测试入口](../docs/TESTING.md)。
本目录需要 Python 3.12；环境安装命令集中在测试/启动文档，不再维护另一套操作流程。

## 当前实现

真实用户接口是 `ShoppingAgent.start_session/chat/get_intent_state`；比赛的 `reset/respond` 由兼容适配层提供。
LangGraph 执行需求理解、三路召回、粗排、精排、对话和输出校验。

- 默认 `PreciseReranker`、本地稠密检索；LambdaMART 必须显式注入或在工作台设置页选择。
- 本地模式不调用 LLM；在线模式的理解或对话调用失败会报错，不会静默切回本地规则。
- `src/shopping_agent/web.py` 是工作台的本机 HTTP 适配层，不替换原有 Agent 或评测规则。
- 模型分数只用于候选排序，不是购买概率；官方隐藏目标不作为运行时输入。

## 按需参考

| 文档 | 什么时候需要 |
|---|---|
| [运行架构](docs/agent_architecture.md) | 理解数据流、在线/离线边界与失败行为 |
| [模块边界](docs/architecture/module_boundaries.md) | 决定代码放在哪里、检查依赖方向 |
| [组件接口](docs/contracts/component_interfaces.md) | 替换召回/精排、调用服务 |
| [粗排说明](docs/coarse_ranking.md) | 修改召回、融合或过滤；含历史实验参考 |
| [Precise 权重历史](../docs/precise_reranker_change_report.md) | 查权重拟合的推导与限制，不是当前操作手册 |
| [LambdaMART 训练](docs/lambdamart_training.md) | 重训、检查样本隔离和特征 |
| [冻结模型说明](models/lambdamart_synthetic_2000/README.md) | 加载模型、核对模型文件 |
| [最新在线评测报告](docs/lambdamart_online_pro_report.md) | 查看当前保留的完整正式结果及限制 |
| [比赛规格](docs/competition_specification.md)、[提交规则](docs/submission_rules.md) | 核对官方协议与交付要求 |
| [数据准备](data/README.md)、[数据归属](DATA_ATTRIBUTION.md) | 准备 catalog、确认数据使用要求 |

机器可读约定：[`agent_api_contract.json`](docs/agent_api_contract.json)、[`evaluation_config.json`](docs/evaluation_config.json)。
`starter/` 与 `docs/baseline_results.json` 是官方弱基线参考，不是 final 的默认实现。

## 显式加载 LambdaMART

在本目录的 Python 环境内：

```python
from shopping_agent.application.service import ShoppingAgent
from shopping_agent.ranking.lambdamart import LambdaMARTReranker

agent = ShoppingAgent(
    "data/catalog.jsonl",
    reranker=LambdaMARTReranker("models/lambdamart_synthetic_2000"),
)
session_id = agent.start_session(user_profile={})
result = agent.chat(session_id, "I need light waterproof shoes")
```

模型文件必须完整同目录保存，见冻结模型说明。前端用户不需要写这段代码。

## LangGraph Studio（开发调试）

完成环境安装后，在本目录执行；这不是购物工作台的启动入口：

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
uv run --extra web --extra ltr --extra deepseek --cache-dir .uv-cache langgraph dev
```

按终端输出打开 Studio。此命令不会自动切换到 LambdaMART；LangSmith 认证与追踪配置按本地环境设置。
