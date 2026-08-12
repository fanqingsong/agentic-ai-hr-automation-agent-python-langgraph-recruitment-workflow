# HR Explorer Agent (DeepAgents + CopilotSidebar)

Read-only free-exploration assistant over MongoDB, Qdrant, and Neo4j. HR managers and admins use the right-hand CopilotKit sidebar on authenticated dashboard pages.

## Architecture

```
Frontend (Vite React)
  Layout / ProtectedRoute
    └─ CopilotKit (runtimeUrl=/api/copilotkit, agent=hr_explorer)
         └─ CopilotSidebar + useCopilotReadable page context

Backend (FastAPI)
  JWT middleware on /api/copilotkit (hr_manager | admin)
  AG-UI endpoint → LangGraphAGUIAgent → create_deep_agent graph
    └─ read-only tools → mongo_query / vector_index / graph_query
```

The coordinator agent may call tools directly or delegate to subagents:

| Subagent | Focus |
|----------|--------|
| `candidate_researcher` | Candidate profiles, semantic CV search, graph neighborhood |
| `job_researcher` | Job posts, JD semantic search, skill requirements |
| `matching_analyst` | Evaluations and candidate–job skill comparison |

Session memory uses in-process `MemorySaver` (lost on process restart).

## Tools (read-only)

| Tool | Store | Purpose |
|------|--------|---------|
| `lookup_candidate` | MongoDB | Truncated candidate profile |
| `lookup_job` | MongoDB | Truncated job summary |
| `list_candidates_filtered` | MongoDB | Name / skill substring list |
| `list_jobs_filtered` | MongoDB | Title substring list |
| `get_candidate_job_evaluation` | MongoDB | Evaluation records |
| `semantic_search_candidates` | Qdrant | CV chunk semantic recall |
| `semantic_search_jobs` | Qdrant | JD chunk semantic recall |
| `find_candidates_by_skill` | Neo4j | Candidates linked to a skill |
| `find_jobs_by_skill` | Neo4j | Jobs requiring a skill |
| `explore_candidate_graph` | Neo4j | Candidate neighborhood |
| `compare_candidate_job_skills` | Neo4j | Shared / missing skills |
| `find_shared_company_candidates` | Neo4j | Same-company peers |

All responses are truncated JSON-friendly summaries. Write operations (`insert` / `update` / `index_*`) are not exposed. Filesystem middleware is limited to `read_file`, `ls`, `glob`, `grep`.

## Auth and roles

- Endpoint base: `/api/copilotkit`
- Multi-route surface (Vite-compatible, no Node CopilotRuntime BFF):
  - `GET|POST /api/copilotkit/info` — agent discovery (fixes CopilotKit `runtime_info_fetch_failed`)
  - `POST /api/copilotkit/agent/hr_explorer/run` — AG-UI SSE run
  - `POST /api/copilotkit/agent/hr_explorer/connect` — connect stub
  - `POST /api/copilotkit/agent/hr_explorer/stop/{threadId}` — stop stub
  - `POST /api/copilotkit` — legacy direct AG-UI run
- Header: `Authorization: Bearer <access_token>`
- Allowed roles: `hr_manager`, `admin`
- `job_seeker` does not get the Copilot provider or sidebar

Vite proxies `/api` to the backend with a long timeout for AG-UI streams.

Frontend must set `useSingleEndpoint={false}` on the v1 `<CopilotKit>` provider (its default is single-route, which POSTs `{method:"info"}` to the AG-UI run path and used to 422). The root `POST /api/copilotkit` also accepts single-route envelopes as a fallback.

## Environment

Reuses existing LLM and knowledge-store settings (no separate agent API key):

- `LLM_PROVIDER` / provider-specific model keys — explorer model
- `EMBEDDING_*`, `QDRANT_*`, `NEO4J_*`, `MONGODB_URL` — tool backends

Health check includes `"agent": "configured" | "unavailable"`.

## Frontend wiring

- Provider: `frontend/src/components/copilot/HrCopilot.tsx` (`HrCopilotProvider`)
- Mounted in `ProtectedRoute` around `Layout`
- Page context via `CopilotPageContext` on Candidates, Candidate detail, Jobs, Job detail
- Tool calls render as expandable cards (`useDefaultTool`)

## Acceptance scenarios

| User question | Expected tool chain |
|---------------|---------------------|
| “找有 FastAPI 经验、做过支付系统的人” | `semantic_search_candidates` → `lookup_candidate` → optional `explore_candidate_graph` |
| “这个岗位缺哪些技能、谁最接近” | `lookup_job` + skill / compare tools + `get_candidate_job_evaluation` |
| “没有写 Kubernetes 但相关的候选人” | Qdrant semantic → Neo4j/Mongo cross-check → cite evidence |
| “和 Alice 同公司背景、又会 Python 的人” | shared-company / explore graph → `find_candidates_by_skill` |

## Out of scope (v1)

- Triggering evaluation, job creation, or CV upload
- Skill alias resolution (e.g. K8s = Kubernetes) as a graph feature
- Writing agent output back into scoring formulas
- Full-screen agent page
- Durable checkpointer across restarts

## Key files

| Path | Role |
|------|------|
| `backend/services/knowledge/mongo_query.py` | Mongo read helpers |
| `backend/services/knowledge/graph_query.py` | Neo4j read helpers |
| `backend/services/agent/tools.py` | Agent tools |
| `backend/services/agent/hr_explorer_agent.py` | `create_deep_agent` factory |
| `backend/services/agent/copilot_runtime.py` | CopilotKit `/info` + AG-UI multi-route mount |
| `backend/main.py` | Runtime mount + JWT middleware |
| `frontend/src/components/copilot/HrCopilot.tsx` | CopilotKit UI shell |
