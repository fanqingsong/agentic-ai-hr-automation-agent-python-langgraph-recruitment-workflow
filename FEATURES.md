# New Features Guide

## Overview

This document describes the new features added to the AI HR Automation platform.

---

## 1. Batch Processing

### Module: `backend/batch_processing.py`

Process multiple candidate CVs concurrently with controlled parallelism.

### Features

- **Concurrent Processing**: Process up to N candidates simultaneously (configurable)
- **Batch Statistics**: Track success rate, average score, processing time
- **Directory Processing**: Process all PDF files from a directory
- **Error Handling**: Continue processing even if individual CVs fail

### Usage

#### Process Specific Candidates

```python
from src.batch_processing import process_candidates_batch
from src.fastapi_api import HRJobPost, JobApplication, HRUser

# Define job posting
job_application = JobApplication(
    title="Senior AI Engineer",
    description="We are looking for...",
    description_html=""
)

hr_user = HRUser(id="1", name="HR Manager", email="hr@company.com")
hr_job_post = HRJobPost(
    id=1,
    ulid="job_001",
    job_application=job_application,
    hr=hr_user
)

# Define candidates
candidates = [
    {
        "name": "John Doe",
        "email": "john@example.com",
        "cv_file_path": "/path/to/john_cv.pdf"
    },
    {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "cv_file_path": "/path/to/jane_cv.pdf"
    }
]

# Process batch
result = await process_candidates_batch(
    candidates=candidates,
    hr_job_post=hr_job_post,
    max_concurrent=5  # Process 5 at a time
)

print(f"Batch ID: {result['batch_id']}")
print(f"Successful: {result['successful']}/{result['total_candidates']}")
print(f"Average Score: {result['average_score']:.1f}")
```

#### Process All CVs from Directory

```python
from src.batch_processing import process_candidates_from_directory

result = await process_candidates_from_directory(
    cv_directory="./resumes",
    hr_job_post=hr_job_post,
    max_concurrent=5
)
```

### API Endpoint

```
POST /api/batch/process
```

Request:
```json
{
  "candidates": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "cv_file_path": "/path/to/cv.pdf"
    }
  ],
  "job_id": "job_id",
  "max_concurrent": 5
}
```

---

## 2. Data Export

### Module: `backend/data_export.py`

Export candidate data to CSV and Excel formats with formatting.

### Features

- **CSV Export**: Simple comma-separated values export
- **Excel Export**: Rich formatting with conditional formatting (color-coded scores)
- **Summary Sheet**: Automatic statistics summary in Excel
- **Batch Export**: Export entire batch results

### Usage

#### Export to CSV

```python
from src.data_export import export_candidates_to_csv

# Assume you have candidate data
candidates = [...]  # List of candidate result dicts

# Export to file
export_candidates_to_csv(candidates, output_path="candidates.csv")

# Or get as string
csv_data = export_candidates_to_csv(candidates)
print(csv_data)
```

#### Export to Excel

```python
from src.data_export import export_candidates_to_excel

export_candidates_to_excel(
    candidates,
    output_path="candidates.xlsx"
)
```

Excel output includes:
- Formatted headers (blue background)
- Color-coded scores (green >= 70, red < 50)
- Summary statistics sheet
- Auto-sized columns

#### Export Batch Results

```python
from src.data_export import export_batch_to_file

batch_result = {...}  # From batch processing

files = export_batch_to_file(
    batch_result,
    format="xlsx",  # or "csv"
    output_dir="./exports"
)

print(files)
# {
#   "excel": "./exports/batch_abc123_20250216_103045.xlsx",
#   "summary": "./exports/summary_abc123_20250216_103045.txt"
# }
```

### API Endpoint

```
POST /api/export/candidates
```

Parameters:
- `job_id` (optional): Filter by job
- `format`: "csv" or "xlsx"
- `min_score` (optional): Minimum score filter
- `max_score` (optional): Maximum score filter

Returns downloadable file.

---

## 3. HR Dashboard API

### Module: `backend/dashboard_api.py`

Comprehensive API endpoints for HR analytics dashboard.

### Features

- **Dashboard Statistics**: Overview metrics and top candidates
- **Candidate Listing**: Paginated, filterable, sortable candidate list
- **Candidate Details**: Full candidate information
- **Jobs Listing**: Available job postings
- **Score Distribution**: Analytics for score ranges
- **Data Export**: Direct export API integration

### API Endpoints

#### Get Dashboard Statistics

```
GET /api/dashboard/stats
```

Query parameters:
- `job_id` (optional): Filter by job
- `days` (default: 30): Days to look back

