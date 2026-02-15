# ============================================================================
# AUTHENTICATION AND AUTHORIZATION DEPENDENCIES
# ============================================================================

"""
FastAPI dependencies for authentication and authorization
"""

from typing import Optional, Annotated, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.user import UserModel
from src.data_models import User, UserRole, TokenData
from src.security import decode_access_token, validate_token_payload
from src.crud.user import get_user_by_email


# ============================================================================
# OAUTH2 SCHEME
# ============================================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/token",
    auto_error=False
)


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserModel:
    """
    Dependency to get current authenticated user from JWT token

    Args:
        token: JWT access token
        db: Database session

    Returns:
        Current user model

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # Validate payload
    if not validate_token_payload(payload):
        raise credentials_exception

    # Get user email from token
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Get user from database
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Dependency to get current active user

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user model

    Raises:
        HTTPException: 400 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Dependency to get current superuser

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current superuser model

    Raises:
        HTTPException: 403 if user is not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


# ============================================================================
# ROLE-BASED AUTHORIZATION
# ============================================================================

class RoleChecker:
    """
    Dependency class for role-based access control

    Usage:
        @app.get("/admin/dashboard")
        def admin_dashboard(
            user: UserModel = Depends(RoleChecker([UserRole.ADMIN]))
        ):
            return {"message": "Welcome admin!"}
    """

    def __init__(self, allowed_roles: List[UserRole]):
        """
        Initialize role checker

        Args:
            allowed_roles: List of roles that can access the endpoint
        """
        self.allowed_roles = allowed_roles

    def __call__(
        self,
        current_user: UserModel = Depends(get_current_active_user)
    ) -> UserModel:
        """
        Check if current user has required role

        Args:
            current_user: Current active user

        Returns:
            Current user if authorized

        Raises:
            HTTPException: 403 if user doesn't have required role
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: one of {[r.value for r in self.allowed_roles]}"
            )
        return current_user


# ============================================================================
# CONVENIENCE ROLE CHECKERS
# ============================================================================

# Common role checkers
require_job_seeker = RoleChecker([UserRole.JOB_SEEKER])
require_hr_manager = RoleChecker([UserRole.HR_MANAGER])
require_admin = RoleChecker([UserRole.ADMIN])

# Multiple role checkers
require_manager_or_admin = RoleChecker([UserRole.HR_MANAGER, UserRole.ADMIN])
require_any_role = RoleChecker([UserRole.JOB_SEEKER, UserRole.HR_MANAGER, UserRole.ADMIN])


# ============================================================================
# OPTIONAL AUTH (allows unauthenticated access)
# ============================================================================

async def get_optional_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """
    Optional authentication - doesn't raise error if no token

    Args:
        token: JWT access token (optional)
        db: Database session

    Returns:
        User model if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
