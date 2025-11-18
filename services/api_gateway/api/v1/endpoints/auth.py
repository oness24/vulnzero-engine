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

router = APIRouter()

# Demo users for MVP (replace with database User model in production)
DEMO_USERS = {
    "admin@vulnzero.com": {
        "id": "1",
        "email": "admin@vulnzero.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7667fJmFni",  # password: Admin123!
        "role": "admin",
        "name": "Admin User",
    },
    "operator@vulnzero.com": {
        "id": "2",
        "email": "operator@vulnzero.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7667fJmFni",  # password: Operator123!
        "role": "operator",
        "name": "Operator User",
    },
    "viewer@vulnzero.com": {
        "id": "3",
        "email": "viewer@vulnzero.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7667fJmFni",  # password: Viewer123!
        "role": "viewer",
        "name": "Viewer User",
    },
}


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
    # Get user from demo users (replace with database query)
    user = DEMO_USERS.get(login_data.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": user["id"]})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "name": user["name"],
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
async def refresh_token(refresh_data: TokenRefreshRequest):
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

    # Find user (in demo, search by ID)
    user = None
    for email, user_data in DEMO_USERS.items():
        if user_data["id"] == user_id:
            user = user_data
            break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new access token
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
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
