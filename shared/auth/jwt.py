"""
JWT token generation and verification
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError

from shared.config.settings import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.api_algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.api_algorithm)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token

    Args:
        token: JWT token string

    Returns:
        Dictionary of token claims

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
        return payload
    except InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify a JWT token and check its type

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Dictionary of token claims

    Raises:
        InvalidTokenError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != token_type:
        raise InvalidTokenError(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")

    return payload


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject (user ID) from a token

    Args:
        token: JWT token string

    Returns:
        Subject from token or None if invalid
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except InvalidTokenError:
        return None
