# ============================================================================
# USER MODEL
# ============================================================================

"""
SQLAlchemy User model for PostgreSQL
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from backend.core.database import Base
from backend.schemas.auth import UserRole


class UserModel(Base):
    """
    User model for authentication and authorization

    Attributes:
        id: UUID primary key
        email: User's email address (unique)
        name: User's full name
        hashed_password: Bcrypt hashed password
        role: User role (job_seeker, hr_manager, admin)
        is_active: Whether the account is active
        is_superuser: Whether the user has superuser privileges
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    role = Column(
        SQLEnum(UserRole),
        default=UserRole.JOB_SEEKER,
        nullable=False
    )

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