Response:
```json
{
  "total_candidates": 150,
  "successful_evaluations": 145,
  "failed_evaluations": 5,
  "average_score": 72.5,
  "highest_score": 95,
  "lowest_score": 35,
  "high_scorers_count": 80,
  "low_scorers_count": 15,
  "recent_candidates": [...],
  "top_candidates": [...]
}
```

#### Get Candidates (Paginated)

```
GET /api/candidates
```

Query parameters:
- `job_id` (optional): Filter by job
- `min_score`, `max_score`: Score range filter
- `limit` (default: 50, max: 500): Page size
- `offset` (default: 0): Pagination offset
- `sort_by` (default: "timestamp"): "timestamp" | "score" | "name"
- `sort_order` (default: "desc"): "asc" | "desc"

Response:
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "candidates": [...]
}
```

#### Get Candidate Details

```
GET /api/candidates/{candidate_id}
```

Returns full candidate information including evaluation.

#### Get Jobs

```
GET /api/jobs
```

Query parameters:
- `limit` (default: 50)
- `active_only` (default: false)

#### Get Score Distribution

```
GET /api/analytics/score-distribution
```

Query parameters:
- `job_id` (optional): Filter by job

Response:
```json
{
  "total": 150,
  "distribution": [
    {
      "range": "0-49",
      "count": 15,
      "percentage": 10.0
    },
    {
      "range": "70-79",
      "count": 45,
      "percentage": 30.0
    }
  ]
}
```

---

## 4. Webhook Integration

### Module: `backend/webhook_integration.py`

Real-time webhook notifications for event-driven integrations.

### Features

- **Event Types**: Subscribe to specific events
- **Multiple Subscribers**: Multiple URLs per event type
- **Retry Logic**: Automatic retries for failed deliveries
- **Event Builders**: Pre-built event payloads

### Event Types

- `candidate.submitted`: New CV submitted
- `candidate.processed`: CV processing completed
- `candidate.evaluated`: Candidate evaluation complete
- `batch.started`: Batch processing started
- `batch.completed`: Batch processing complete

### Usage

#### Subscribe to Events

```python
from src.webhook_integration import subscribe_to_webhook

subscription = subscribe_to_webhook(
    webhook_url="https://your-app.com/webhooks/hr",
    event_types=[
        "candidate.submitted",
        "candidate.processed",
        "candidate.evaluated"
    ]
)

print(subscription)
# {
#   "subscription_id": "wh_20250216103045",
#   "webhook_url": "https://your-app.com/webhooks/hr",
#   "events": ["candidate.submitted", ...],
#   "status": "active"
# }
```

#### Webhook Payload Format

```json
{
  "event": "candidate.evaluated",
  "timestamp": "2025-02-16T10:30:45",
  "data": {
    "candidate": {
      "name": "John Doe",
      "email": "john@example.com",
      "job_title": "Senior AI Engineer"
    },
    "evaluation": {
      "score": 85,
      "decision": "Strong Hire",
      "reasoning": "Excellent match...",
      "strengths": ["Python", "LangChain"],
      "gaps": ["Kubernetes experience"]
    },
    "evaluated_at": "2025-02-16T10:30:45"
  }
}
```

#### Unsubscribe

```python
from src.webhook_integration import unsubscribe_from_webhook

unsubscribe_from_webhook(
    webhook_url="https://your-app.com/webhooks/hr"
    # event_type="candidate.evaluated"  # Optional specific event
)
```

---

## 5. Extended Notifications

### Module: `backend/extended_notifications.py`

Additional notification channels: Telegram and Discord.

### Features

- **Telegram Bot**: Send candidate alerts via Telegram
- **Discord Webhook**: Rich embeds with candidate details
- **Unified Manager**: Broadcast to multiple channels
- **Auto-setup**: Configure from environment variables

### Configuration

Add to your `.env` file:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_or_group_id

# Discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Usage

#### Setup from Environment

```python
from src.extended_notifications import setup_notifications_from_env

setup_notifications_from_env()
```

#### Send Notifications

```python
from src.extended_notifications import send_candidate_notification

candidate_data = {
    "candidate_name": "John Doe",
    "candidate_email": "john@example.com",
    "job_title": "Senior AI Engineer",
    "evaluation_score": 85,
    "evaluation": {"decision": "Strong Hire"},
    "summary": "Experienced engineer...",
    "cv_link": "https://storage.google...",
    "timestamp": "2025-02-16T10:30:45"
}

results = await send_candidate_notification(candidate_data)
```

#### Telegram Message Format

```
🔔 New High-Scoring Candidate Alert

👤 Candidate: John Doe
📧 Email: john@example.com
💼 Position: Senior AI Engineer

