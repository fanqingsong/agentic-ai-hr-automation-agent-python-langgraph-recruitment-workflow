# Core: database, dependencies, MongoDB client
from backend.core.database import get_db, init_db, SessionLocal, Base, engine
from backend.core.dependencies import (
    oauth2_scheme,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_optional_user,
    RoleChecker,
    require_job_seeker,
    require_hr_manager,
    require_admin,
    require_manager_or_admin,
    require_any_role,
)

__all__ = [
    "get_db",
    "init_db",
    "SessionLocal",
    "Base",
    "engine",
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "get_optional_user",
    "RoleChecker",
    "require_job_seeker",
    "require_hr_manager",
    "require_admin",
    "require_manager_or_admin",
    "require_any_role",
]
