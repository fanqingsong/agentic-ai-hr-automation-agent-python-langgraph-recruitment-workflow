# ============================================================================
# AUTHENTICATION API ROUTES
# ============================================================================

from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.schemas.auth import User, UserCreate, UserUpdate, Token, UserRole
from backend.models.user import UserModel
from backend.crud.user import (
    create_user,
    authenticate_user,
    get_user_by_email,
    get_user,
    update_user,
    get_users,
    delete_user,
    count_users,
)
from backend.services.security import create_access_token
from backend.core.dependencies import (
    get_current_active_user,
    get_current_superuser,
)
from backend.config import Config

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
) -> UserModel:
    """Register a new user."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Registration attempt - Email: {user.email}, Name: {user.name}, Role: {user.role}")

    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        logger.warning(f"Registration failed - Email already registered: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        new_user = create_user(db, user)
        logger.info(f"Registration successful - User ID: {new_user.id}, Email: {new_user.email}")
        return new_user
    except Exception as e:
        logger.error(f"Registration failed for {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/token", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
) -> Token:
    """OAuth2 compatible token endpoint."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Login attempt - Email: {form_data.username}")

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Login failed - Incorrect email or password for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Login successful - User ID: {user.id}, Email: {user.email}")
    access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=User)
def read_users_me(
    current_user: Annotated[UserModel, Depends(get_current_active_user)]
) -> UserModel:
    """Get current authenticated user."""
    return current_user


@router.put("/me", response_model=User)
def update_current_user(
    user_update: dict,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
) -> UserModel:
    """Update current user profile."""
    update_data = UserUpdate(**user_update)
    updated_user = update_user(db, str(current_user.id), update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user


@router.get("/users", response_model=list[User])
def read_users(
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
    skip: int = 0,
    limit: int = 100,
    role: UserRole = None,
    db: Session = Depends(get_db)
) -> list[UserModel]:
    """Get list of users (Admin only)."""
    users = get_users(db, skip=skip, limit=limit, role=role.value if role else None)
    return users


@router.get("/users/{user_id}", response_model=User)
def read_user(
    user_id: str,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
    db: Session = Depends(get_db)
) -> UserModel:
    """Get specific user by ID (Admin only)."""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(
    user_id: str,
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
    db: Session = Depends(get_db)
) -> None:
    """Delete user (Admin only)."""
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get("/stats/users")
def get_user_stats(
    current_user: Annotated[UserModel, Depends(get_current_superuser)],
    db: Session = Depends(get_db)
) -> dict:
    """Get user statistics (Admin only)."""
    return {
        "total_users": count_users(db),
        "job_seekers": count_users(db, UserRole.JOB_SEEKER.value),
        "hr_managers": count_users(db, UserRole.HR_MANAGER.value),
        "admins": count_users(db, UserRole.ADMIN.value),
    }