📊 Score: 85/100
✅ Decision: Strong Hire

📝 Summary:
Experienced software engineer with 5 years...

🔗 CV Link: https://storage.google...
⏰ Time: 2025-02-16T10:30:45
```

#### Discord Message Format

- Rich embed with color-coded score
- Structured fields
- @everyone mention for high scores
- Clickable CV link

---

## Integration with LangGraph Workflow

### Adding New Nodes

```python
from src.hr_automation import create_hr_workflow
from src.extended_notifications import send_extended_notifications_node
from src.webhook_integration import send_candidate_webhooks

# Extend workflow
def create_enhanced_hr_workflow():
    graph = StateGraph(AgentState)

    # Add existing nodes
    graph.add_node("upload_cv", upload_cv_node)
    # ... other nodes ...

    # Add webhook node after evaluation
    graph.add_node("send_webhooks", send_candidate_webhooks)

    # Add extended notifications
    graph.add_node("extended_notifications", send_extended_notifications_node)

    # Update edges
    graph.add_edge("evaluate", "send_webhooks")
    graph.add_edge("send_webhooks", "skills_match_node")

    # Add parallel extended notifications
    graph.add_conditional_edges(
        "score_decision",
        route_on_score,
        {
            "notify_hr": "fan_out_notifications",
            "extended_notify": "extended_notifications",
            "end": END
        }
    )

    return graph.compile()
```

---

## Environment Variables

Add these to your `env.example`:

```bash
# ===== EXTENDED NOTIFICATIONS =====
# Telegram Bot API
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890

# Discord Webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123/abc

# ===== WEBHOOK SUBSCRIPTIONS =====
# Optional: Default webhook subscribers
WEBHOOK_CANDIDATE_SUBMITTED=https://your-app.com/webhooks/candidate
WEBHOOK_CANDIDATE_EVALUATED=https://your-app.com/webhooks/evaluated
```

---

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...

    # Data export
    "xlsxwriter>=3.0.0",

    # Webhooks and notifications
    "httpx>=0.28.0",
]
```

Install with:
```bash
uv add xlsxwriter httpx
```

---

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

All new endpoints are documented with examples.

---

## Testing

### Test Batch Processing

```python
# test_batch.py
import asyncio
from src.batch_processing import process_candidates_from_directory
from src.fastapi_api import HRJobPost, JobApplication, HRUser

async def test():
    job_app = JobApplication(
        title="Test Position",
        description="Test job description",
        description_html=""
    )

    hr_user = HRUser(id="1", name="Test HR", email="hr@test.com")
    job_post = HRJobPost(id=1, ulid="test", job_application=job_app, hr=hr_user)

    result = await process_candidates_from_directory(
        cv_directory="./test_resumes",
        hr_job_post=job_post,
        max_concurrent=3
    )

    print(result)

asyncio.run(test())
```

### Test Webhooks

Use a service like webhook.site to test webhook delivery:

```python
from src.webhook_integration import subscribe_to_webhook
from src.webhook_integration import webhook_manager

# Subscribe to test webhook
subscribe_to_webhook(
    webhook_url="https://webhook.site/your-unique-id",
    event_types=["candidate.submitted"]
)

# Send test event
import asyncio

async def test_webhook():
    await webhook_manager.send_webhook(
        "candidate.submitted",
        {"candidate_name": "Test", "candidate_email": "test@test.com"}
    )

asyncio.run(test_webhook())
```

---

## Troubleshooting

### Batch Processing Issues

**Problem**: Memory issues with large batches
**Solution**: Reduce `max_concurrent` parameter

**Problem**: CV extraction fails
**Solution**: Check LlamaCloud API key, verify PDF files are valid

### Export Issues

**Problem**: Excel export fails
**Solution**: Install xlsxwriter: `uv add xlsxwriter`

**Problem**: CSV encoding issues
**Solution**: Files are UTF-8 encoded. Use UTF-8 compatible editor.

### Notification Issues

**Problem**: Telegram not sending
**Solution**:
- Verify bot token from @BotFather
- Get correct chat ID (use @userinfobot)
- Ensure bot has permission to send messages

**Problem**: Discord webhook fails
**Solution**:
- Verify webhook URL is complete
- Check webhook hasn't been deleted
- Ensure bot has permission to post

### Webhook Issues

**Problem**: Webhooks not delivered
**Solution**:
- Check webhook URL is accessible
- Verify server accepts POST requests
- Check logs for specific error messages

---

## Support

For issues or questions:
- Developer: Furqan Khan (furqan.cloud.dev@gmail.com)
- Organization: AICampus - Agentic AI Research Community
