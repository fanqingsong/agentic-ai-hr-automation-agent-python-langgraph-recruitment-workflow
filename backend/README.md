# Backend - Modular Structure

后端按模块化方式组织，便于维护和扩展。

## 目录结构

```
backend/
├── main.py                 # 应用入口：FastAPI app、路由注册、uvicorn
├── config.py               # 全局配置（LLM、MinIO、DB 等）
│
├── core/                   # 核心基础设施
│   ├── database.py         # PostgreSQL 连接、Session、init_db
│   ├── dependencies.py     # 认证依赖（get_current_user、RoleChecker 等）
│   └── mongodb.py          # MongoDB 客户端与 get_mongo_db()
│
├── models/                 # SQLAlchemy 模型
│   └── user.py             # UserModel（认证用户）
│
├── schemas/                # Pydantic 模型（请求/响应、状态）
│   ├── auth.py             # 用户与 Token：UserRole, User, UserCreate, Token...
│   ├── hr.py               # HR/Agent：AgentState, JobSkills, CandidateEvaluation...
│   └── hr_api.py           # HR API 请求/响应：HRJobPost, JobApplication, ProcessingResult...
│
├── api/                    # 路由层
│   ├── auth.py             # 认证相关：/api/auth/register, /token, /me, /users...
│   └── dashboard.py        # Dashboard + HR：/api/dashboard/*, /api/jobs/*, /api/cv/process...
│
├── crud/                   # 数据库读写
│   └── user.py             # 用户 CRUD
│
├── services/               # 业务与外部服务
│   ├── security.py         # 密码哈希、JWT
│   ├── llm_provider.py      # 多 LLM 工厂（OpenAI、Azure、Anthropic、Ollama）
│   ├── storage/
│   │   └── minio_storage.py  # MinIO 存储
│   └── hr/
│       ├── automation.py     # LangGraph 工作流（create_hr_workflow, process_candidate）
│       ├── data_extraction.py # CV 解析（LlamaExtract）
│       ├── skills_match.py    # 技能匹配
│       ├── upload_service.py  # CV 上传
│       ├── batch_processing.py # 批量处理
│       └── data_export.py     # CSV/Excel 导出
│
├── utils/
│   └── ulid_helper.py      # ULID 生成
│
```

## 启动方式

推荐使用模块化入口：

```bash
# 开发
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
uv run python -m backend.main
```

仅保留单一入口：

```bash
uv run uvicorn backend.main:app --reload
```

## 导入约定

- 所有代码请从模块化路径导入，例如：
  - `from backend.core.database import get_db, init_db`
  - `from backend.schemas.auth import User, UserCreate`
  - `from backend.api.auth import router`
  - `from backend.services.hr.automation import process_candidate`
  - `from backend.schemas.hr_api import HRJobPost, JobApplication`
