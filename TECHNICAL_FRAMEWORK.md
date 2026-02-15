# Technical Framework Documentation
## AI-Powered HR Automation Platform

**Version:** 1.0.0
**Last Updated:** 2025-02-15
**Developed By:** AICampus - Agentic AI Research Community

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Technology Stack](#technology-stack)
4. [System Architecture](#system-architecture)
5. [Component Design](#component-design)
6. [Data Models](#data-models)
7. [API Specification](#api-specification)
8. [Workflow Design](#workflow-design)
9. [External Integrations](#external-integrations)
10. [Security Considerations](#security-considerations)
11. [Deployment Architecture](#deployment-architecture)
12. [Performance & Cost Optimization](#performance--cost-optimization)
13. [Extensibility Points](#extensibility-points)

---

## System Overview

### Purpose
Enterprise-grade Agentic AI platform for HR automation that transforms manual recruitment processes into an intelligent, automated workflow. The system processes CV submissions, extracts candidate information, evaluates against job descriptions, and triggers multi-channel notifications.

### Core Capabilities
- **Automated CV Processing**: PDF resume parsing using LlamaIndex
- **Intelligent Data Extraction**: Structured JSON output for candidate profiles
- **AI-Powered Evaluation**: Candidate scoring (1-100) with detailed reasoning
- **Multi-LLM Support**: OpenAI, Azure OpenAI, Anthropic, Google Gemini, Ollama
- **Automated Logging**: MongoDB integration for candidate tracking
- **Multi-Channel Notifications**: Telegram, Discord, Slack, WhatsApp
- **RESTful API**: FastAPI-based backend with async support
- **Self-Hosted Storage**: MinIO object storage for CV files
- **Real-time Analytics**: Web-based HR Dashboard (Next.js frontend)

---

## Architecture Principles

### Design Philosophy

1. **Agentic AI First**
   - LangGraph state machine for complex, multi-step workflows
   - LLMs as planners, not processors (reasoning vs execution separation)
   - Structured JSON outputs for reliable data parsing

2. **Modularity**
   - Factory pattern for LLM provider abstraction
   - Plugin-style node architecture for workflow extensions
   - Clear separation of concerns (extraction, evaluation, notification)

3. **Async-First**
   - AsyncMongoClient for non-blocking database operations
   - Async/await throughout the request lifecycle
   - Optimized for concurrent request handling

4. **Cost Efficiency**
   - Minimal context passing between nodes
   - Smaller models for simple tasks (GPT-4o-mini)
   - Local Ollama option for zero-cost processing

5. **Developer Experience**
   - Type-safe with Pydantic models
   - Auto-generated API documentation (Swagger/ReDoc)
   - Comprehensive error handling and validation

---

## Technology Stack

### AI & Automation Layer

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | LangGraph 1.0.6 | State machine-based agentic workflow |
| **Framework** | LangChain 1.2.4 | LLM abstraction and tool integration |
| **Extraction** | LlamaIndex 0.6.90 | Intelligent document parsing |
| **LLM Providers** | OpenAI / Azure OpenAI / Anthropic / Gemini / Ollama | Multi-provider support |

### Backend Layer

| Component | Technology | Version |
|-----------|-----------|---------|
| **API Framework** | FastAPI | 0.128.0 |
| **Runtime** | Python | ≥3.12 |
| **Database** | MongoDB (Async) | 4.16.0 |
| **Server** | Uvicorn + Gunicorn | 0.40.0 / 23.0.0 |
| **Package Manager** | uv | Latest |

### Cloud Services

| Service | Provider | Usage |
|---------|----------|-------|
| **Storage** | MinIO Object Storage | CV file hosting with signed URLs |
| **Database** | MongoDB (Async) | Candidate data storage, evaluation results |
| **Notifications** | Telegram, Discord, Slack, WhatsApp | Multi-channel HR alerts |

### Frontend Layer (Separate Repository)

| Component | Technology |
|-----------|-----------|
| **Framework** | Next.js 16 |
| **Language** | TypeScript |
| **Styling** | TailwindCSS |

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐        │
│  │              │         │              │         │              │        │
│  │ Job Seeker   │         │ HR Manager   │         │   Admin      │        │
│  │ (CV Submit)  │         │ (Create Job) │         │ (Analytics)  │        │
│  │              │         │              │         │              │        │
│  └──────┬───────┘         └──────┬───────┘         └──────┬───────┘        │
│         │                        │                        │                 │
│         └────────────────────────┴────────────────────────┘                 │
│                                  │                                          │
│                          ┌───────▼────────┐                                 │
│                          │  Next.js App   │                                 │
│                          │  (Frontend)    │                                 │
│                          └───────┬────────┘                                 │
└──────────────────────────────────┼─────────────────────────────────────────┘
                                   │ HTTP/REST
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ /api/jobs    │  │/candidate-app│  │  /health     │              │   │
│  │  │              │  │   -submit    │  │              │              │   │
│  │  │ POST         │  │  POST        │  │  GET         │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              CORS Middleware                                 │   │   │
│  │  │              Exception Handlers                              │   │   │
│  │  │              Request Validation (Pydantic)                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────┬──────────────────────────────┘   │
└─────────────────────────────────────────┼───────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AI WORKFLOW LAYER (LangGraph)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       StateGraph Workflow                           │   │
│  │                                                                      │   │
│  │  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │   │
│  │  │   CV    │──▶│ Extract  │──▶│ Job      │──▶│ Summary  │          │   │
│  │  │ Upload  │   │ CV Data  │   │ Skills   │   │ Generate │          │   │
│  │  └─────────┘   └──────────┘   └──────────┘   └──────────┘          │   │
│  │                                                                  │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │   │
│  │  │ Evaluate │──▶│ Skills   │──▶│ Score    │──▶│ Notify   │      │   │
│  │  │ (Retry)  │   │ Match    │   │ Decision │   │ Decision │      │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘      │   │
│  │                                                  │               │   │
│  │                                         ┌────────┴────────┐       │   │
│  │                                         ▼                 ▼       │   │
│  │                                    ┌─────────┐      ┌─────────┐  │   │
│  │                                    │  YES    │      │   NO    │  │   │
│  │                                    │ (Notify)│      │ (End)   │  │   │
│  │                                    └────┬────┘      └────┬────┘  │   │
│  └─────────────────────────────────────────┼─────────────────┼──────┘   │
│                                              │                 │          │
└──────────────────────────────────────────────┼─────────────────┼──────────┘
                                               │                 │
                                               │                 │
              ┌────────────────────────────────┴─────┐   ┌──────┴──────┐
              │           PARALLEL NOTIFICATIONS      │   │    END      │
              ├──────────────┬──────────────┬────────┤   └─────────────┘
              │              │              │        │
              ▼              ▼              ▼        ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Telegram │  │  Slack   │  │ Discord  │
        │          │  │          │  │          │
        └──────────┘  └──────────┘  └──────────┘
              │              │              │
              └──────────────┴──────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   MongoDB    │  │    Google    │  │    Google    │  │    Google    │  │
│  │  (Jobs Data) │  │    Cloud     │  │    Sheets    │  │    Drive     │  │
│  │              │  │   Storage    │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM PROVIDER LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    OpenAI    │  │  Anthropic   │  │    Google    │  │    Ollama    │  │
│  │  GPT-4o-mini │  │   Claude     │  │   Gemini     │  │   Qwen3      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│                         ┌──────────────────┐                                │
│                         │  LLM Factory      │                                │
│                         │  (Factory Pattern)│                               │
│                         └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. LangGraph Workflow Engine

**File:** [src/hr_automation.py:83-139](src/hr_automation.py)

The core state machine orchestrating the entire candidate evaluation pipeline.

#### Workflow Nodes

| Node | Purpose | LLM Used | Output |
|------|---------|----------|--------|
| `upload_cv` | Upload CV to GCS | N/A | `cv_file_url` |
| `extract_cv_data_node` | Parse CV with LlamaIndex | LlamaExtract | `extracted_cv_data` |
| `extract_job_skills_node` | Extract skills from JD | Extraction LLM (t=0.0) | `job_skills` |
| `generate_summary` | Create 200-word summary | Summary LLM (t=0.5) | `summary` |
| `evaluate` | Score candidate 1-100 | Evaluation LLM (t=0.4) | `evaluation` |
| `skills_match_node` | Match skills to JD | Skills Match LLM | `skills_match` |
| `score_decision` | Route based on score | N/A | `notify_hr` flag |
| `fan_out_notifications` | Trigger parallel sends | N/A | Branch to 3 nodes |
| `send_email` | Send notification (Telegram/Discord) | N/A | Notification sent |
| `send_slack` | Post Slack message | N/A | Slack sent |
| `send_whatsapp` | Send WhatsApp message | N/A | WhatsApp sent |

#### Conditional Routing

```python
def route_on_score(state: AgentState) -> str:
    """Route based on evaluation score"""
    if state["evaluation_score"] >= 70:
        return "notify_hr"
    return "end"
```

#### Retry Strategy

```python
retry_once = RetryPolicy(max_attempts=2)
graph.add_node("evaluate", evaluate_candidate_node, retry_policy=retry_once)
```

---

### 2. LLM Provider Factory

**File:** [src/llm_provider.py:36-187](src/llm_provider.py)

Implements Factory pattern for multi-provider LLM support.

#### Supported Providers

| Provider | Default Model | Use Case |
|----------|--------------|----------|
| **OpenAI** | gpt-4o-mini | Production (fast, low cost) |
| **Anthropic** | claude-3-5-sonnet-20241022 | Complex reasoning |
| **Google** | gemini-2.5-pro | Multi-modal tasks |
| **Ollama** | qwen3:8b | Local development (free) |

#### Specialized LLM Creators

```python
# Data extraction (low temperature for determinism)
create_extraction_llm(temperature=0.2, max_tokens=500)

# Summarization (medium temperature for creativity)
create_summary_llm(temperature=0.5, max_tokens=300)

# Evaluation (balanced temperature)
create_evaluation_llm(temperature=0.4, max_tokens=600)

# Job skills extraction (zero temperature for consistency)
create_job_skills_llm(temperature=0.0, max_tokens=600)
```

---

### 3. Configuration Management

**File:** [src/config.py:14-166](src/config.py)

Centralized configuration with validation.

#### Configuration Structure

```python
class Config:
    # LLM Provider
    LLM_PROVIDER: str = "openai" | "azure" | "anthropic" | "gemini" | "ollama"

    # Model-specific settings
    OPENAI_MODEL: str = "gpt-4o-mini"
    AZURE_OPENAI_MODEL: str = "gpt-4o-mini"
    AZURE_OPENAI_ENDPOINT: str = "https://..."
    AZURE_OPENAI_DEPLOYMENT: str = "deployment-name"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    GEMINI_MODEL: str = "gemini-2.5-pro"
    OLLAMA_MODEL: str = "qwen3:8b"

    # Temperature settings
    EXTRACTION_TEMP: float = 0.2
    SUMMARY_TEMP: float = 0.5
    EVALUATION_TEMP: float = 0.4

    # MinIO storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "cv-uploads"
    MINIO_SECURE: bool = False

    # FastAPI settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    DEBUG: bool = False
```

#### Environment Variables

Required environment variables (see [env.example](env.example)):

```bash
# Choose one LLM provider
LLM_PROVIDER=openai|azure|anthropic|gemini|ollama

# Provider-specific API keys
OPENAI_API_KEY=sk-...
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...

# MinIO storage
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=cv-uploads
```

---

### 4. Data Extraction Layer

**File:** [src/data_extraction.py](src/data_extraction.py)

Intelligent CV parsing using LlamaIndex LlamaExtract.

#### Extraction Capabilities

- **Personal Information**: Name, email, phone, location
- **Education**: Degrees, institutions, years
- **Work History**: Companies, titles, durations
- **Technical Skills**: Programming languages, frameworks, tools
- **Online Profiles**: GitHub, LinkedIn URLs

#### Output Schema

```python
class PersonalData(BaseModel):
    fullName: str
    phoneNumber: str
    birthdate: str
    githubUrl: str
    linkedinUrl: str
    city: str

class Qualifications(BaseModel):
    education: list[Education]
    jobHistory: list[JobHistory]
    technicalSkills: list[str]
```

---

### 5. MinIO Storage Integration

**File:** [src/minio_storage.py:27-300](src/minio_storage.py)

Self-hosted S3-compatible object storage service.

#### Services Implemented

| Method | Purpose |
|--------|---------|
| `upload_pdf()` | Upload CVs and generate signed URLs |
| `get_file_url()` | Generate presigned URL for file access |
| `download_file()` | Retrieve files from storage |
| `delete_file()` | Remove files from storage |
| `list_files()` | List files in bucket |

#### Presigned URL Generation

```python
# Generate 24-hour presigned URL for CV access
signed_url = self.client.presigned_get_object(
    bucket_name=self.bucket_name,
    object_name=unique_name,
    expires=timedelta(hours=24)
)
```

#### Upload Service

**File:** [src/upload_service.py:23-230](src/upload_service.py)

Unified CV upload service with LangGraph integration.

```python
class CVUploadService:
    async def upload_cv_file(self, file_path: str, candidate_name: str) -> Dict[str, Any]:
        """Upload local CV file to MinIO"""
        async def upload_cv_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """LangGraph node for uploading CVs"""
```

---

### 6. FastAPI Application

**File:** [src/fastapi_api.py](src/fastapi_api.py)

Async REST API server with Pydantic validation.

#### API Endpoints

| Method | Endpoint | Purpose | Request Body |
|--------|----------|---------|--------------|
| **GET** | `/` | API info | None |
| **GET** | `/health` | Health check | None |
| **GET** | `/api/config` | Get configuration | None |
| **POST** | `/api/jobs` | Create job posting | `HRJobPost` |
| **POST** | `/api/candidate-application-submit` | Submit CV | Form data + file |

#### Middleware

- **CORS**: Configurable for production
- **Exception Handlers**: HTTP, Validation, General
- **Request Validation**: Pydantic models with custom validators

#### Async Lifecycle

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Config.validate()
    logger.info("✅ Configuration validated")
    yield
    # Shutdown
    logger.info("👋 Shutting down")
```

---

## Data Models

### Core State Object

**File:** [src/data_models.py:83-110](src/data_models.py)

```python
class AgentState(TypedDict):
    # ===== INPUT DATA =====
    candidate_name: str                    # Candidate full name
    candidate_email: str                   # Candidate email
    cv_file_path: str                      # Local path to CV
    cv_file_url: str                       # Cloud storage URL

    # ===== PROCESSED DATA =====
    extracted_cv_data: dict                # Structured CV data
    summary: str                           # 200-word professional summary
    job_title: str                         # Position title
    job_description: str                   # Job description (plain text)
    job_description_html: str              # Job description (HTML)
    job_skills: JobSkills                  # Extracted required skills
    hr_email: str                          # HR manager email
    evaluation: dict                       # Candidate evaluation
    skills_match: dict                     # Skill matching analysis
    tag: str                               # Candidate tag
    evaluation_score: int                  # Final score (1-100)

    # ===== NOTIFICATION CONTROL =====
    notification_message: str              # Formatted notification
    notify_hr: bool                        # Whether to notify HR

    # ===== METADATA =====
    timestamp: str                         # Processing timestamp
    errors: list[str]                      # Error collection
    messages: list[AnyMessage]             # LangGraph message history
```

### Pydantic Models

#### Job Skills Schema

```python
class JobSkills(BaseModel):
    tech_skills: List[str]      # Python, SQL, Docker, etc.
    soft_skills: List[str]      # Communication, Leadership, etc.
```

#### Candidate Evaluation Schema

```python
class CandidateEvaluation(BaseModel):
    score: int                   # 1-100
    reasoning: str               # Detailed justification
    strengths: List[str]         # Candidate strengths
    gaps: list[str]              # Missing qualifications
    decision: str                # Hire/No Hire decision
```

#### Skills Match Schema

```python
class SkillsMatch(BaseModel):
    strong: list[str]            # Fully matched skills
    partial: list[str]           # Partially matched
    missing: list[str]           # Not found in CV
```

---

## API Specification

### Request/Response Formats

### 1. Create Job Posting

**Endpoint:** `POST /api/jobs`

**Request Body:**
```json
{
  "hr": {
    "id": "507f1f77bcf86cd799439011",
    "name": "Jane Smith",
    "email": "jane.smith@company.com"
  },
  "jobApplication": {
    "title": "Senior AI Engineer",
    "descriptionHTML": "<p>We are looking for...</p>"
  }
}
```

**Response:**
```json
{
  "success": true,
  "jobId": "507f1f77bcf86cd799439012"
}
```

### 2. Submit Candidate Application

**Endpoint:** `POST /api/candidate-application-submit`

**Request:** `multipart/form-data`
```
jobId: string
name: string
email: string
cv_file: <file>
```

**Response:**
```json
{
  "success": true,
  "message": "Candidate processed successfully",
  "candidateName": "John Doe",
  "candidateEmail": "john.doe@email.com",
  "summary": "Experienced software engineer with 5 years...",
  "score": 85,
  "reasoning": "Strong match in Python, Docker...",
  "cvLink": "https://storage.googleapis.com/...",
  "timestamp": "2025-02-15T10:30:00",
  "errors": []
}
```

### 3. Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-15T10:30:00",
  "service": "AI HR Automation",
  "version": "1.0.0",
  "config": {
    "llm_provider": "openai"
  }
}
```

---

## Workflow Design

### Detailed Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CANDIDATE SUBMISSION                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 1: upload_cv                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  cv_file_path (local file)                                       │
│ Action: Upload to MinIO Object Storage                                  │
│ Output: cv_file_url (signed URL, 24h valid)                             │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 2: extract_cv_data_node                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  cv_file_path                                                    │
│ Action: LlamaIndex LlamaExtract parsing                                 │
│ Output: extracted_cv_data {PersonalData, Qualifications}                │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 3: extract_job_skills_node                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  job_description                                                  │
│ Action: LLM extraction (t=0.0)                                          │
│ Output: job_skills {tech_skills[], soft_skills[]}                       │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 4: generate_summary                                                │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  extracted_cv_data                                               │
│ Action: LLM summarization (t=0.5, max 300 tokens)                       │
│ Output: summary (200-word professional summary)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 5: evaluate (WITH RETRY)                                           │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  extracted_cv_data, job_description, job_skills                   │
│ Action: LLM evaluation (t=0.4)                                          │
│         RetryPolicy: max_attempts=2                                     │
│ Output: evaluation {score, reasoning, strengths, gaps, decision}        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 6: skills_match_node                                               │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  extracted_cv_data.technicalSkills, job_skills                    │
│ Action: Skill matching algorithm                                        │
│ Output: skills_match {strong[], partial[], missing[]}                   │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 7: score_decision                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Input:  evaluation_score                                                │
│ Action: Conditional routing logic                                       │
│         if score >= 70 → notify_hr                                      │
│         else → end                                                      │
│ Output: Route decision                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                         │                    │
              score >= 70 │              score < 70
                         │                    │
                         ▼                    ▼
              ┌──────────────────┐    ┌─────────────┐
              │ fan_out_notifications│   │    END      │
              └────────┬─────────┘    └─────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │send_telegram│  │send_slack│  │send_discord│
   └────┬────┘    └────┬────┘    └────┬────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     SAVE        │
              │   (MongoDB)     │
              └────────┬────────┘
                       │
                       ▼
                  ┌─────────┐
                  │   END   │
                  └─────────┘
```

---

## External Integrations

### MinIO Object Storage

#### 1. MinIO Storage Service

**Purpose:** Self-hosted S3-compatible object storage for uploaded CVs

**Implementation:**
```python
class MinIOStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str, secure: bool = False):
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._ensure_bucket_exists()

    def upload_pdf(self, pdf_bytes: bytes, filename: str, folder: str = "cvs") -> dict:
        """Upload PDF and generate signed URL"""
        import uuid
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'pdf'
        unique_name = f"{folder}/{uuid.uuid4().hex}.{ext}"

        self.upload_file(pdf_bytes, unique_name, "application/pdf")

        # Generate presigned URL (24-hour expiry)
        signed_url = self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=unique_name,
            expires=timedelta(hours=24)
        )

        return {
            "object_name": unique_name,
            "signed_url": signed_url,
            "expires_in_hours": 24
        }
```

**Configuration:**
```python
class Config:
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "cv-uploads")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
```

**Docker Compose Setup:**
```yaml
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"  # API
      - "9001:9001"  # Console
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin123
    volumes:
      - minio_data:/data
```

**Access:**
- MinIO Console: http://localhost:9001 (minioadmin / minioadmin123)
- MinIO API: http://localhost:9000

#### 2. MongoDB Database

**Purpose:** Persistent candidate data storage

**Collection Structure:**
```python
{
    "_id": ObjectId("..."),
    "timestamp": "2026-02-16T10:30:00Z",
    "candidate_name": "John Doe",
    "candidate_email": "john@example.com",
    "job_id": "job_123",
    "job_title": "Senior Python Developer",
    "score": 85,
    "decision": "ACCEPT",
    "summary": "Strong candidate with 5 years experience...",
    "cv_url": "http://localhost:9000/cv-uploads/abc123.pdf",
    "strengths": ["Python", "FastAPI", "MongoDB"],
    "gaps": ["Docker experience limited"],
    "skills_match": {"Python": 95, "FastAPI": 80, "MongoDB": 85},
    "reasoning": "Candidate meets all core requirements...",
    "email_sent": true,
    "application_id": "ulid_abc123"
}
```

**Implementation:**
```python
class AsyncMongoDB:
    async def save_candidate(self, candidate_data: dict) -> str:
        """Save candidate evaluation to MongoDB"""
        result = await self.collection.insert_one(candidate_data)
        return str(result.inserted_id)

    async def get_candidate(self, candidate_id: str) -> Optional[dict]:
        """Retrieve candidate by ID"""
        return await self.collection.find_one({"_id": ObjectId(candidate_id)})
```

---

## Security Considerations

### 1. API Key Management

**Implementation:**
```python
from pydantic import SecretStr

llm_kwargs = {
    "model": model,
    "api_key": SecretStr(api_key)  # Masked in logs
}
```

**Best Practices:**
- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate keys regularly
- Use separate keys for dev/staging/production

### 2. Input Validation

**Pydantic Validators:**
```python
class CandidateSubmittedApplication(BaseModel):
    name: str
    email: EmailStr              # Validated email format
    job_id: str

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v):
        return v.strip()[:100]   # Length limit
```

### 3. File Upload Security

**Implementations:**
- File type validation (PDF only)
- File size limits
- Temporary file cleanup
- Virus scanning (recommended for production)

### 4. CORS Configuration

**Development:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production:** Configure specific allowed origins

### 5. MongoDB Security

**Implementation:**
- Use connection strings with authentication
- Enable TLS/SSL for connections
- Implement network whitelist
- Regular backups

### 6. Google Service Account

**Best Practices:**
- Use principle of least privilege
- Separate service accounts per environment
- Rotate credentials regularly
- Monitor API usage

---

## Deployment Architecture

### Docker Deployment

**File:** [docker-compose.yml](docker-compose.yml)

```yaml
services:
  hr-automation:
    build: .
    container_name: ai-hr-automation-api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_SHEET_ID=${GOOGLE_SHEET_ID}
      - HOST=0.0.0.0
      - PORT=8000
      - WORKERS=4
    volumes:
      - ./google-service-account-credentials.json:/app/...:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - hr-network

networks:
  hr-network:
    driver: bridge
```

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.fastapi_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Deployment Options

#### Option 1: Traditional VPS/Dedicated Server
```bash
# Using Gunicorn with Uvicorn workers
gunicorn src.fastapi_api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

#### Option 2: Cloud Platform (AWS/GCP/Azure)
- **AWS:** ECS Fargate + Application Load Balancer
- **GCP:** Cloud Run + Cloud SQL
- **Azure:** Container Instances + Cosmos DB

#### Option 3: Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hr-automation-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hr-api
  template:
    metadata:
      labels:
        app: hr-api
    spec:
      containers:
      - name: api
        image: ghcr.io/org/hr-automation:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: openai-key
```

### Infrastructure Requirements

**Minimum for Development:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- Database: MongoDB Atlas (M10+)

---

## Performance & Cost Optimization

### Cost Analysis

**Per-Candidate Breakdown:**

| LLM Provider | Model | Cost per 1K tokens | Est. Tokens | Cost per Candidate |
|-------------|-------|-------------------|-------------|-------------------|
| **OpenAI** | gpt-4o-mini | $0.150 / $0.600 | ~5,000 | **$0.0015** |
| **Anthropic** | claude-3-haiku | $0.25 / $1.25 | ~5,000 | $0.003 |
| **Google** | gemini-1.5-flash | $0.075 / $0.15 | ~5,000 | $0.0005 |
| **Ollama** | qwen3:8b | Free | Local | **$0** |

**Scaling Costs:**
- 100 candidates: ~$0.15 (OpenAI)
- 1,000 candidates: ~$1.50 (OpenAI)
- 10,000 candidates: ~$15.00 (OpenAI)

### Optimization Strategies

#### 1. Token Efficiency
```python
# Minimal context passing between nodes
# Only pass extracted data, not full CV text
def reduce_latest(current, new):
    return new  # Replace, don't accumulate
```

#### 2. Model Selection Strategy
```python
# Use smaller models for simple tasks
EXTRACTION_MODEL = "gpt-4o-mini"      # Fast, cheap
EVALUATION_MODEL = "gpt-4o"           # Better reasoning
```

#### 3. Caching
```python
# Cache job skill extractions (same JD for many candidates)
@lru_cache(maxsize=128)
def extract_job_skills_cached(job_description: str):
    return extract_job_skills(job_description)
```

#### 4. Batch Processing
```python
# Process multiple CVs concurrently
async def process_batch(candidates: list):
    tasks = [process_candidate(c) for c in candidates]
    return await asyncio.gather(*tasks)
```

#### 5. Local Development
```python
# Use Ollama for zero-cost development
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
```

### Performance Metrics

**Target SLAs:**
- API Response Time: < 5 seconds (single CV)
- CV Processing: < 30 seconds
- Concurrent Users: 50+ (4 workers)
- Uptime: 99.5%

---

## Extensibility Points

### 1. Adding New LLM Providers

```python
# In llm_provider.py
class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    YOUR_PROVIDER = "your-provider"  # Add here

@staticmethod
def _create_your_provider(model, temperature, max_tokens, api_key, **kwargs):
    """Create your provider's LLM instance"""
    from your_langchain_integration import ChatYourProvider
    return ChatYourProvider(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key
    )
```

### 2. Adding New Workflow Nodes

```python
# In hr_automation.py
def your_custom_node(state: AgentState) -> AgentState:
    """Your custom processing logic"""
    # Process state
    result = do_something(state["input_data"])
    state["new_field"] = result
    return state

# Add to graph
graph.add_node("your_custom_node", your_custom_node)

# Connect to workflow
graph.add_edge("existing_node", "your_custom_node")
```

### 3. Adding New Notification Channels

```python
def send_telegram_notification(state: AgentState) -> AgentState:
    """Send Telegram notification"""
    import requests
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    message = format_notification_message(state)

    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": message}
    )

    return state

# Add to parallel notifications
graph.add_edge("fan_out_notifications", "send_telegram")
```

### 4. Custom Evaluation Logic

```python
# Modify routing logic
def route_on_score(state: AgentState) -> str:
    score = state["evaluation_score"]

    if score >= 90:
        return "notify_hr_priority"
    elif score >= 70:
        return "notify_hr"
    elif score >= 50:
        return "notify_hr_review"
    else:
        return "end"

# Add conditional edges
graph.add_conditional_edges(
    "score_decision",
    route_on_score,
    {
        "notify_hr_priority": "fan_out_notifications_urgent",
        "notify_hr": "fan_out_notifications",
        "notify_hr_review": "mark_for_review",
        "end": END
    }
)
```

### 5. Additional Data Extraction

```python
# Extend LlamaIndex schema
class ExtendedQualifications(BaseModel):
    education: list[Education]
    jobHistory: list[JobHistory]
    technicalSkills: list[str]

    # Add custom fields
    certifications: list[str] = Field(description="Professional certifications")
    languages: list[str] = Field(description="Spoken languages")
    projects: list[str] = Field(description="Notable projects")
```

---

## Appendix

### A. File Structure

```
agentic-ai-hr-automation/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   ├── data_models.py               # Pydantic models & AgentState
│   ├── data_extraction.py           # LlamaIndex CV parsing
│   ├── llm_provider.py              # Multi-provider LLM factory
│   ├── hr_automation.py             # LangGraph workflow
│   ├── minio_storage.py             # MinIO object storage service
│   ├── upload_service.py            # Unified upload service
│   ├── fastapi_api.py               # FastAPI application
│   ├── batch_processing.py          # Batch CV processing
│   ├── data_export.py               # Data export (CSV/Excel)
│   ├── dashboard_api.py             # HR analytics API
│   ├── webhook_integration.py       # Webhook subscriptions
│   ├── extended_notifications.py    # Telegram/Discord notifications
│   └── utils/
│       └── ulid_helper.py           # ULID generation
├── frontend/                        # Next.js app (separate repo)
├── outputs/                         # Generated artifacts
├── logs/                            # Application logs
├── tests/                           # Test suite
├── pyproject.toml                   # uv dependencies
├── uv.lock                          # Locked dependencies
├── Dockerfile                       # Container definition
├── docker-compose.yml               # Multi-container setup (MinIO + MongoDB)
├── env.example                      # Environment template
├── README.md                        # User guide
├── DOCUMENTATION.md                 # Detailed setup guide
└── TECHNICAL_FRAMEWORK.md           # This document
```

### B. Key Dependencies

```toml
[project]
name = "agentic-ai-hr-automation"
requires-python = ">=3.12"

dependencies = [
    # AI/ML
    "langchain>=1.2.4",
    "langgraph>=1.0.6",
    "llama-cloud-services>=0.6.90",

    # LLM Providers
    "openai>=2.15.0",
    "anthropic>=0.76.0",
    "langchain-google-genai>=4.2.0",
    "langchain-openai>=1.1.7",
    "langchain-anthropic>=1.3.1",
    "ollama>=0.6.1",

    # API
    "fastapi>=0.128.0",
    "uvicorn[standard]>=0.40.0",
    "gunicorn>=23.0.0",

    # Database
    "pymongo[srv]>=4.16.0",

    # Storage
    "minio>=7.0.0",

    # Data Export
    "xlsxwriter>=3.0.0",

    # Utilities
    "pydantic>=2.12.5",
    "python-dotenv>=1.2.1",
    "python-multipart>=0.0.21",
    "python-ulid>=3.1.0",
    "beautifulsoup4>=4.14.3",
]
```

### C. Environment Variables Reference

```bash
# ===== LLM PROVIDER CONFIGURATION =====
LLM_PROVIDER=openai|anthropic|gemini|ollama

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Gemini
GEMINI_API_KEY=AI...
GEMINI_MODEL=gemini-2.5-pro

# Ollama (Local)
OLLAMA_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434

# ===== LLM TEMPERATURE SETTINGS =====
EXTRACTION_TEMP=0.2
SUMMARY_TEMP=0.5
EVALUATION_TEMP=0.4

# ===== MINIO OBJECT STORAGE =====
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=cv-uploads
MINIO_SECURE=false

# ===== FASTAPI CONFIGURATION =====
HOST=0.0.0.0
PORT=8000
RELOAD=false
DEBUG=false
WORKERS=4

# ===== DATABASE =====
MONGODB_URL=mongodb://localhost:27017
# or with authentication:
# MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/ai-hr-automation

# ===== OPTIONAL FEATURES =====
ENABLE_SLACK_NOTIFICATIONS=false
ENABLE_WHATSAPP_NOTIFICATIONS=false
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
WHATSAPP_API_KEY=...
```

### D. Troubleshooting

**Issue:** CV extraction fails
- **Solution:** Verify LlamaCloud API key is valid
- **Check:** `LLAMA_CLOUD_API_KEY` in .env

**Issue:** MinIO connection fails
- **Solution:** Verify MinIO is running and accessible
- **Check:** `MINIO_ENDPOINT` and credentials in .env
- **Test:** Access http://localhost:9001 (MinIO Console)

**Issue:** MongoDB connection fails
- **Solution:** Verify MongoDB is running
- **Check:** `MONGODB_URL` in .env
- **Docker:** Ensure MongoDB container is started

**Issue:** High memory usage with Ollama
- **Solution:** Use smaller model (qwen3:7b instead of 14b)
- **Check:** Available RAM

**Issue:** Slow API response
- **Solution:** Increase worker count or use smaller LLM
- **Check:** Uvicorn worker configuration

### E. Support & Resources

- **Documentation:** [DOCUMENTATION.md](DOCUMENTATION.md)
- **Original Source:** https://aicampusmagazines.gumroad.com/l/gscdiq
- **Developer:** Furqan Khan (furqan.cloud.dev@gmail.com)
- **Organization:** AICampus - Agentic AI Research Community

---

**Document Version:** 1.0.0
**Last Modified:** 2025-02-15
**Framework Version:** 1.0.0
