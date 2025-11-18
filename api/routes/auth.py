"""
Authentication and authorization routes
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from shared.models.database import get_db
from shared.models.models import User, UserRole
from shared.models.schemas import (
    Token,
    TokenRefresh,
    UserLogin,
    UserResponse,
    UserCreate,
)
from shared.auth.jwt import create_access_token, create_refresh_token, verify_token
from shared.auth.password import hash_password, verify_password
from shared.auth.dependencies import get_current_active_user, require_admin
from jwt.exceptions import InvalidTokenError
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username and password

    Returns JWT access and refresh tokens
    """
    # Get user from database
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    # Check if user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(
            "failed_login_attempt",
            username=credentials.username,
            ip=request.client.host if request.client else None,
        )

        # Update failed login attempts
        if user:
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(failed_login_attempts=User.failed_login_attempts + 1)
            )
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Update last login
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            last_login_at=datetime.utcnow(),
            last_login_ip=request.client.host if request.client else None,
            failed_login_attempts=0,  # Reset on successful login
        )
    )
    await db.commit()

    logger.info(
        "user_login_successful",
        username=user.username,
        user_id=user.id,
        ip=request.client.host if request.client else None,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token

    Returns new access and refresh tokens
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify refresh token
        payload = verify_token(token_data.refresh_token, token_type="refresh")
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception

    # Get user from database
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    # Generate new tokens
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    refresh_token = create_refresh_token(data={"sub": user.username})

    logger.info("token_refreshed", username=user.username, user_id=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user information

    Requires valid access token
    """
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
):
    """
    Logout current user

    Note: JWT tokens are stateless, so this is informational only.
    Client should delete the tokens.
    """
    logger.info("user_logout", username=current_user.username, user_id=current_user.id)

    return {
        "message": "Successfully logged out",
        "username": current_user.username,
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Register a new user (Admin only)

    Creates a new user account with the specified role
    """
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate role
    try:
        user_role = UserRole(user_data.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_role,
        is_active=True,
        is_superuser=False,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(
        "user_registered",
        username=new_user.username,
        user_id=new_user.id,
        role=new_user.role.value,
        created_by=current_admin.username,
    )

    return UserResponse.model_validate(new_user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    List all users (Admin only)

    Returns a paginated list of users
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()

    return [UserResponse.model_validate(user) for user in users]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    Delete a user (Admin only)

    Permanently removes a user account
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting yourself
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    await db.delete(user)
    await db.commit()

    logger.info(
        "user_deleted",
        username=user.username,
        user_id=user.id,
        deleted_by=current_admin.username,
    )

    return None
