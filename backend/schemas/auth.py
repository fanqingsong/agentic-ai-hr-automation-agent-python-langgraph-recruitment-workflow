# ============================================================================
# USER AND AUTHENTICATION SCHEMAS
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class UserRole(str, Enum):
    """User roles for access control"""
    JOB_SEEKER = "job_seeker"
    HR_MANAGER = "hr_manager"
    ADMIN = "admin"


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserUpdate(BaseModel):
    """User update model"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    """User model for API responses"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with hashed password (database)"""
    hashed_password: str


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Token payload data"""
    email: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None
