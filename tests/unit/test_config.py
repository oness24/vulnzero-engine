"""Unit tests for configuration module."""
import pytest

from vulnzero.shared.config import get_settings


@pytest.mark.unit
def test_get_settings():
    """Test getting settings."""
    settings = get_settings()

    assert settings is not None
    assert settings.environment in ["development", "staging", "production"]
    assert settings.log_level is not None
    assert settings.database_url is not None


@pytest.mark.unit
def test_settings_are_cached():
    """Test that settings are cached."""
    settings1 = get_settings()
    settings2 = get_settings()

    # Should be the same instance
    assert settings1 is settings2


@pytest.mark.unit
def test_settings_validation():
    """Test settings validation."""
    settings = get_settings()

    # Check required fields
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "jwt_secret_key")
