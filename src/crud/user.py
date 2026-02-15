# ============================================================================
# USER CRUD OPERATIONS
# ============================================================================

"""
CRUD operations for User model
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models.user import UserModel
from src.data_models import UserCreate, UserUpdate
from src.security import get_password_hash, verify_password


def get_user(db: Session, user_id: str) -> Optional[UserModel]:
    """
    Get user by ID

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        User model if found, None otherwise
    """
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """
    Get user by email

    Args:
        db: Database session
        email: User email

    Returns:
        User model if found, None otherwise
    """
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[UserModel]:
    """
    Get list of users with optional filtering

    Args:
        db: Database session
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        role: Filter by role
        is_active: Filter by active status

    Returns:
        List of user models
    """
    query = db.query(UserModel)

    # Apply filters
    if role:
        query = query.filter(UserModel.role == role)
    if is_active is not None:
        query = query.filter(UserModel.is_active == is_active)

    return query.offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> UserModel:
    """
    Create new user

    Args:
        db: Database session
        user: User creation data

    Returns:
        Created user model
    """
    # Hash password
    hashed_password = get_password_hash(user.password)

    # Create user model
    db_user = UserModel(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser
    )

    # Save to database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user(db: Session, user_id: str, user_update: UserUpdate) -> Optional[UserModel]:
    """
    Update user

    Args:
        db: Database session
        user_id: User UUID
        user_update: User update data

    Returns:
        Updated user model if found, None otherwise
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)

    return db_user


def delete_user(db: Session, user_id: str) -> bool:
    """
    Delete user

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        True if deleted, False if not found
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return False

    db.delete(db_user)
    db.commit()

    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[UserModel]:
    """
    Authenticate user with email and password

    Args:
        db: Database session
        email: User email
        password: Plain text password

    Returns:
        User model if authentication successful, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def count_users(db: Session, role: Optional[str] = None) -> int:
    """
    Count total users

    Args:
        db: Database session
        role: Optional role filter

    Returns:
        Number of users
    """
    query = db.query(UserModel)
    if role:
        query = query.filter(UserModel.role == role)
    return query.count()
