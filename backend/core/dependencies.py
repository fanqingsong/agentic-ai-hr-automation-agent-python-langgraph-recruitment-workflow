# ============================================================================
# AUTHENTICATION AND AUTHORIZATION DEPENDENCIES
# ============================================================================

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.user import UserModel
from backend.schemas.auth import UserRole, TokenData
from backend.services.security import decode_access_token, validate_token_payload
from backend.crud.user import get_user_by_email


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/token",
    auto_error=False
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserModel:
    """Dependency to get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    if not validate_token_payload(payload):
        raise credentials_exception

    email = payload.get("sub")
    if not email:
        raise credentials_exception

    try:
        user = get_user_by_email(db, email)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("get_user_by_email failed: %s", e)
        raise credentials_exception
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Dependency to get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Dependency to get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


class RoleChecker:
    """Dependency class for role-based access control."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: UserModel = Depends(get_current_active_user)
    ) -> UserModel:
        role = getattr(current_user, "role", None)
        role_value = role.value if hasattr(role, "value") else role
        allowed_values = {r.value if hasattr(r, "value") else r for r in self.allowed_roles}
        if role_value not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: one of {list(allowed_values)}"
            )
        return current_user


require_job_seeker = RoleChecker([UserRole.JOB_SEEKER])
require_hr_manager = RoleChecker([UserRole.HR_MANAGER])
require_admin = RoleChecker([UserRole.ADMIN])
require_manager_or_admin = RoleChecker([UserRole.HR_MANAGER, UserRole.ADMIN])
require_any_role = RoleChecker([UserRole.JOB_SEEKER, UserRole.HR_MANAGER, UserRole.ADMIN])


async def get_optional_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """Optional authentication - doesn't raise error if no token."""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
