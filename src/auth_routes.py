# ============================================================================
# AUTHENTICATION API ROUTES
# ============================================================================

"""
API routes for user authentication and authorization
"""

from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.database import get_db
from src.data_models import User, UserCreate, Token, UserRole
from src.models.user import UserModel
from src.crud.user import (
    create_user,
    authenticate_user,
    get_user_by_email,
    get_user,
    update_user,
    get_users,
    delete_user,
    count_users
)
from src.security import create_access_token
from src.dependencies import (
    get_current_active_user,
    get_current_superuser,
    RoleChecker
)
from src.config import Config

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ============================================================================
# REGISTRATION
# ============================================================================

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register(
    user: UserCreate,
    db: Session = Depends(get_db)
) -> UserModel:
    """
    Register a new user

    Args:
        user: User creation data
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: 400 if email already registered
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    new_user = create_user(db, user)
    return new_user


# ============================================================================
# LOGIN / TOKEN
# ============================================================================

@router.post("/token", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
) -> Token:
    """
    OAuth2 compatible token endpoint

    Get an access token by providing username (email) and password

    Args:
        form_data: OAuth2 password form (username=email, password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer"
    )


# ============================================================================
# CURRENT USER
# ============================================================================

@router.get("/me", response_model=User)
def read_users_me(
    current_user: Annotated[UserModel, Depends(get_current_active_user)]
) -> UserModel:
    """
    Get current authenticated user

    Args:
        current_user: Current authenticated user

    Returns:
        Current user data
    """
    return current_user


@router.put("/me", response_model=User)
def update_current_user(
    user_update: dict,
    current_user: Annotated[UserModel, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
) -> UserModel:
    """
    Update current user profile

    Args:
        user_update: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user data
    """
    from src.data_models import UserUpdate

    # Create update model
    update_data = UserUpdate(**user_update)

    # Update user
    updated_user = update_user(db, str(current_user.id), update_data)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return updated_user


# ============================================================================
# USER MANAGEMENT (ADMIN ONLY)
# ============================================================================

@router.get("/users", response_model=list[User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    role: UserRole = None,
    db: Session = Depends(get_db),
    current_user: Annotated[UserModel, Depends(get_current_superuser)]
) -> list[UserModel]:
    """
    Get list of users (Admin only)

    Args:
        skip: Pagination offset
        limit: Max records to return
        role: Filter by role
        db: Database session
        current_user: Current superuser

    Returns:
        List of users
    """
    users = get_users(db, skip=skip, limit=limit, role=role.value if role else None)
    return users


@router.get("/users/{user_id}", response_model=User)
def read_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Annotated[UserModel, Depends(get_current_superuser)]
) -> UserModel:
    """
    Get specific user by ID (Admin only)

    Args:
        user_id: User UUID
        db: Database session
        current_user: Current superuser

    Returns:
        User data

    Raises:
        HTTPException: 404 if user not found
    """
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
    db: Session = Depends(get_db),
    current_user: Annotated[UserModel, Depends(get_current_superuser)]
) -> None:
    """
    Delete user (Admin only)

    Args:
        user_id: User UUID
        db: Database session
        current_user: Current superuser

    Raises:
        HTTPException: 404 if user not found
    """
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get("/stats/users")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: Annotated[UserModel, Depends(get_current_superuser)]
) -> dict:
    """
    Get user statistics (Admin only)

    Args:
        db: Database session
        current_user: Current superuser

    Returns:
        User statistics
    """
    return {
        "total_users": count_users(db),
        "job_seekers": count_users(db, UserRole.JOB_SEEKER.value),
        "hr_managers": count_users(db, UserRole.HR_MANAGER.value),
        "admins": count_users(db, UserRole.ADMIN.value),
    }
