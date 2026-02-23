# ============================================================================
# POSTGRESQL DATABASE CONNECTION (用户认证)
# ============================================================================

"""
PostgreSQL database connection for user authentication and management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import Config

config = Config()

engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
    echo=config.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from backend.models.user import UserModel  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        if "already exists" not in str(e):
            raise


def drop_all_tables():
    """Drop all database tables (USE WITH CAUTION!)."""
    Base.metadata.drop_all(bind=engine)
