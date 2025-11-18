"""
Authentication utilities for JWT-based authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models.database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer security scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Dictionary of claims to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.api_algorithm)

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Dictionary of claims to encode

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=settings.api_algorithm)

    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the current authenticated user from JWT token

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        User information dictionary

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials

    try:
        payload = decode_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

        # TODO: Fetch user from database
        # For now, return payload data
        user_data = {
            "username": username,
            "role": payload.get("role", "viewer"),
            "user_id": payload.get("user_id"),
        }

        return user_data

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Get the current active user

    Args:
        current_user: Current user from token

    Returns:
        User information

    Raises:
        HTTPException: If user is inactive
    """
    # TODO: Check if user is active in database
    return current_user


def require_role(required_role: str):
    """
    Dependency to require a specific role

    Args:
        required_role: Required role name

    Returns:
        Dependency function
    """

    async def role_checker(current_user: dict = Depends(get_current_active_user)) -> dict:
        user_role = current_user.get("role", "viewer")

        # Define role hierarchy
        role_hierarchy = {
            "admin": 3,
            "operator": 2,
            "viewer": 1,
        }

        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 99):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )

        return current_user

    return role_checker


# Role-based dependencies
require_admin = require_role("admin")
require_operator = require_role("operator")
require_viewer = require_role("viewer")
