# ============================================================================
# AI HR Automation API - Modular Entry Point
# ============================================================================

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import Config
from backend.core.database import init_db
from backend.core.mongodb import ensure_indexes, get_mongo_db
from backend.api.auth import router as auth_router
from backend.api.dashboard import register_dashboard_routes
from backend.schemas.hr_api import HealthResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""
    logger.info("=" * 80)
    logger.info("🚀 Starting AI HR Automation API")
    logger.info("=" * 80)
    logger.info(f"Host: {Config.HOST}:{Config.PORT}")
    logger.info("=" * 80)

    try:
        Config.validate()
        logger.info("✅ Configuration validated successfully")
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        logger.warning("⚠️  API will start but may not function correctly")

    try:
        init_db()
        logger.info("✅ Database tables initialized successfully")
        try:
            from backend.core.seed import seed_default_users
            seed_default_users()
        except Exception as seed_err:
            logger.warning(f"⚠️  Default account seeding failed: {seed_err}")
    except Exception as e:
        err_msg = str(e).lower()
        if "name resolution" in err_msg or "could not translate host" in err_msg or "connection" in err_msg:
            logger.warning(
                "⚠️  PostgreSQL unreachable: %s (host=%s). "
                "When running outside Docker, set POSTGRES_SERVER=localhost in .env. "
                "User authentication will be disabled until DB is available.",
                e,
                getattr(Config, "POSTGRES_SERVER", "?"),
            )
        else:
            logger.exception("❌ Database initialization failed")
        logger.warning("⚠️  User authentication may not work correctly")

    try:
        await ensure_indexes(db)
        logger.info("✅ MongoDB indexes ensured")
    except Exception as idx_err:
        logger.warning(f"⚠️  MongoDB index creation failed: {idx_err}")

    yield

    logger.info("👋 Shutting down AI HR Automation API")


app = FastAPI(
    title="AI HR Automation API",
    description="Automated CV review and candidate evaluation system powered by LangGraph and OpenAI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

_cors_origins = Config.get_cors_origins()
if "*" in _cors_origins:
    # "*" cannot be combined with credentials per the CORS spec; drop credentials.
    logger.warning("CORS_ORIGINS contains '*'; disabling allow_credentials for spec compliance.")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _cors_error_headers(request: Request) -> Dict[str, str]:
    """CORS headers for responses produced by the generic ``Exception`` handler.

    Starlette runs the ``Exception`` handler inside ServerErrorMiddleware, which
    sits *outside* CORSMiddleware. Without this, a real 500 reaches the browser
    with no ``Access-Control-Allow-Origin`` header and surfaces as an opaque
    "Network Error" / CORS error instead of the actual failure. Re-adding the
    headers here lets the frontend read the real status and message.
    """
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if "*" in _cors_origins:
        return {"Access-Control-Allow-Origin": "*"}
    if origin in _cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


# Auth routes
app.include_router(auth_router)

# Dashboard + HR routes (MongoDB); my_resumes (incl. job-recommendations) is registered first inside
db = get_mongo_db()
register_dashboard_routes(app, db)


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AI HR Automation API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "dashboard": "/api/dashboard/stats",
        "description": "Automated CV review and candidate evaluation using LangGraph",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="AI HR Automation",
        config={"llm_provider": Config.LLM_PROVIDER},
    )


@app.get("/api/config")
async def get_config():
    """Get current configuration (non-sensitive data only)."""
    return {
        "model_provider": Config.LLM_PROVIDER,
        "extraction_temp": Config.EXTRACTION_TEMP,
        "summary_temp": Config.SUMMARY_TEMP,
        "evaluation_temp": Config.EVALUATION_TEMP,
    }


# Exception handlers
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers=_cors_error_headers(request),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if Config.DEBUG else "An error occurred processing your request",
            "timestamp": datetime.now().isoformat(),
        },
        headers=_cors_error_headers(request),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "path": str(request.url),
            "timestamp": datetime.now().isoformat(),
        },
        headers=_cors_error_headers(request),
    )


if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    logger.info("API Documentation: http://127.0.0.1:8000/docs")
    uvicorn.run(
        "backend.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )
