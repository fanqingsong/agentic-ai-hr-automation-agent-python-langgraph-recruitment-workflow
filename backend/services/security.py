# ============================================================================
# SECURITY AND AUTHENTICATION UTILITIES
# ============================================================================

"""
JWT token creation and password hashing utilities
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from backend.config import Config


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT access token."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM]
        )
        return payload
    except (JWTError, AttributeError, TypeError):
        return None


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    return create_access_token(data, expires_delta)


def validate_token_payload(payload: Dict[str, Any]) -> bool:
    """Validate token payload structure."""
    required_fields = ["sub", "exp", "role"]
    return all(field in payload for field in required_fields)
