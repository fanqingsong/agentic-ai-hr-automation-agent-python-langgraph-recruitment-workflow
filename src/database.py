# ============================================================================
# POSTGRESQL DATABASE CONNECTION (用户认证)
# ============================================================================

"""
PostgreSQL database connection for user authentication and management
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config import Config

# SQLAlchemy engine
engine = create_engine(
    Config.DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    echo=Config.DEBUG,    # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db():
    """
    Dependency to get database session

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """
    Initialize database tables

    Call this on application startup:
        from src.database import init_db
        init_db()
    """
    from src.models.user import User  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """
    Drop all database tables (USE WITH CAUTION!)

    Only use this for testing/development!
    """
    Base.metadata.drop_all(bind=engine)
