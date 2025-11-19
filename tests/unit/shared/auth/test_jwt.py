"""
JWT Token Tests

Comprehensive tests for JWT token generation, verification, and validation.
"""

import pytest
from datetime import datetime, timedelta
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
import jwt

from shared.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
    get_token_subject,
)
from shared.config.settings import settings


class TestJWTTokenCreation:
    """Tests for JWT token creation functions"""

    def test_create_access_token_with_default_expiration(self):
        """Test creating access token with default expiration"""
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token contents
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_custom_expiration(self):
        """Test creating access token with custom expiration time"""
        data = {"sub": "user123"}
        custom_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta=custom_delta)

        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])

        # Check that expiration is approximately 60 minutes from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        delta = exp_time - iat_time

        assert 59 <= delta.total_seconds() / 60 <= 61, "Expiration should be ~60 minutes"

    def test_create_access_token_includes_all_claims(self):
        """Test that access token includes all required claims"""
        data = {"sub": "user123", "username": "john_doe", "role": "operator"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])

        # Verify all original data is present
        assert payload["sub"] == "user123"
        assert payload["username"] == "john_doe"
        assert payload["role"] == "operator"

        # Verify automatic claims
        assert payload["type"] == "access"
        assert isinstance(payload["exp"], int)
        assert isinstance(payload["iat"], int)

    def test_create_refresh_token_with_default_expiration(self):
        """Test creating refresh token with default expiration"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_create_refresh_token_with_custom_expiration(self):
        """Test creating refresh token with custom expiration"""
        data = {"sub": "user123"}
        custom_delta = timedelta(days=14)
        token = create_refresh_token(data, expires_delta=custom_delta)

        payload = jwt.decode(token, settings.api_secret_key, algorithms=[settings.api_algorithm])

        # Check that expiration is approximately 14 days from now
        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])
        delta = exp_time - iat_time

        assert 13.9 <= delta.days <= 14.1, "Expiration should be ~14 days"

    def test_access_and_refresh_tokens_are_different(self):
        """Test that access and refresh tokens have different types"""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)

        access_payload = jwt.decode(access_token, settings.api_secret_key, algorithms=[settings.api_algorithm])
        refresh_payload = jwt.decode(refresh_token, settings.api_secret_key, algorithms=[settings.api_algorithm])

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_token != refresh_token


class TestJWTTokenDecoding:
    """Tests for JWT token decoding"""

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_decode_token_with_invalid_signature(self):
        """Test that invalid signature raises error"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        # Modify the token to invalidate signature
        parts = token.split('.')
        if len(parts) == 3:
            # Change one character in signature
            parts[2] = parts[2][:-1] + ('a' if parts[2][-1] != 'a' else 'b')
            invalid_token = '.'.join(parts)

            with pytest.raises(InvalidTokenError):
                decode_token(invalid_token)

    def test_decode_malformed_token(self):
        """Test that malformed token raises error"""
        with pytest.raises(InvalidTokenError):
            decode_token("this.is.not.a.valid.token")

    def test_decode_empty_token(self):
        """Test that empty token raises error"""
        with pytest.raises(InvalidTokenError):
            decode_token("")

    def test_decode_expired_token(self):
        """Test that expired token raises error"""
        data = {"sub": "user123"}
        # Create token that expired 1 second ago
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expired_delta)

        with pytest.raises(InvalidTokenError):
            decode_token(token)

    def test_decode_token_created_in_future(self):
        """Test handling of token with future iat (issued at) time"""
        # Manually create a token with future iat
        future_time = datetime.utcnow() + timedelta(hours=1)
        data = {
            "sub": "user123",
            "iat": future_time.timestamp(),
            "exp": (future_time + timedelta(minutes=30)).timestamp(),
            "type": "access"
        }

        token = jwt.encode(data, settings.api_secret_key, algorithm=settings.api_algorithm)

        # This should still decode (JWT doesn't validate iat by default)
        payload = decode_token(token)
        assert payload["sub"] == "user123"


class TestJWTTokenVerification:
    """Tests for JWT token verification"""

    def test_verify_access_token(self):
        """Test verifying a valid access token"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        payload = verify_token(token, token_type="access")

        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Test verifying a valid refresh token"""
        data = {"sub": "user123"}
        token = create_refresh_token(data)

        payload = verify_token(token, token_type="refresh")

        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_token_wrong_type_access_as_refresh(self):
        """Test that access token fails when verified as refresh"""
        data = {"sub": "user123"}
        access_token = create_access_token(data)

        with pytest.raises(InvalidTokenError) as exc_info:
            verify_token(access_token, token_type="refresh")

        assert "Invalid token type" in str(exc_info.value)
        assert "Expected refresh" in str(exc_info.value)

    def test_verify_token_wrong_type_refresh_as_access(self):
        """Test that refresh token fails when verified as access"""
        data = {"sub": "user123"}
        refresh_token = create_refresh_token(data)

        with pytest.raises(InvalidTokenError) as exc_info:
            verify_token(refresh_token, token_type="access")

        assert "Invalid token type" in str(exc_info.value)
        assert "Expected access" in str(exc_info.value)

    def test_verify_expired_token(self):
        """Test that expired token fails verification"""
        data = {"sub": "user123"}
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(InvalidTokenError):
            verify_token(expired_token, token_type="access")

    def test_verify_invalid_token(self):
        """Test that invalid token fails verification"""
        with pytest.raises(InvalidTokenError):
            verify_token("invalid.token.here", token_type="access")


