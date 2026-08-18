# Langfuse 自托管集成 + Agent Evaluation

本项目集成了 [Langfuse v4](https://langfuse.com/self-hosting) 自托管可观测性平台,为所有 LLM / LangGraph 工作流提供 **tracing(链路追踪)** 与 **evaluation(质量评估)**。

## 架构

按 [Langfuse 官方自托管架构](https://langfuse.com/self-hosting#architecture),`docker-compose.yml` 内新增 6 个服务:

```
┌────────────────────────── hr-network ──────────────────────────┐
│                                                                 │
│  hr-automation (FastAPI backend)                                │
│    │  langfuse Python SDK v4 (CallbackHandler + scores)         │
│    ▼                                                            │
│  langfuse-web ──────► langfuse-worker (异步事件处理)             │
│    │  web UI: http://localhost:3000                             │
│    ├─► langfuse-postgres   (OLTP, 主数据库)      127.0.0.1:5434 │
│    ├─► langfuse-clickhouse (OLAP, traces/scores) 127.0.0.1:8123 │
│    ├─► langfuse-redis      (队列/缓存)           127.0.0.1:6380 │
│    └─► langfuse-minio      (事件/媒体对象存储)    127.0.0.1:9090 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

- 事件先写入 S3(MinIO)、Redis 仅排队,worker 异步写入 ClickHouse — 抗流量尖峰、可恢复。
- Postgres / ClickHouse 均以 **UTC** 时区运行(官方要求,否则查询结果错误)。
- 通过 `LANGFUSE_INIT_*` 环境变量在首次启动时**自动初始化** org / project / 管理员 / API keys,与 `.env` 中后端使用的 `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` 一致,零手工配置。

## 启动

```bash
docker compose up -d
# 首次启动需等 2–3 分钟(langfuse-web 日志出现 "Ready")

# Langfuse UI:    http://localhost:3000
# 登录账号:       LANGFUSE_INIT_USER_EMAIL / LANGFUSE_INIT_USER_PASSWORD (.env)
```

后端 `/health` 的 `config.langfuse` 字段会显示 `ok` / `unreachable` / `disabled`。

## 被追踪的内容

| Trace 名称 | 来源 | session 分组 |
|---|---|---|
| `cv-extraction` | Graph1:上传 CV → 抽取 → 摘要 (`process_cv_upload`) | `candidate:{email}` |
| `job-evaluation` | Graph2:岗位技能抽取 → 评估 → 打分 (`evaluate_job_against_candidate`) | `job:{job_id}` |
| `hr_explorer` | HR Explorer Deep Agent(侧边栏对话,每轮一个 trace) | AG-UI `thread_id` |

实现方式(langfuse SDK v4):每次调用通过 `RunnableConfig` 注入 `CallbackHandler`
(`backend/core/langfuse_client.py::make_trace_config`),并用保留 metadata key 设置
`langfuse_trace_name` / `langfuse_session_id` / `langfuse_user_id` / `langfuse_tags`。
Graph 内所有节点/LLM/工具调用自动成为子 span。**追踪失败不影响业务**(全部 best-effort)。

## Agent Evaluation(评估)

评估器位于 `backend/services/evaluation/`,分两类:

### 1. 启发式评估器(确定性、零成本,每次运行后自动打分)

| 分数名 | 适用 | 含义 |
|---|---|---|
| `extraction_completeness` | cv-extraction | CV 抽取结构完整度(name/email/experience/education/skills) |
| `summary_quality` | cv-extraction | 摘要非兜底模板、长度合理 |
| `evaluation_plausibility` | job-evaluation | 分数 1-100、tag 与分数档位一致(≥70 high / ≥50 moderate)、reasoning/strengths/gaps 存在 |
| `skills_match_coverage` | job-evaluation | 必需技能匹配率 strong/(strong+missing) |
| `workflow_success` | 两者 | 布尔:工作流无 errors |

在线模式:每次工作流跑完立即通过 `create_score()` 把分数挂到刚创建的 trace 上
(`score_id = trace_id-name` 幂等,重跑覆盖不重复)。

### 2. LLM-as-judge 评估器(默认关闭,按需开启,产生额外 LLM 成本)

- `llm_judge_quality`(job-evaluation):审查候选评估输出本身的质量 —— 打分是否有依据、reasoning 是否 grounded。
- `agent_response_quality`(hr_explorer):审查 Agent 最终回答的帮助性/具体性。

开启方式(任选其一):

- `.env` 中 `LANGFUSE_LLM_JUDGE_ENABLED=true`(全局默认)
- API 调用时传 `use_llm_judge: true`(单次)

### 批量评估 API

```
GET  /api/agent-evaluations/status   # 集成状态 + 评估器注册表
GET  /api/agent-evaluations/traces?limit=50&name=cv-extraction   # 最近 traces(含分数)
POST /api/agent-evaluations/run      # 重放评估器,分数写回 Langfuse
     body: {"limit": 50, "trace_name": null, "use_llm_judge": false}
```

以上均为 `hr_manager` / `admin` 角色。前端「Agent Evals」页面提供相同能力的可视化
(traces 表格 + 一键批量评估)。

## 配置(.env)

```bash
# 后端 SDK
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...        # 与 LANGFUSE_INIT_PROJECT_PUBLIC_KEY 一致
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000  # docker-compose 内自动覆盖为 http://langfuse-web:3000
LANGFUSE_LLM_JUDGE_ENABLED=false

# 服务端(见 .env 注释;生产务必换掉所有 change_me 值)
NEXTAUTH_SECRET / LANGFUSE_SALT / LANGFUSE_ENCRYPTION_KEY = openssl rand -hex
```

未配置 keys 时 tracing 自动禁用,所有 API 返回 503 并提示配置。

## 关键文件

| 文件 | 职责 |
|---|---|
| `docker-compose.yml` (langfuse-* 服务) | 自托管栈 |
| `backend/core/langfuse_client.py` | SDK 客户端、trace config、打分、REST 拉取 traces |
| `backend/services/evaluation/evaluators.py` | 启发式评估器 + 注册表 |
| `backend/services/evaluation/llm_judge.py` | LLM-as-judge 评估器 |
| `backend/services/evaluation/runner.py` | 在线/批量评估编排 |
| `backend/api/routes/agent_evaluations.py` | /api/agent-evaluations/* 路由 |
| `backend/services/hr/automation.py` | Graph1/Graph2 追踪接入点 |
| `backend/services/agent/copilot_runtime.py` | Explorer Agent 追踪接入点 |
| `frontend/src/pages/AgentEvaluationsPage.tsx` | 可视化页面 |
| `tests/test_evaluators.py` | 评估器单元测试 |

## 常见问题

- **生产部署 (`docker-compose.prod.yml`)**:该文件未内置 Langfuse 服务;如需在生产启用,把 `docker-compose.yml` 中 6 个 `langfuse-*` 服务、对应 volumes 一并复制过去即可(网络同为 `hr-network`,`.env` 插值变量通用)。
- **langfuse-web 一直不 Ready**:首次启动要跑数据库迁移,等 2–3 分钟;`docker compose logs langfuse-web` 查看进度。
- **`/health` 显示 unreachable**:确认 `LANGFUSE_HOST` — 宿主机跑后端用 `http://localhost:3000`,容器内由 compose 覆盖为 `http://langfuse-web:3000`。
- **镜像拉取失败**:compose 使用华为云 mirror 前缀;可直接改回 `docker.io/langfuse/langfuse:4` 等官方镜像名。
- **升级**:`docker compose pull langfuse-web langfuse-worker && docker compose up -d`。
