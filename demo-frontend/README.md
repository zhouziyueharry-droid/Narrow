# Shopping Copilot 前端

[返回项目首页](../README.md) · [测试与产物](../docs/TESTING.md)

页面、样式、素材和前端测试来自 `demo@3cabe276` 的 Vue 3 / Vite 应用。
只引入前端，没有合并该分支的 Python Demo API、模拟器修改、依赖配置或历史数据。
当前 HTTP 接口由 final 的[本地适配层](../techjam-conversational-search/src/shopping_agent/web.py)提供。

## 启动

需要 Python 3.12、uv、Node.js 22.13 或更高的兼容版本。先按[数据说明](../techjam-conversational-search/data/README.md)准备
`techjam-conversational-search/data/catalog.jsonl`，从**仓库根目录**运行：

```powershell
.\scripts\run_demo.ps1
```

也可以通过 `-CatalogPath 'C:\path\to\catalog.jsonl'` 显式借用其他工作目录的商品数据，不复制私有 `.env`。
脚本安装所需依赖并启动三个仅监听本机的服务；按 Ctrl+C 停止。
已安装依赖时可传 `-SkipInstall`。日志和新评测保存在被忽略的 `demo_runs/`。
不要用其他 worktree 的 `.env` 覆盖当前配置；新 worktree 不会自动带入 catalog、虚拟环境或密钥。

| 服务 | 地址 |
|---|---|
| Vue 工作台 | http://127.0.0.1:5173 |
| 本地 API | http://127.0.0.1:8000 |
| final Trace 查看器 | http://127.0.0.1:3000 |

手动启动时分别在对应目录执行：

```powershell
# techjam-conversational-search/
uv run --extra web --extra ltr --extra deepseek python -m shopping_agent.web
# demo-frontend/
npm ci --cache .npm-cache
npm run dev
# trace-visualizer/
npm ci --cache .npm-cache
npm run dev
```

## 与 final 的适配

- 首页、双语聊天、三种评测、运行历史、设置页保留队友的布局和交互。
- 聊天调用 `ShoppingAgent.start_session/chat`，商品详情来自后端 catalog，浏览器不下载整份 catalog。
- Native 调用现有 `evaluate_with_traces.py`；TechJam/Realistic 调用现有 `user_simulator.cli`，不修改模拟器或评分规则。
- 默认 provider 为本地，默认精排为 final 原有 `PreciseReranker`。设置页可以显式选择冻结的 `LambdaMART`，用于后续聊天和评测；不训练模型。
- 修改设置会重置内存聊天；同一服务仅允许一个评测任务。聊天在服务重启后不保留，评测记录可恢复。
- 最新 `20260830_211751_+0800` 的 200 条评测自动显示为只读归档，不能从界面删除。新测试不会覆盖它。
- Trace 深链读取当前 run 的记录，不重跑检索或排序。保留 final 的 JSON 格式校验和未知快照状态。
- final 模拟器不记录逐轮官方门控；模拟器 Trace 不推断门控或伪造精确流失结论。Realistic 使用已接受商品（或最后推荐商品）作为观察对象，不冒充官方指定目标。

## DeepSeek 与安全

需要在线模型时，在 Agent 项目的 `.env` 配置 `DEEPSEEK_API_KEY`，再在设置页主动选择 DeepSeek。
连接测试、在线聊天和在线评测会产生 API 费用；安装、构建和本地模式不会调用付费模型。
Base URL 仅从服务端 `DEEPSEEK_BASE_URL` 读取，浏览器不能把密钥改发到别的地址。
密钥不会返回前端；跨站写入请求及非本机 Host 会被拒绝。当前不提供公网部署或 LAN 模式。

## 排查启动问题

| 现象 | 检查 |
|---|---|
| 找不到 catalog | 数据文件是否存在；使用 `-CatalogPath` 指定现有文件 |
| 提示缺少 `.venv` | 首次不要传 `-SkipInstall`，让脚本安装依赖 |
| 页面打不开或服务提前退出 | 查看 `demo_runs/server-logs/<时间戳>-frontend.err.log`、`-api.err.log`、`-trace.err.log`；确认 5173 / 8000 / 3000 没有被其他服务占用 |
| DeepSeek 不可用 | Agent 目录的 `.env` 是否配置密钥；只做本地测试时不需要密钥 |

服务的标准输出保存在同目录的 `*.out.log`。不要把整个日志目录当作评测结果上传。
代码测试、构建命令以及每种评测的结果文件统一见[测试与产物](../docs/TESTING.md)。

导入保留现有 `package-lock.json`；新增 Python 依赖集中在可选 `web` extra。
构建产物位于 `dist/`。构建后 API 也能提供 Vue 静态页面及客户端路由。