class TestGetTokenSubject:
    """Tests for get_token_subject function"""

    def test_get_subject_from_valid_token(self):
        """Test extracting subject from valid token"""
        data = {"sub": "user123"}
        token = create_access_token(data)

        subject = get_token_subject(token)

        assert subject == "user123"

    def test_get_subject_from_token_without_sub(self):
        """Test extracting subject from token without sub claim"""
        data = {"username": "john_doe"}  # No 'sub' claim
        token = create_access_token(data)

        subject = get_token_subject(token)

        assert subject is None

    def test_get_subject_from_invalid_token(self):
        """Test that invalid token returns None"""
        subject = get_token_subject("invalid.token.here")

        assert subject is None

    def test_get_subject_from_expired_token(self):
        """Test that expired token returns None"""
        data = {"sub": "user123"}
        expired_token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        subject = get_token_subject(expired_token)

        assert subject is None

    def test_get_subject_from_empty_token(self):
        """Test that empty token returns None"""
        subject = get_token_subject("")

        assert subject is None


class TestJWTEdgeCases:
    """Edge case tests for JWT functions"""

    def test_token_with_unicode_data(self):
        """Test creating token with Unicode data"""
        data = {
            "sub": "user123",
            "name": "José González",
            "city": "São Paulo",
            "note": "测试"
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["name"] == "José González"
        assert payload["city"] == "São Paulo"
        assert payload["note"] == "测试"

    def test_token_with_special_characters(self):
        """Test creating token with special characters"""
        data = {
            "sub": "user@example.com",
            "role": "admin/operator",
            "note": "Test!@#$%^&*()"
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["sub"] == "user@example.com"
        assert payload["role"] == "admin/operator"

    def test_token_with_large_payload(self):
        """Test creating token with large payload"""
        data = {
            "sub": "user123",
            "permissions": ["perm" + str(i) for i in range(100)],
            "metadata": {"key" + str(i): "value" + str(i) for i in range(50)}
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert len(payload["permissions"]) == 100
        assert len(payload["metadata"]) == 50

    def test_token_with_nested_data(self):
        """Test creating token with nested data structures"""
        data = {
            "sub": "user123",
            "user_info": {
                "name": "John Doe",
                "email": "john@example.com",
                "roles": ["admin", "operator"],
                "metadata": {
                    "department": "engineering",
                    "level": 5
                }
            }
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["user_info"]["name"] == "John Doe"
        assert payload["user_info"]["metadata"]["department"] == "engineering"

    def test_token_with_boolean_and_numeric_values(self):
        """Test creating token with various data types"""
        data = {
            "sub": "user123",
            "is_active": True,
            "is_admin": False,
            "login_count": 42,
            "score": 95.5
        }
        token = create_access_token(data)

        payload = decode_token(token)
        assert payload["is_active"] is True
        assert payload["is_admin"] is False
        assert payload["login_count"] == 42
        assert payload["score"] == 95.5

    def test_multiple_tokens_same_data_are_different(self):
        """Test that multiple tokens with same data have different iat"""
        import time
        data = {"sub": "user123"}

        token1 = create_access_token(data)
        time.sleep(0.1)  # Wait to ensure different iat
        token2 = create_access_token(data)

        # Tokens should be different due to different iat
        assert token1 != token2

        payload1 = decode_token(token1)
        payload2 = decode_token(token2)

        # iat should be different
        assert payload1["iat"] != payload2["iat"]


@pytest.mark.security
class TestJWTSecurity:
    """Security-focused tests for JWT"""

    def test_token_cannot_be_modified_without_detection(self):
        """Test that modifying token payload is detected"""
        data = {"sub": "user123", "role": "viewer"}
        token = create_access_token(data)

        # Try to decode and modify
        parts = token.split('.')
        if len(parts) == 3:
            # Modify the payload (even though this won't have valid signature)
            import base64
            import json

            # This test verifies that signature verification catches tampering
            # We create a new token with modified data but wrong signature
            modified_payload = {"sub": "user123", "role": "admin"}  # Escalated role!
            modified_payload_bytes = json.dumps(modified_payload).encode()
            modified_payload_b64 = base64.urlsafe_b64encode(modified_payload_bytes).decode().rstrip('=')

            tampered_token = f"{parts[0]}.{modified_payload_b64}.{parts[2]}"

            with pytest.raises(InvalidTokenError):
                decode_token(tampered_token)

    def test_token_replay_attack_prevention(self):
        """Test that tokens have unique iat to prevent simple replay"""
        import time

        data = {"sub": "user123"}
        token1 = create_access_token(data)
        time.sleep(0.1)
        token2 = create_access_token(data)

        # Both tokens are valid but different
        payload1 = decode_token(token1)
        payload2 = decode_token(token2)

        assert payload1["iat"] < payload2["iat"]

    def test_token_expiration_is_enforced(self):
        """Test that token expiration is strictly enforced"""
        data = {"sub": "user123"}

        # Create token that expires in 1 second
        token = create_access_token(data, expires_delta=timedelta(seconds=1))

        # Token should be valid immediately
        payload = decode_token(token)
        assert payload["sub"] == "user123"

        # Wait for expiration
        import time
        time.sleep(2)

        # Token should now be expired
        with pytest.raises(InvalidTokenError):
            decode_token(token)
