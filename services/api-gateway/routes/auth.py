"""
Authentication routes
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from shared.models.database import get_db
from shared.models.models import User
from shared.models.schemas import Token, UserLogin, TokenRefresh
from services.api_gateway.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login endpoint - authenticate user and return JWT tokens
    """
    # Fetch user from database
    query = select(User).where(User.username == user_credentials.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Check if user exists
    if not user:
        logger.warning("login_failed", username=user_credentials.username, reason="user_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        logger.warning("login_failed", username=user_credentials.username, reason="user_inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support.",
        )

    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        await db.commit()

        logger.warning(
            "login_failed",
            username=user_credentials.username,
            reason="invalid_password",
            failed_attempts=user.failed_login_attempts,
        )

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.is_active = False
            await db.commit()
            logger.warning("account_locked", username=user_credentials.username)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to too many failed login attempts. Please contact support.",
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    await db.commit()

    logger.info("login_successful", username=user.username, user_id=user.id)

    # Create JWT tokens
    user_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role.value,
    }

    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh):
    """
    Refresh access token using refresh token
    """
    try:
        payload = decode_token(token_data.refresh_token)

        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_data = {
            "sub": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "role": payload.get("role"),
        }

        access_token = create_access_token(user_data)
        new_refresh_token = create_refresh_token(user_data)

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
        ) from e


@router.post("/logout")
async def logout():
    """
    Logout endpoint

    In a production system, this would invalidate the token in a blacklist/database.
    For now, returns success response - client should discard token.
    """
    return {"message": "Successfully logged out"}
