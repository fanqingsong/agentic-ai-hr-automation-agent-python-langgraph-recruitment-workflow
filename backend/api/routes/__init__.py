# ============================================================================
# Dashboard API routes – split by feature
# ============================================================================

import logging

from backend.api.routes.batch import get_batch_router
from backend.api.routes.candidates import get_candidates_router
from backend.api.routes.cv import get_cv_router
from backend.api.routes.dashboard_stats import get_dashboard_stats_router
from backend.api.routes.export import get_export_router
from backend.api.routes.jobs import get_jobs_router
from backend.api.routes.my_resumes import get_my_resumes_router

logger = logging.getLogger(__name__)


def register_dashboard_routes(app, db):
    """
    Register all dashboard/HR API routers with the FastAPI app.
    Mount my_resumes first so /api/my-resumes/{id}/job-recommendations and /download are matched before /api/my-resumes/{id}.
    """
    app.include_router(get_my_resumes_router(db), prefix="/api")
    app.include_router(get_dashboard_stats_router(db), prefix="/api")
    app.include_router(get_candidates_router(db), prefix="/api")
    app.include_router(get_cv_router(db), prefix="/api")
    app.include_router(get_jobs_router(db), prefix="/api")
    app.include_router(get_export_router(db), prefix="/api")
    app.include_router(get_batch_router(db), prefix="/api")
    logger.info("✅ Dashboard API routes registered successfully")
