# ============================================================================
# SECURITY AND AUTHENTICATION UTILITIES
# ============================================================================

"""
JWT token creation and password hashing utilities
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from src.config import Config

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode in token (e.g., {"sub": user_email})
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT access token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token (longer expiration than access token)

    Args:
        data: Payload data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT refresh token
    """
    # Refresh tokens typically have longer expiration (e.g., 7 days)
    if expires_delta is None:
        expires_delta = timedelta(days=7)

    return create_access_token(data, expires_delta)


# ============================================================================
# TOKEN VALIDATION
# ============================================================================

def validate_token_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate token payload structure

    Args:
        payload: Decoded JWT payload

    Returns:
        True if payload is valid, False otherwise
    """
    # Check for required fields
    required_fields = ["sub", "exp", "role"]
    return all(field in payload for field in required_fields)
