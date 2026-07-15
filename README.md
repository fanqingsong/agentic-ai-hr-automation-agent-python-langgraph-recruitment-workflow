![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)  
![LangChain](https://img.shields.io/badge/LangChain-Framework-blue?logo=python)  
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-blueviolet)  
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG%20Framework-6C5CE7)  
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)  
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-black?logo=openai)  
![Anthropic](https://img.shields.io/badge/Anthropic-Claude-5A67D8)  
![Google Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google)  
![Ollama](https://img.shields.io/badge/Ollama-Qwen-000000)  
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)  
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite)  
![TypeScript](https://img.shields.io/badge/TypeScript-TS-3178C6?logo=typescript)  
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-UI-38B2AC?logo=tailwindcss)  
![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?logo=mongodb)  
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Auth-336791?logo=postgresql)  
![MinIO](https://img.shields.io/badge/MinIO-Storage-000000?logo=minio)

**AI-powered recruitment automation with LangGraph orchestration, LLM reasoning, and enterprise workflow automation.**

## Agentic AI-Powered HR Automation  
Instant CV Intelligence for Modern Hiring Teams  
Python + LangGraph + FastAPI

\> 🚀 Enterprise-grade Agentic AI platform for HR automation, candidate intelligence, and recruitment workflows.

  
For Anyone:  
Interested In Learning Agentic AI for a real-world practical use-case  
  
Automated CV review and candidate evaluation system using LangChain, LangGraph, LlamaIndex, FastAPI.  
By AICampus - Agentic AI Research Community

## 🎯 Features

*   ✅ Automated CV processing to Candidate Review & Evaluation
*   🤖 AI-powered data extraction (personal info, experience, skills, qualifications etc.)
*   📝 200-word professional summaries
*   ⭐ Candidate scoring (1-100) with detailed reasoning
*   📊 Optional Google Sheets logging (configurable)
*   🚀 High-performance FastAPI with async support
*   ⭐ Data Analytics with web-based HR Dashaboard support for management and visualization
*   ⭐ Real-time notifications for HR teams

![Agentic AI HR Automation](https://github.com/user-attachments/assets/93257061-8520-4853-8991-0501a3146e64)  
 

![AI HR Automation - 3](https://github.com/user-attachments/assets/d734715a-d11d-4f3d-86b3-e403624b3933)

  
  
 

## Agentic AI-Powered HR Automation + Web-based HR Dashboard

### 🛠️ Tech Stack

| Category | Tools |
| --- | --- |
| **Agentic AI** | ![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)![LangChain](https://img.shields.io/badge/LangChain-Framework-blue?logo=python)![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-blueviolet)![LlamaIndex](https://img.shields.io/badge/LlamaIndex-RAG%20Framework-6C5CE7) |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)![MongoDB](https://img.shields.io/badge/MongoDB-Data-47A248?logo=mongodb)![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Auth-336791?logo=postgresql)![MinIO](https://img.shields.io/badge/MinIO-Storage-000000?logo=minio) |
| **Frontend** | ![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)![Vite](https://img.shields.io/badge/Vite-Build-646CFF?logo=vite)![TypeScript](https://img.shields.io/badge/TypeScript-TS-3178C6?logo=typescript)![TailwindCSS](https://img.shields.io/badge/TailwindCSS-UI-38B2AC?logo=tailwindcss) |

### 🧠 LLM Providers

![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-black?logo=openai)![Azure OpenAI](https://img.shields.io/badge/Azure-OpenAI-0078D4?logo=microsoft)![Anthropic](https://img.shields.io/badge/Anthropic-Claude-5A67D8)![Ollama](https://img.shields.io/badge/Ollama-Local-000000)

\> Created by **AICampus** - Agentic AI Research Community

### 🔧 Tech Features

*   **LangGraph workflows**: (1) **CV extraction** — upload → extract → summary → save to MongoDB; (2) **Job evaluation** — extract job skills → evaluate candidate → skills match → score decision.
*   AI-based data extraction (personal info, experience, skills) with structured JSON; minimal tokens via compact schemas.
*   **JWT authentication** (PostgreSQL users, roles: job\_seeker, hr\_manager, admin).
*   **MinIO** object storage for CV files; optional local fallback.
*   Multi-LLM: OpenAI, Azure OpenAI, Anthropic Claude, Ollama (Qwen3 etc.).
*   Error handling, timestamped records, health and config endpoints.

### Automation Workflow

**1\. CV extraction workflow** (single CV upload): `upload_cv` → `extract_cv_data` → `generate_summary` → `save_candidate_to_mongodb`.  
**2\. Job evaluation workflow** (score candidate for a job): `extract_job_skills` → `evaluate_candidate` → `skills_match` → `score_decision`.

![AI HR Automation Workflow](https://github.com/user-attachments/assets/d6c6b065-25fc-4832-875c-63d6cb1cb388)  
![AI HR Automation - LangGraph](https://github.com/user-attachments/assets/c8699540-8ac4-457a-852d-d166c93d9963)  
 

## 💰 Cost

5,000 tokens × ($0.30 / 1,000,000) = $0.0015 per resume   
 

*   **$0.0015 per candidate** using GPT-4o-mini reasoning model
*   100 candidates ~ $0.15
*   1,000 candidates under $5

![AI HR Automation - OpenAI GPT Usage](https://github.com/user-attachments/assets/c9928905-b0c6-4023-9f5e-20407c9d3f05)  
 

### 📺 Watch the Video

![Watch the video](https://github.com/user-attachments/assets/ddeea993-8645-4ee2-a184-50bc629a5029)

  
 

## 🚀 Quick Start

### 1\. Clone & Install

```plaintext
# Clone the repository
git clone <your-repo-url>
cd agentic-ai-hr-automation-agent-python-langgraph-recruitment-workflow

# Install dependencies (uv: 10–100x faster than pip, handles LangGraph nested deps)
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version

# Install Python deps from pyproject.toml (.venv created automatically)
uv sync

# Configure environment
cp env.example .env
# Edit .env: LLM keys, MongoDB, PostgreSQL, MinIO, SECRET_KEY, etc.
```

### 2\. Setup & Configure LLM

*   LLM Provider to support multiple LLMs
*   For development/testing, use LLM\_PROVIDER=ollama (free)
*    
    *   Ollama requires 8GB+ RAM for larger models
*   For production, use openai or anthropic based on your needs
*   Claude (anthropic) has better reasoning for complex evaluations
*   OpenAI gpt-4o-mini is faster and cheaper for simple tasks
*   Setup API Keys in .env

### 3\. Infrastructure (MongoDB, PostgreSQL, MinIO)

*   **MongoDB**: Job posts, candidates, evaluations. Set `MONGODB_URL` (e.g. `mongodb://localhost:27017`).
*   **PostgreSQL**: User auth (JWT). Set `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. Run migrations if needed (Alembic).
*   **MinIO**: CV file storage. Set `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`. With Docker Compose, MinIO starts automatically.

Optional: Google Drive/Sheets for logging can be configured separately if you use that integration.

### 4\. Run API Server

```plaintext
# Development (from project root)
uv run uvicorn backend.main:app --reload --port 8000

# Or: python -m backend.main (uses HOST/PORT from .env)
# Production
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5\. Run Frontend (React + Vite)

```plaintext
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 6\. Access Documentation

*   Swagger UI: http://localhost:8000/docs
*   ReDoc: http://localhost:8000/redoc
*   Health: http://localhost:8000/health

## 📖 Usage

### Authentication (`/api/auth`)

*   `POST /api/auth/register` — Register (name, email, password, role: job\_seeker | hr\_manager | admin)
*   `POST /api/auth/token` — Login (OAuth2 form: username=email, password) → JWT
*   `GET /api/auth/me` — Current user (Bearer token)
*   `PUT /api/auth/me` — Update profile
*   Admin: `GET/PUT/DELETE /api/auth/users`, `GET /api/auth/stats/users`

#### Default accounts (默认账号)

| Role | Email | Password |
| --- | --- | --- |
| Admin (superuser) | `admin@hr-automation.com` | `admin123` |
| HR Manager | `hr@hr-automation.com` | `hr123456` |
| Job Seeker | `seeker@hr-automation.com` | `seeker123` |

These three accounts are **created automatically on every application startup** by `backend/core/seed.py` (called from the FastAPI lifespan in `backend/main.py`). Seeding is idempotent:

- If an account is missing, it is created with the password above (using the app's own hashing, so credentials always work).
- If an account exists but the password no longer verifies (e.g. a stale hash), its password is reset to the value above.

**Change these passwords after first login.**

Configuration via environment variables:

- `SEED_DEFAULT_USERS=false` — disable seeding entirely (recommended for production).
- Override credentials: `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`, `SEED_HR_EMAIL` / `SEED_HR_PASSWORD`, `SEED_SEEKER_EMAIL` / `SEED_SEEKER_PASSWORD`.

### Jobs (`/api/jobs`)

*   `GET /api/jobs` — List jobs (optional: `active_only`, `limit`)
*   `GET /api/jobs/{job_id}` — Job detail (supports ObjectId or ULID)
*   `POST /api/jobs` — Create job (HR/Admin; body camelCase for frontend)
*   `PUT /api/jobs/{job_id}` — Update job
*   `GET /api/jobs/{job_id}/candidate-recommendations` — Ranked candidates for job (optional `refresh=true` to re-run evaluation)

### CV & Candidates

*   `POST /api/cv/process` — Upload CV (form: candidate\_name, candidate\_email, cv\_file). Runs **CV extraction workflow** (extract → summary → save to MongoDB). Optional: auth for `user_id`/`user_email`.
*   `GET /api/candidates` — List candidates (HR/Admin; filter by job\_id, score, sort)
*   `GET /api/candidates/{candidate_id}` — Candidate detail

### My Resumes (Job seeker)

*   `GET /api/my-resumes` — List current user's resumes
*   `GET /api/my-resumes/{resume_id}` — Resume detail
*   `GET /api/my-resumes/{resume_id}/download` — Download CV file (MinIO)
*   `GET /api/my-resumes/{resume_id}/job-recommendations` — Job recommendations for this resume (optional `refresh` to re-run **job evaluation workflow**)

### Dashboard & Export

*   `GET /api/dashboard/stats` — Dashboard statistics
*   Export routes for Excel etc. under `/api/export`
*   Batch processing under `/api/batch`

### HR Dashboard – Frontend (React + Vite + TypeScript)

```plaintext
cd frontend &amp;&amp; npm install &amp;&amp; npm run dev
# http://localhost:5173
```

## 🐳 Docker Deployment

Project uses **Docker Compose** (v2: `docker compose`). Services: **MinIO**, **MongoDB**, **Mongo Express**, **PostgreSQL**, **hr-automation** (FastAPI), **frontend** (Vite dev server).

```plaintext
# Build and run (development: hot reload for backend + frontend)
docker compose up -d

# Or use helper scripts
./bin/start-dev.sh          # Dev mode (hot reload)
./bin/start-dev.sh --detach # Background

# View logs
docker compose logs -f

# Stop
docker compose down
```

| Service | Port | Description |
| --- | --- | --- |
| Backend API | 8000 | FastAPI (backend.main:app) |
| Frontend | 5173 | Vite dev server |
| MinIO API | 9000 | Object storage |
| MinIO Console | 9001 | Web UI |
| MongoDB | 27017 | Data |
| Mongo Express | 8081 | MongoDB Web UI |
| PostgreSQL | 5432 | User auth DB |

## 📁 Project Structure

```plaintext
backend/                 # FastAPI app (entry: backend.main:app)
  api/
    auth.py              # JWT auth routes (/api/auth)
    dashboard.py         # Registers dashboard routes
    routes/              # jobs, candidates, cv, my_resumes, dashboard_stats, export, batch
  config.py              # Config (LLM, MinIO, Postgres, MongoDB)
  core/                  # database (Postgres), mongodb, dependencies
  models/, crud/         # User model and CRUD (auth)
  schemas/               # Pydantic schemas (hr, hr_api, auth)
  services/
    hr/                  # automation, data_extraction, batch_processing
    hr/graph/            # LangGraph: cv_extraction_workflow, job_evaluation_workflow
    hr/graph/nodes/      # upload, extract, summary, save, evaluate, skills_match, etc.
  storage.py             # MinIO storage abstraction
frontend/                # React + Vite + TypeScript (port 5173)
bin/                     # start-dev.sh, start-prod.sh, stop-dev.sh
env.example              # Environment template
docker-compose.yml       # MinIO, MongoDB, Mongo Express, Postgres, hr-automation, frontend
```

## 📚 Documentation

See **DOCUMENTATION.md** (if present) for step-by-step setup and configuration.

## Why uv package manager for Python3 projects

*   Speed: 10–100x faster than pip. Solves nested dependencies and version conflict issues for complex architectures like LangGraph
*   Automatic Setup:For most modern workflows, you do not need to create or activate a virtual environment manually.
*   On-Demand Creation: When you run a command like uv run or uv sync in a project directory, uv checks for a virtual environment (typically in a .venv folder). If one doesn't exist, uv will automatically create it and install the required dependencies before executing your command.
*   Automatic Updates: If you add a dependency using uv add , uv updates your pyproject.toml, synchronizes the .venv, and updates the uv.lock file all in one step.

## 🧠 Why OpenAI GPT-4o-mini Is a good option?

*   Structured extraction
*   Deterministic JSON output
*   Fast response time
*   Very low cost
*   HR-grade reasoning quality
*   Scales cleanly for large input tokens

## Why LangChain and LangGraph for Agentic AI

We chose LangChain because its ecosystem offers mature abstractions for prompt handling and tool invocation. Its modular design allowed the team to integrate multiple model providers and build on a standard interface instead of rolling out their own.  
LangChain provides the foundation to focus on what matters the most: safety, scalability, and developer experience.

Its node-and-edge model lets Remote represent complex workflows— ingestion, mapping, execution, validation— as a directed graph. Each step becomes a node with explicit transitions for success, failure, or retry. This makes the agent's state transparent and recoverable, similar to how distributed systems engineers reason about pipelines. LangGraph's focus on long-running, stateful agents was a perfect match for our multi-step migration process.

## Results and impact

By combining LLM reasoning with deterministic code execution, It has turned a manual process into an automated workflow. HR teams no longer need to process large amount of text – they simply plug data into the Code Execution Agent. The agent transforms diverse formats into a consistent JSON schema in seconds instead of days.

Beyond speed, the system has made everything more reliable. The LLM guides the process, but the actual data manipulation happens with trusted Python libraries, completely sidestepping hallucination issues.

## Lessons learned

Building this AI agent taught AICampus several lessons that now inform how its team builds AI systems across different business use-cases:

*   LLMs are planners, not processors. Use them to reason about tasks and choose tools, but offload heavy data processing to code.
*   Validated JSON processing for ingestion. Large intermediate results never pass back to the model, keeping the context small.
*   Structure beats improvisation. Orchestrating workflows as graphs makes them much easier to debug and extend.
*   Context tokens are precious. Large intermediate results should stay in the execution environment where they belong.
*   Python remains the analytics workhorse. Libraries & tools like LangChain and LlamaIndex offer fast, flexible data manipulation that's hard to beat.

## Local Testing

In 2026, context management is critical for agentic HR tasks, as evaluating multiple long-form CVs against a job description can quickly exceed standard 8k or 32k limits. For local testing with Ollama, here is how the top models compare in context capacity as of January 2026.  
Context Window Comparison (2026)

## Model Choice

Building an agentic HR automation system on a local machine requires balancing reasoning depth with the limitations of RAM. You must prioritize smaller, highly efficient models to ensure LangGraph agents can complete multi-step tasks without crashing.  
  
  
Best Model Recommendation for 2026:

For this specific HR evaluation use case on low hardware, DeepSeek-R1-Distill-Qwen-7B or Qwen3-7B-Instruct are the superior choices.

DeepSeek-R1-Distill-Qwen-7B (Primary Choice):  
Reasoning Capability: This is a "reasoning-first" model that uses chain-of-thought (CoT). For HR tasks, it will "think" through a candidate's qualifications before outputting a final score, similar to GPT-4o's internal reasoning.  
  
Fit: A 4-bit quantized version requires approximately 4.5GB to 5GB of memory.  
  
LangGraph Performance: It is highly reliable for the structured output and "decisions" required in LangGraph nodes.  
 

Qwen3-7B-Instruct (Alternative):  
Reasoning Capability: Noted in 2026 as one of the most efficient models for tool-calling and structured data extraction (e.g., parsing a CV into JSON).  
  
Fit: Consumes roughly 4.8GB of memory in its standard 4-bit quantization, making it very fast for local testing on Intel Macs.

Avoid Large Models: Do not attempt to run 14B or 20B models. On small RAM with an Intel processor, these will offload too many layers to system memory, causing tokens-per-second to drop below 1–2, which is unusable for testing agent loops.  
  
Optimize Ollama Context: HR tasks involving long resumes require context. Limit your context window to 16,384 (16k) in your LangGraph configuration to prevent memory saturation on your i9 processor.  
  
LangGraph Integration: Use the Ollama Functions or Tool Calling wrappers in LangGraph. Qwen3-7B is specifically optimized for these "agentic" triggers in the 2026 library updates.  
  
Recommendation: Start with ollama run deepseek-r1:7b. If the "thinking" steps make your agent loops too slow for local testing, switch to ollama run qwen3:7b for faster, direct instruction execution.  
 

## PROMPT GUIDE

The following prompt uses Chain-of-Thought (CoT) and Strict Grounding patterns optimized for reasoning models like OpenAI's GPT-4o.  
Recommended HR System Prompt (2026)

### ROLEadmin@hr-automation.com

You are an Expert Technical Recruiter specializing in high-precision candidate evaluation. Your goal is to provide objective, evidence-based assessments of CVs against specific Job Descriptions (JD).

### GUIDELINES (ANTI-HALLUCINATION)

1.  GROUNDING: Use ONLY the provided CV text. Do not infer skills, companies, or dates that are not explicitly stated.
2.  HONESTY: If a required skill from the JD is missing or ambiguous in the CV, explicitly state "Missing" or "Insufficient Evidence".
3.  NO GUESSING: Never invent projects or experience to make a candidate seem like a better fit. If you are unsure, rate your confidence as "Low" for that specific skill.
4.  REASONING: Always perform a step-by-step analysis before providing a final score.

### EVALUATION PROCESS

Step 1: Extract core technical skills explicitly mentioned in the CV.  
Step 2: Cross-reference extracted skills against the JD's 'Required' and 'Preferred' sections.  
Step 3: Analyze "Years of Experience" for each skill. Calculate total relevant experience manually.  
Step 4: Identify gaps where the CV fails to meet JD requirements.  
Step 5: Provide a final Evaluation Score (0-100) and a justification summary.

Why this works for your setup:  
 

*   Chain-of-Thought (CoT): By forcing the model to list reasoning\_steps first, you utilize the model’s limited reasoning capacity more effectively, reducing the likelihood of a "lazy" or incorrect final score.
*   Structured Schema: LLLM models in 2026 are highly trained on JSON outputs. Using a clear JSON structure ensures your LangGraph nodes can parse the results programmatically without error.
*   Confidence Scoring: Including a "Missing Skills" section forces the model to look for negatives, which counteracts the natural tendency of LLMs to be "agreeable" and over-rate candidates.

## AI-Powered HR Automation with LangGraph

## Complete CV Review to Candidate Evaluation System

\> Developed By AICampus | Gateway for future AI research & learning