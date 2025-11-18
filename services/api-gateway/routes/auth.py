"""
Authentication routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.database import get_db
from shared.models.schemas import Token, UserLogin, TokenRefresh
from services.api_gateway.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Login endpoint - authenticate user and return JWT tokens

    For MVP, uses hardcoded admin user. In production, validate against database.
    """
    # TODO: Fetch user from database
    # For MVP, use hardcoded credentials
    if user_credentials.username == "admin" and user_credentials.password == "admin":
        user_data = {
            "sub": user_credentials.username,
            "user_id": 1,
            "role": "admin",
        }

        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
