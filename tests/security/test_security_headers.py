"""
Security Headers Middleware Tests

Tests for the SecurityHeadersMiddleware to ensure proper
security headers are applied to all HTTP responses.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from shared.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Test suite for SecurityHeadersMiddleware"""

    @pytest.fixture
    def app_development(self):
        """Create a test FastAPI app with development security headers"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, is_production=False)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        return app

    @pytest.fixture
    def app_production(self):
        """Create a test FastAPI app with production security headers"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, is_production=True)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        return app

    @pytest.fixture
    def client_dev(self, app_development):
        """Test client for development app"""
        return TestClient(app_development)

    @pytest.fixture
    def client_prod(self, app_production):
        """Test client for production app"""
        return TestClient(app_production)

    # ========================================================================
    # Development Mode Tests
    # ========================================================================

    def test_dev_mode_has_permissive_csp(self, client_dev):
        """Test that development mode has permissive CSP for HMR"""
        response = client_dev.get("/test")

        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers

        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp, "Dev CSP should allow unsafe-inline for HMR"
        assert "'unsafe-eval'" in csp, "Dev CSP should allow unsafe-eval for HMR"

    def test_dev_mode_no_hsts(self, client_dev):
        """Test that development mode does not set HSTS"""
        response = client_dev.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers, \
            "Development mode should not set HSTS"

    def test_dev_mode_has_basic_security_headers(self, client_dev):
        """Test that development mode still has basic security headers"""
        response = client_dev.get("/test")

        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    # ========================================================================
    # Production Mode Tests
    # ========================================================================

    def test_prod_mode_has_strict_csp(self, client_prod):
        """Test that production mode has strict CSP"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers

        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" not in csp, "Production CSP should not allow unsafe-inline"
        assert "'unsafe-eval'" not in csp, "Production CSP should not allow unsafe-eval"
        assert "default-src 'self'" in csp

    def test_prod_mode_has_hsts(self, client_prod):
        """Test that production mode sets HSTS"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers

        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts, "HSTS should have 1-year max-age"
        assert "includeSubDomains" in hsts
        assert "preload" in hsts

    def test_prod_mode_has_all_security_headers(self, client_prod):
        """Test that production mode has all required security headers"""
        response = client_prod.get("/test")

        assert response.status_code == 200

        # Check all security headers are present
        required_headers = [
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
            "X-XSS-Protection",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"

    def test_prod_mode_permissions_policy(self, client_prod):
        """Test that Permissions-Policy restricts dangerous features"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert "Permissions-Policy" in response.headers

        policy = response.headers["Permissions-Policy"]

        # Check that dangerous features are disabled
        restricted_features = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
        ]

        for feature in restricted_features:
            assert feature in policy, f"Permissions-Policy should restrict {feature}"

    # ========================================================================
    # Common Security Headers Tests
    # ========================================================================

    def test_x_frame_options_prevents_clickjacking(self, client_prod):
        """Test X-Frame-Options header prevents clickjacking"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert response.headers["X-Frame-Options"] == "DENY", \
            "X-Frame-Options should be DENY to prevent clickjacking"

    def test_x_content_type_options_prevents_mime_sniffing(self, client_prod):
        """Test X-Content-Type-Options prevents MIME-sniffing"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff", \
            "X-Content-Type-Options should be nosniff"

    def test_referrer_policy_minimizes_information_leak(self, client_prod):
        """Test Referrer-Policy minimizes information leakage"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin", \
            "Referrer-Policy should minimize information leakage"

    # ========================================================================
    # Edge Cases and Error Scenarios
    # ========================================================================

    def test_headers_applied_to_error_responses(self, client_prod):
        """Test that security headers are applied even to error responses"""
        response = client_prod.get("/nonexistent")

        assert response.status_code == 404

        # Security headers should still be present
        assert "X-Frame-Options" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_middleware_does_not_break_json_responses(self, client_prod):
        """Test that middleware doesn't interfere with JSON responses"""
        response = client_prod.get("/test")

        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    def test_headers_applied_to_multiple_requests(self, client_prod):
        """Test that headers are consistently applied across multiple requests"""
        for _ in range(5):
            response = client_prod.get("/test")
            assert response.status_code == 200
            assert "Content-Security-Policy" in response.headers
            assert "X-Frame-Options" in response.headers

    # ========================================================================
    # CSP Directive Tests
    # ========================================================================

    def test_csp_blocks_inline_scripts_in_production(self, client_prod):
        """Test that production CSP blocks inline scripts"""
        response = client_prod.get("/test")

        csp = response.headers["Content-Security-Policy"]

        # Parse CSP to check script-src directive
        assert "script-src 'self'" in csp, \
            "Production CSP should only allow scripts from same origin"

    def test_csp_allows_development_tools(self, client_dev):
        """Test that development CSP allows tools like Vite HMR"""
        response = client_dev.get("/test")

        csp = response.headers["Content-Security-Policy"]

        # Development should allow WebSocket for HMR
        assert "connect-src" in csp
        assert "ws:" in csp or "wss:" in csp, \
            "Development CSP should allow WebSocket for HMR"

    # ========================================================================
    # Regression Tests
    # ========================================================================

    def test_no_duplicate_headers(self, client_prod):
        """Test that middleware doesn't create duplicate headers"""
        response = client_prod.get("/test")

        # Check that each header appears only once
        for header in response.headers:
            header_values = response.headers.get_list(header)
            assert len(header_values) == 1, \
                f"Header {header} appears multiple times: {header_values}"

    def test_middleware_preserves_existing_headers(self, client_prod):
        """Test that middleware doesn't remove other headers"""
        response = client_prod.get("/test")

        # FastAPI should still set content-type
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


@pytest.mark.integration
class TestSecurityHeadersIntegration:
    """Integration tests for SecurityHeadersMiddleware"""

    def test_headers_with_real_api_endpoints(self, client_prod):
        """Test that headers work with various response types"""
        # This would test with actual API endpoints if available
        # For now, just verify the test endpoint works
        response = client_prod.get("/test")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
