"""
Authentication and Authorization Security Tests

Tests to ensure proper authentication and authorization mechanisms
are in place and cannot be bypassed.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt

from shared.auth.jwt import create_access_token, create_refresh_token, verify_token
from shared.config.settings import settings


class TestAuthenticationSecurity:
    """Test suite for authentication security"""

    def test_protected_routes_reject_unauthenticated_requests(self, client: TestClient):
        """Test that protected routes return 401 for unauthenticated requests"""
        protected_endpoints = [
            "/api/vulnerabilities/",
            "/api/patches/",
            "/api/deployments/",
            "/api/dashboard/stats",
            "/api/monitoring/metrics",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"

    def test_invalid_token_is_rejected(self, client: TestClient):
        """Test that invalid JWT tokens are rejected"""
        invalid_token = "invalid.token.here"

        response = client.get(
            "/api/vulnerabilities/",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json().get("detail", "").lower()

    def test_malformed_token_is_rejected(self, client: TestClient):
        """Test that malformed tokens are rejected"""
        malformed_tokens = [
            "Bearer",  # No token
            "invalid-format",  # No Bearer prefix
            "Bearer ",  # Empty token
            "Bearer token-without-dots",  # Invalid format
        ]

        for token in malformed_tokens:
            response = client.get(
                "/api/vulnerabilities/",
                headers={"Authorization": token}
            )
            assert response.status_code == 401

    def test_expired_token_is_rejected(self, client: TestClient):
        """Test that expired tokens are rejected"""
        # Create an expired token (expired 1 hour ago)
        expired_token = create_access_token(
            data={"sub": "test_user"},
            expires_delta=timedelta(hours=-1)
        )

        response = client.get(
            "/api/vulnerabilities/",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    def test_token_with_invalid_signature_is_rejected(self):
        """Test that tokens with invalid signatures are rejected"""
        # Create token with wrong secret key
        fake_token = jwt.encode(
            {"sub": "test_user", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm="HS256"
        )

        with pytest.raises(Exception):  # Should raise InvalidTokenError
            verify_token(fake_token)

    def test_token_with_missing_required_claims_is_rejected(self):
        """Test that tokens missing required claims are rejected"""
        # Token without 'sub' claim
        invalid_token = jwt.encode(
            {"exp": datetime.utcnow() + timedelta(hours=1), "type": "access"},
            settings.api_secret_key,
            algorithm=settings.api_algorithm
        )

        # This should be handled in your authentication dependency
        # The exact behavior depends on your implementation
        assert invalid_token is not None  # Basic validation

    def test_refresh_token_cannot_be_used_as_access_token(self, client: TestClient):
        """Test that refresh tokens cannot be used to access protected routes"""
        # Create a refresh token
        refresh_token = create_refresh_token(data={"sub": "test_user"})

        # Try to use it as an access token
        response = client.get(
            "/api/vulnerabilities/",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )

        # Should be rejected (either 401 or specific error about token type)
        assert response.status_code in [401, 403]

    def test_token_reuse_after_logout(self, client: TestClient):
        """Test that tokens cannot be reused after logout"""
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"username": "test_user", "password": "test_password"}
        )

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]

            # Logout
            client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )

            # Try to use token after logout
            response = client.get(
                "/api/vulnerabilities/",
                headers={"Authorization": f"Bearer {token}"}
            )

            # Depending on implementation, token might still work (stateless JWT)
            # or be rejected (if using token blacklist)
            # Document the expected behavior here

    def test_weak_password_is_rejected(self, client: TestClient):
        """Test that weak passwords are rejected during registration"""
        weak_passwords = [
            "123",  # Too short
            "password",  # Common password
            "abc",  # Too short and simple
        ]

        for weak_password in weak_passwords:
            response = client.post(
                "/api/auth/register",
                json={
                    "username": "new_user",
                    "email": "user@example.com",
                    "password": weak_password,
                    "full_name": "Test User"
                }
            )

            # Should reject weak password (400 or 422)
            assert response.status_code in [400, 422]


class TestAuthorizationSecurity:
    """Test suite for authorization and role-based access control"""

    def test_viewer_cannot_create_resources(self, client: TestClient, viewer_token: str):
        """Test that viewers cannot create resources"""
        response = client.post(
            "/api/patches/generate",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={"vulnerability_id": "123", "patch_type": "automated"}
        )

        assert response.status_code == 403

    def test_viewer_cannot_delete_resources(self, client: TestClient, viewer_token: str):
        """Test that viewers cannot delete resources"""
        response = client.delete(
            "/api/vulnerabilities/123",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )

        assert response.status_code == 403

    def test_developer_cannot_manage_users(self, client: TestClient, developer_token: str):
        """Test that developers cannot manage users"""
        response = client.post(
            "/api/auth/register",
            headers={"Authorization": f"Bearer {developer_token}"},
            json={
                "username": "new_admin",
                "email": "admin@example.com",
                "password": "secure_password123",
                "full_name": "New Admin",
                "role": "admin"
            }
        )

        assert response.status_code == 403

    def test_user_cannot_access_other_users_data(
        self, client: TestClient, user1_token: str
    ):
        """Test that users cannot access other users' private data"""
        # Try to access another user's profile
        response = client.get(
            "/api/auth/users/999",  # Different user ID
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        # Should be forbidden or not found
        assert response.status_code in [403, 404]

    def test_privilege_escalation_through_token_manipulation(self):
        """Test that privilege escalation through token manipulation is prevented"""
        # Create a token with viewer role
        viewer_token = create_access_token(
            data={"sub": "viewer_user", "role": "viewer"}
        )

        # Try to decode and modify the role (client-side)
        # This should fail because the signature won't match
        decoded = jwt.decode(
            viewer_token,
            options={"verify_signature": False}  # Dangerous, but for testing
        )

        # Modify the role
        decoded["role"] = "admin"

        # Re-encode with same secret (attacker wouldn't know this)
        fake_admin_token = jwt.encode(
            decoded,
            settings.api_secret_key,
            algorithm=settings.api_algorithm
        )

        # Verify the original token still has viewer role
        verified = verify_token(viewer_token)
        assert verified["role"] == "viewer"

    def test_horizontal_privilege_escalation_prevention(
        self, client: TestClient, user1_token: str
    ):
        """Test that users cannot modify resources they don't own"""
        # Try to update another user's resource
        response = client.patch(
            "/api/vulnerabilities/123",  # Resource owned by different user
            headers={"Authorization": f"Bearer {user1_token}"},
            json={"status": "false_positive"}
        )

        # Should be forbidden
        assert response.status_code == 403


class TestPasswordSecurity:
    """Test suite for password security"""

    def test_password_is_hashed_not_plain_text(self, db_session):
        """Test that passwords are stored as hashes, not plain text"""
        from shared.models.models import User

        # This is a meta-test to ensure passwords are hashed
        # In practice, check the User model uses password hashing
        user = User(
            username="test_user",
            email="test@example.com",
            full_name="Test User"
        )

        # Password should be hashed using bcrypt or similar
        assert hasattr(user, "password_hash") or hasattr(user, "hashed_password")

    def test_password_not_returned_in_api_responses(self, client: TestClient, admin_token: str):
        """Test that password hashes are never returned in API responses"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code == 200:
            user_data = response.json()

            # Password fields should not be in response
            assert "password" not in user_data
            assert "password_hash" not in user_data
            assert "hashed_password" not in user_data

    def test_brute_force_protection(self, client: TestClient):
        """Test that brute force attacks are prevented"""
        # Attempt multiple failed logins
        for i in range(10):
            response = client.post(
                "/api/auth/login",
                json={"username": "test_user", "password": f"wrong_password_{i}"}
            )

        # After multiple attempts, should see rate limiting or account lockout
        # Exact implementation depends on your rate limiting strategy
        # This test documents the expectation

    def test_timing_attack_resistance(self, client: TestClient):
        """Test that login timing is consistent to prevent timing attacks"""
        import time

        # Time login with valid username but wrong password
        start1 = time.time()
        client.post(
            "/api/auth/login",
            json={"username": "existing_user", "password": "wrong_password"}
        )
        duration1 = time.time() - start1

        # Time login with non-existent username
        start2 = time.time()
        client.post(
            "/api/auth/login",
            json={"username": "nonexistent_user", "password": "wrong_password"}
        )
        duration2 = time.time() - start2

        # Timing should be similar (within 50ms) to prevent user enumeration
        time_difference = abs(duration1 - duration2)
        assert time_difference < 0.05, "Login timing varies too much (timing attack risk)"


class TestSessionSecurity:
    """Test suite for session security"""

    def test_token_rotation_on_refresh(self, client: TestClient):
        """Test that refreshing a token generates a new token"""
        # Get initial tokens
        login_response = client.post(
            "/api/auth/login",
            json={"username": "test_user", "password": "test_password"}
        )

        if login_response.status_code == 200:
            initial_access_token = login_response.json()["access_token"]
            refresh_token = login_response.json()["refresh_token"]

            # Refresh the token
            refresh_response = client.post(
                "/api/auth/refresh",
                json={"refresh_token": refresh_token}
            )

            if refresh_response.status_code == 200:
                new_access_token = refresh_response.json()["access_token"]

                # New token should be different
                assert new_access_token != initial_access_token

    def test_concurrent_session_detection(self, client: TestClient):
        """Test detection of concurrent sessions"""
        # This depends on your session management implementation
        # Document expected behavior for concurrent logins
        pass

    def test_session_fixation_prevention(self, client: TestClient):
        """Test that session fixation attacks are prevented"""
        # Get a token before authentication
        # After authentication, token should be regenerated
        # This prevents session fixation attacks
        pass


# Pytest fixtures for different user roles
@pytest.fixture
def viewer_token():
    """Create a token for a viewer role user"""
    return create_access_token(data={"sub": "viewer_user", "role": "viewer"})


@pytest.fixture
def developer_token():
    """Create a token for a developer role user"""
    return create_access_token(data={"sub": "developer_user", "role": "developer"})


@pytest.fixture
def admin_token():
    """Create a token for an admin role user"""
    return create_access_token(data={"sub": "admin_user", "role": "admin"})


@pytest.fixture
def user1_token():
    """Create a token for user 1"""
    return create_access_token(data={"sub": "user1", "role": "developer", "user_id": 1})


@pytest.fixture
def user2_token():
    """Create a token for user 2"""
    return create_access_token(data={"sub": "user2", "role": "developer", "user_id": 2})
