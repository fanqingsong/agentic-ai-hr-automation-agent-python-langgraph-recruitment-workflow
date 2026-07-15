# ============================================================================
# DEFAULT USER SEEDING (startup)
# ============================================================================

"""
Seed default demo accounts (admin / HR manager / job seeker) on application startup.

Behavior (idempotent, runs on every startup):
- If a default account is missing, it is created with the configured password.
- If it exists but the configured password no longer verifies (e.g. a stale hash
  from the SQL init script), its password is reset so the documented credentials
  always work for demos.

Disable entirely with SEED_DEFAULT_USERS=false. Override credentials via env vars
(SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD, SEED_HR_EMAIL / SEED_HR_PASSWORD,
SEED_SEEKER_EMAIL / SEED_SEEKER_PASSWORD).
"""

import logging
import os

from backend.core.database import SessionLocal
from backend.crud.user import create_user, get_user_by_email
from backend.schemas.auth import UserCreate, UserRole
from backend.services.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


def _default_accounts() -> list[dict]:
    return [
        {
            "email": os.getenv("SEED_ADMIN_EMAIL", "admin@hr-automation.com"),
            "password": os.getenv("SEED_ADMIN_PASSWORD", "admin123"),
            "name": "System Administrator",
            "role": UserRole.ADMIN,
            "is_superuser": True,
        },
        {
            "email": os.getenv("SEED_HR_EMAIL", "hr@hr-automation.com"),
            "password": os.getenv("SEED_HR_PASSWORD", "hr123456"),
            "name": "HR Manager",
            "role": UserRole.HR_MANAGER,
            "is_superuser": False,
        },
        {
            "email": os.getenv("SEED_SEEKER_EMAIL", "seeker@hr-automation.com"),
            "password": os.getenv("SEED_SEEKER_PASSWORD", "seeker123"),
            "name": "Job Seeker",
            "role": UserRole.JOB_SEEKER,
            "is_superuser": False,
        },
    ]


def seed_default_users() -> None:
    """Create/repair the default demo accounts. Safe to call on every startup."""
    if os.getenv("SEED_DEFAULT_USERS", "true").lower() in ("false", "0", "no"):
        logger.info("SEED_DEFAULT_USERS disabled; skipping default account seeding")
        return

    db = SessionLocal()
    try:
        created, repaired = 0, 0
        for acct in _default_accounts():
            try:
                existing = get_user_by_email(db, acct["email"])
                if existing is None:
                    create_user(
                        db,
                        UserCreate(
                            email=acct["email"],
                            name=acct["name"],
                            password=acct["password"],
                            role=acct["role"],
                            is_active=True,
                            is_superuser=acct["is_superuser"],
                        ),
                    )
                    created += 1
                    logger.info(f"Seeded default account: {acct['email']} ({acct['role'].value})")
                elif not _password_ok(acct["password"], existing.hashed_password):
                    # Stale/mismatched/invalid hash (e.g. from SQL init) -> reset so documented creds work
                    existing.hashed_password = get_password_hash(acct["password"])
                    db.commit()
                    repaired += 1
                    logger.warning(f"Reset password for default account: {acct['email']}")
            except Exception as acct_err:
                db.rollback()
                logger.warning(f"Failed to seed default account {acct['email']}: {acct_err}")
        if created or repaired:
            logger.info(f"Default account seeding done (created={created}, repaired={repaired})")
        else:
            logger.info("Default accounts already present and valid")
    except Exception as e:
        logger.warning(f"Default account seeding skipped/failed: {e}")
    finally:
        db.close()


def _password_ok(password: str, hashed: str) -> bool:
    """verify_password, treating a malformed/unknown hash as a non-match rather than raising."""
    try:
        return verify_password(password, hashed)
    except Exception:
        return False
