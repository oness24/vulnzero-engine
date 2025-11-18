"""
Tests for configuration module
"""

import pytest
from pydantic import ValidationError
from shared.config.settings import Settings


def test_settings_default_values():
    """Test that settings can be created with default values"""
    # Create settings without environment variables
    settings = Settings(api_secret_key="test-secret-key")

    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.api_port == 8000
    assert settings.api_algorithm == "HS256"


def test_settings_custom_values():
    """Test that settings can be customized"""
    settings = Settings(
        environment="production",
        debug=False,
        api_secret_key="prod-secret-key",
        api_port=9000,
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        redis_url="redis://localhost:6379/0",
        celery_broker_url="redis://localhost:6379/1",
        celery_result_backend="redis://localhost:6379/2",
    )

    assert settings.environment == "production"
    assert settings.is_production is True
    assert settings.is_development is False
    assert settings.api_port == 9000


def test_settings_deployment_strategy_validation():
    """Test that deployment strategy is validated"""
    # Valid strategy
    settings = Settings(
        api_secret_key="test-secret",
        deployment_strategy="canary",
        database_url="postgresql+asyncpg://test",
        redis_url="redis://test",
        celery_broker_url="redis://test",
        celery_result_backend="redis://test",
    )
    assert settings.deployment_strategy == "canary"

    # Invalid strategy should raise error
    with pytest.raises(ValidationError):
        Settings(
            api_secret_key="test-secret",
            deployment_strategy="invalid-strategy",
            database_url="postgresql+asyncpg://test",
            redis_url="redis://test",
            celery_broker_url="redis://test",
            celery_result_backend="redis://test",
        )


def test_settings_cors_origins_parsing():
    """Test that CORS origins are parsed correctly"""
    settings = Settings(
        api_secret_key="test-secret",
        cors_origins="http://localhost:3000, http://localhost:8000, https://app.example.com",
        database_url="postgresql+asyncpg://test",
        redis_url="redis://test",
        celery_broker_url="redis://test",
        celery_result_backend="redis://test",
    )

    assert len(settings.cors_origins_list) == 3
    assert "http://localhost:3000" in settings.cors_origins_list
    assert "http://localhost:8000" in settings.cors_origins_list
    assert "https://app.example.com" in settings.cors_origins_list


def test_settings_allowed_hosts_parsing():
    """Test that allowed hosts are parsed correctly"""
    settings = Settings(
        api_secret_key="test-secret",
        allowed_hosts="localhost, 127.0.0.1, api.example.com",
        database_url="postgresql+asyncpg://test",
        redis_url="redis://test",
        celery_broker_url="redis://test",
        celery_result_backend="redis://test",
    )

    assert len(settings.allowed_hosts_list) == 3
    assert "localhost" in settings.allowed_hosts_list
    assert "127.0.0.1" in settings.allowed_hosts_list
    assert "api.example.com" in settings.allowed_hosts_list


def test_settings_llm_configuration():
    """Test LLM configuration settings"""
    settings = Settings(
        api_secret_key="test-secret",
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        anthropic_model="claude-3-opus-20240229",
        database_url="postgresql+asyncpg://test",
        redis_url="redis://test",
        celery_broker_url="redis://test",
        celery_result_backend="redis://test",
    )

    assert settings.llm_provider == "anthropic"
    assert settings.anthropic_api_key == "test-key"
    assert settings.anthropic_model == "claude-3-opus-20240229"


def test_settings_feature_flags():
    """Test feature flag settings"""
    settings = Settings(
        api_secret_key="test-secret",
        feature_auto_remediation=True,
        feature_manual_approval_required=False,
        feature_critical_vuln_auto_approve=True,
        feature_ml_prioritization=True,
        database_url="postgresql+asyncpg://test",
        redis_url="redis://test",
        celery_broker_url="redis://test",
        celery_result_backend="redis://test",
    )

    assert settings.feature_auto_remediation is True
    assert settings.feature_manual_approval_required is False
    assert settings.feature_critical_vuln_auto_approve is True
    assert settings.feature_ml_prioritization is True
