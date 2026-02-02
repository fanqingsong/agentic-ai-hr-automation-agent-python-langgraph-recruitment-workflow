# ============================================================================
# AI-Powered HR Automation with LangGraph
# Complete CV Review to Candidate Evaluation System
# Backend Server Access via FastAPI

# Get the full source code of complete project:
# https://aicampusmagazines.gumroad.com/l/gscdiq

## Developed By AICampus - Gateway for future AI research & learning
## Developer: Furqan Khan
## Email: furqan.cloud.dev@gmail.com
# ============================================================================

"""
FastAPI Wrapper for AI HR Automation
Integrates with hr_automation.py LangGraph workflow
Handles Forms submissions with CV file processing
"""

from bson import ObjectId
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict, field_serializer, field_validator
from pydantic.alias_generators import to_camel

from typing import Dict, Any
import os
import sys
import uvicorn
from dotenv import load_dotenv
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import tempfile
import shutil

from pymongo import AsyncMongoClient
from typing import List
from bs4 import BeautifulSoup
import re
from typing import Optional
from src.config import Config
from utils.ulid_helper import generate_ulid

# Add parent directory to path to import hr_automation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MONGODB SETUP
# ============================================================================
# 1. Initialize the Async Client
# In 2026, AsyncMongoClient is the standard for non-blocking operations
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncMongoClient(MONGODB_URL)
db = client.get_database("ai-hr-automation")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ProcessingResult(BaseModel):
    """Model for processing result response"""
    success: bool
    message: str
    candidate_name: str
    candidate_email: str
    summary: str
    score: int
    reasoning: str
    cv_link: str
    timestamp: str
    errors: List[str] = []


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    service: str
    version: str = "1.0.0"
    config: Dict[str, str]

class User(BaseModel):
    id: str
    name: str
    email: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('id')
    def serialize_id(self, value: Optional[str]) -> Optional[str]:
        """Convert ObjectId to string when serializing"""
        if value and isinstance(value, ObjectId):
            return str(value)
        return value


class HRUser(User):
    role: Optional[str] = "hr manager"


class JobApplication(BaseModel):
    title: str
    description_html: str = Field(
        validation_alias="descriptionHTML",  # For parsing incoming data
        serialization_alias="descriptionHTML"  # For serializing outgoing data
    )
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @model_validator(mode='after')
    def strip_html_and_assign(self) -> 'JobApplication':
        # More Aggressive Line Breaking for LLM Input Prompt
        if self.description_html:
            soup = BeautifulSoup(self.description_html, "html.parser")
            # Add newlines around block elements
            block_elements = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                              'ul', 'ol', 'blockquote', 'pre', 'hr']
            for tag in soup.find_all(block_elements):
                # Add newline before and after block elements
                tag.insert_before('\n\n')
                tag.insert_after('\n\n')

            # Handle list items
            for li in soup.find_all('li'):
                li.insert_before('\n• ')

            # Handle line breaks
            for br in soup.find_all('br'):
                br.replace_with('\n')

            # Handle strong/bold text (keep inline)
            for strong in soup.find_all(['strong', 'b']):
                strong.insert_before('')
                strong.insert_after('')

            # Extract text
            text = soup.get_text()

            # Clean up excessive whitespace
            # Collapse multiple spaces into one
            text = re.sub(r'[ \t]+', ' ', text)
            # Collapse 3+ newlines into 2
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Remove spaces at start/end of lines
            text = '\n'.join(line.strip() for line in text.split('\n'))
            # Remove leading/trailing whitespace
            text = text.strip()

            self.description = text
        return self


class HRJobPost(BaseModel):
    id: Optional[str] = Field(
        default=None,
        validation_alias="_id",  # For parsing incoming data
        serialization_alias="id"  # For serializing outgoing data
    )

    ulid: Optional[str] = Field(default_factory=generate_ulid)
    job_application: JobApplication = Field(
        validation_alias="jobApplication",  # For parsing incoming data
        serialization_alias="jobApplication"  # For serializing outgoing data
    )
    hr: HRUser
    created_at: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('id')
    def serialize_id(self, value: Optional[str]) -> Optional[str]:
        """Convert ObjectId to string when serializing"""
        if value and isinstance(value, ObjectId):
            return str(value)
        return value

    @field_validator('ulid', mode='before')
    @classmethod
    def generate_ulid_if_missing(cls, v):
        """Generate ULID if not provided"""
        if v is None or v == '':
            return generate_ulid()
        return v


class CandidateSubmittedApplication(BaseModel):
    job_id: str = Field(
        validation_alias="jobId",  # For parsing incoming data
        serialization_alias="jobId"  # For serializing outgoing data
    )
    name: str
    email: EmailStr

    # Config to handle camelCase (camelCase) automatically
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows using either snake_case or camelCase in constructor
        from_attributes=True  # Useful if converting from ORM (database) objects
    )


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting AI HR Automation API")
    logger.info("=" * 80)
    logger.info(f"Host: {Config.HOST}:{Config.PORT}")
    logger.info("=" * 80)

    # Validate configuration
    try:
        Config.validate()
        logger.info("✅ Configuration validated successfully")
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        logger.warning("⚠️  API will start but may not function correctly")

    yield

    # Shutdown
    logger.info("👋 Shutting down AI HR Automation API")


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="AI HR Automation API",
    description="Automated CV review and candidate evaluation system powered by LangGraph and OpenAI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "AI HR Automation API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "description": "Automated CV review and candidate evaluation using LangGraph"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns system status and configuration
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="AI HR Automation",
        config={
            "llm_provider": Config.LLM_PROVIDER
        }
    )

from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Debug validation errors"""
    print("Validation Error Details:")
    print(exc.errors())
    print("Body:", exc.body)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.get("/api/config")
async def get_config():
    """
    Get current configuration (non-sensitive data only)
    """
    return {
        "model_provider": Config.LLM_PROVIDER,
        "extraction_temp": Config.EXTRACTION_TEMP,
        "summary_temp": Config.SUMMARY_TEMP,
        "evaluation_temp": Config.EVALUATION_TEMP
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "path": str(request.url),
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if Config.DEBUG else "An error occurred processing your request",
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# MAIN
# ============================================================================

def get_optimal_workers():
    # Detect available CPU cores (logical cores)
    cores = os.cpu_count() or 1  # Fallback to 1 if detection fails

    # Apply standard production formula
    return (2 * cores) + 1

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    logger.info(f"API Documentation: http://127.0.0.1:8000/docs")

    ## Get optimal workers for production
    # workers_count = get_optimal_workers()
    # print(f"Starting server with {workers_count} workers...")

    uvicorn.run("fastapi_api:app",
                host="127.0.0.1",
                port=8000,
                reload=False,
                log_level="info",
                # workers=workers_count
                )