# 快速参考指南 - 新功能

## 📋 目录

1. [功能概览](#功能概览)
2. [快速开始](#快速开始)
3. [API 端点](#api-端点)
4. [代码示例](#代码示例)
5. [配置](#配置)
6. [常见问题](#常见问题)

---

## 功能概览

| 功能 | 文件 | 描述 |
|------|------|------|
| 🔀 **批量处理** | [src/batch_processing.py](src/batch_processing.py) | 并发处理多个简历 |
| 📊 **数据导出** | [src/data_export.py](src/data_export.py) | CSV/Excel 导出 |
| 📈 **Dashboard API** | [src/dashboard_api.py](src/dashboard_api.py) | 分析和统计端点 |
| 🔔 **Webhook** | [src/webhook_integration.py](src/webhook_integration.py) | 事件回调集成 |
| 💬 **扩展通知** | [src/extended_notifications.py](src/extended_notifications.py) | Telegram & Discord |

---

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制并更新 `.env`:

```bash
# Telegram (可选)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Discord (可选)
DISCORD_WEBHOOK_URL=your_webhook_url
```

### 3. 启动 API

```bash
uvicorn src.fastapi_api:app --reload
```

### 4. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API 端点

### Dashboard API

```
GET  /api/dashboard/stats              # 统计概览
GET  /api/candidates                   # 候选人列表 (分页)
GET  /api/candidates/{id}              # 候选人详情
GET  /api/jobs                         # 职位列表
GET  /api/analytics/score-distribution # 分数分布
```

### 批量处理

```
POST /api/batch/process                # 批量处理
POST /api/batch/process-directory      # 目录批量处理
GET  /api/batch/{id}/export            # 导出批结果
```

### 数据导出

```
POST /api/export/candidates            # 导出 (CSV/Excel)
```

---

## 代码示例

### 批量处理简历

```python
from src.batch_processing import process_candidates_batch
from src.fastapi_api import HRJobPost, JobApplication, HRUser

# 准备职位数据
job_app = JobApplication(
    title="Senior AI Engineer",
    description="Job description...",
    description_html=""
)
hr_user = HRUser(id="1", name="HR", email="hr@company.com")
job_post = HRJobPost(
    id=1,
    ulid="job_001",
    job_application=job_app,
    hr=hr_user
)

# 准备候选人
candidates = [
    {"name": "John Doe", "email": "john@test.com", "cv_file_path": "/path/john.pdf"},
    {"name": "Jane Smith", "email": "jane@test.com", "cv_file_path": "/path/jane.pdf"}
]

# 批量处理
result = await process_candidates_batch(
    candidates=candidates,
    hr_job_post=job_post,
    max_concurrent=5
)

print(f"成功: {result['successful']}/{result['total_candidates']}")
print(f"平均分: {result['average_score']:.1f}")
```

### 导出候选人数据

```python
from src.data_export import export_candidates_to_excel

candidates = [...]  # 候选人数据列表

export_candidates_to_excel(
    candidates,
    output_path="candidates.xlsx"
)
```

### Webhook 订阅

```python
from src.webhook_integration import subscribe_to_webhook

subscribe_to_webhook(
    webhook_url="https://your-app.com/webhooks/hr",
    event_types=[
        "candidate.submitted",
        "candidate.evaluated"
    ]
)
```

### 发送通知

```python
from src.extended_notifications import setup_notifications_from_env, send_candidate_notification

# 从环境变量设置
setup_notifications_from_env()

# 发送通知
candidate_data = {
    "candidate_name": "John Doe",
    "candidate_email": "john@test.com",
    "job_title": "Senior AI Engineer",
    "evaluation_score": 85,
    "evaluation": {"decision": "Strong Hire"},
    "summary": "Experienced engineer...",
    "cv_link": "https://...",
    "timestamp": "2025-02-16T10:30:45"
}

await send_candidate_notification(candidate_data)
```

---

## 配置

### 环境变量

```bash
# ===== LLM 配置 =====
LLM_PROVIDER=openai|anthropic|gemini|ollama
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AI...

# ===== Google 服务 =====
GOOGLE_SHEET_ID=your_sheet_id
GOOGLE_CLOUD_STORAGE_BUCKET=your_bucket
GOOGLE_CREDENTIALS_JSON_FILE=google-service-account-credentials.json

# ===== 扩展通知 (新) =====
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_webhook_url

# ===== Webhook (可选) =====
WEBHOOK_CANDIDATE_SUBMITTED=https://...
WEBHOOK_CANDIDATE_EVALUATED=https://...

# ===== FastAPI =====
HOST=0.0.0.0
PORT=8000
WORKERS=4
DEBUG=false
```

---

## 常见问题

### Q: 如何设置 Telegram 机器人?

1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 创建机器人
3. 获取 bot token
4. 找到 @userinfobot 获取 chat ID
5. 添加到 `.env`:
   ```bash
   TELEGRAM_BOT_TOKEN=你的token
   TELEGRAM_CHAT_ID=你的chat_id
   ```

### Q: 如何设置 Discord webhook?

1. 打开 Discord 服务器设置
2. 进入"集成" → "Webhook"
3. 创建 webhook
4. 复制 webhook URL
5. 添加到 `.env`:
   ```bash
   DISCORD_WEBHOOK_URL=你的webhook_url
   ```

### Q: 批量处理时如何控制并发数?

```python
result = await process_candidates_batch(
    candidates=candidates,
    hr_job_post=job_post,
    max_concurrent=3  # 同时处理 3 个
)
```

### Q: Excel 导出需要什么依赖?

```bash
pip install xlsxwriter
# 或
uv add xlsxwriter
```

### Q: 如何测试 webhook?

使用 webhook.site:
1. 访问 https://webhook.site
2. 复制你的唯一 URL
3. 订阅 webhook:
   ```python
   subscribe_to_webhook(
       webhook_url="https://webhook.site/你的ID",
       event_types=["candidate.evaluated"]
   )
   ```

### Q: Dashboard API 支持哪些筛选?

- `job_id` - 按职位筛选
- `min_score` - 最低分数
- `max_score` - 最高分数
- `limit` - 返回数量 (默认 50)
- `offset` - 偏移量 (分页)
- `sort_by` - 排序字段 (timestamp|score|name)
- `sort_order` - 排序方向 (asc|desc)

示例:
```
GET /api/candidates?min_score=70&limit=10&sort_by=score&sort_order=desc
```

---

## 文档资源

- **完整功能指南:** [FEATURES.md](FEATURES.md)
- **技术框架:** [TECHNICAL_FRAMEWORK.md](TECHNICAL_FRAMEWORK.md)
- **变更日志:** [CHANGELOG.md](CHANGELOG.md)
- **实施总结:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

## 性能提示

### 批量处理优化

```python
# CPU 密集型: 降低并发数
max_concurrent=3

# I/O 密集型: 提高并发数
max_concurrent=10

# 推荐值:
max_concurrent=5  # 默认推荐
```

### 内存优化

```python
# 处理大量文件时分批
batches = [candidates[i:i+100] for i in range(0, len(candidates), 100)]

for batch in batches:
    await process_candidates_batch(batch, job_post)
```

---

## 技术支持

- **Email:** furqan.cloud.dev@gmail.com
- **Organization:** AICampus
- **文档:** 见上文"文档资源"

---

**版本:** 1.1.0
**最后更新:** 2025-02-16
