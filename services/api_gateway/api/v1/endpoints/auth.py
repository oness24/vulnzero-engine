"""
VulnZero API Gateway - Authentication Endpoints
JWT-based authentication with login, refresh, and logout
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
    get_current_user,
)
from services.api_gateway.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    LogoutResponse,
)
from shared.config.settings import settings
from shared.models.models import User
from datetime import datetime

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
    description="""
    Authenticate user and return JWT tokens.

    **Demo Credentials:**
    - Admin: `admin@vulnzero.com` / `Admin123!`
    - Operator: `operator@vulnzero.com` / `Operator123!`
    - Viewer: `viewer@vulnzero.com` / `Viewer123!`

    **Returns:**
    - `access_token`: Short-lived token for API access (30 minutes)
    - `refresh_token`: Long-lived token for refreshing access (7 days)
    """,
)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access and refresh tokens.
    """
    # Get user from database
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed login attempts and update last login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    # Note: In production, get IP from request headers
    # user.last_login_ip = request.client.host
    db.commit()

    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "name": user.full_name or user.username,
        },
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh Access Token",
    description="""
    Use refresh token to obtain a new access token.

    This endpoint allows clients to get a new access token without
    requiring the user to log in again.
    """,
)
async def refresh_token(refresh_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Fetch user from database
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = db.query(User).filter(User.id == user_id_int).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create new access token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }

    access_token = create_access_token(token_data)

    return TokenRefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="User Logout",
    description="""
    Logout current user.

    Note: Since JWT tokens are stateless, this endpoint is primarily
    for client-side token deletion. In production, implement token
    blacklisting for enhanced security.
    """,
)
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user (client should delete tokens).
    """
    # In production, add token to blacklist/revocation list
    # For MVP, just return success message

    return LogoutResponse(
        message=f"Successfully logged out user {current_user['email']}"
    )


@router.get(
    "/me",
    summary="Get Current User",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information.
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user["role"],
    }
