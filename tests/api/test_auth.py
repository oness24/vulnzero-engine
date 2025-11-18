"""
Tests for authentication endpoints
"""

import pytest
from httpx import AsyncClient
from jose import jwt

from shared.config import settings
from services.api_gateway.auth import create_access_token, create_refresh_token, decode_token


def test_create_access_token():
    """Test JWT access token creation"""
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)

    # Decode and verify
    payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
    assert payload["sub"] == "testuser"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_create_refresh_token():
    """Test JWT refresh token creation"""
    data = {"sub": "testuser", "role": "admin"}
    token = create_refresh_token(data)

    assert token is not None
    assert isinstance(token, str)

    # Decode and verify
    payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
    assert payload["sub"] == "testuser"
    assert payload["type"] == "refresh"


def test_decode_valid_token():
    """Test decoding a valid token"""
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)

    payload = decode_token(token)

    assert payload["sub"] == "testuser"
    assert payload["role"] == "admin"


def test_decode_invalid_token():
    """Test decoding an invalid token raises exception"""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid.token.here")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong_password"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    """Test refreshing access token"""
    # First, login to get tokens
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    tokens = login_response.json()

    # Use refresh token to get new access token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test refreshing with invalid refresh token"""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """Test that using access token for refresh fails"""
    # Get access token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    tokens = login_response.json()

    # Try to use access token as refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},  # Wrong token type
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Test logout endpoint"""
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token"""
    response = await client.get("/api/v1/vulnerabilities")

    assert response.status_code == 403  # Forbidden without auth


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient, auth_headers: dict):
    """Test accessing protected endpoint with valid token"""
    response = await client.get("/api/v1/vulnerabilities", headers=auth_headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token"""
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = await client.get("/api/v1/vulnerabilities", headers=headers)

    assert response.status_code == 401
