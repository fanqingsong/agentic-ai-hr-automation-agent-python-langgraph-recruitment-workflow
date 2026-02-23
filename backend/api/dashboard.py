# ============================================================================
# HR Dashboard API – entry point (routes are split under api/routes/)
# ============================================================================

"""
Dashboard and HR API are registered via backend.api.routes.
This module re-exports the registration function for backward compatibility.
"""

from backend.api.routes import get_my_resumes_router, register_dashboard_routes

__all__ = ["register_dashboard_routes", "get_my_resumes_router"]




