"""Application configuration and settings."""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: str = Field(default="development", description="Environment: development, staging, production")
    log_level: str = Field(default="INFO", description="Logging level")
    api_port: int = Field(default=8000, description="API server port")
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL for CORS")

    # Database
    database_url: str = Field(
        default="postgresql://vulnzero:password@localhost:5432/vulnzero",
        description="PostgreSQL database URL",
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )

    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Anthropic model to use"
    )
    llm_provider: str = Field(
        default="openai", description="LLM provider to use: openai or anthropic"
    )

    # Vulnerability Scanners
    wazuh_api_url: Optional[str] = Field(default=None, description="Wazuh API URL")
    wazuh_api_username: Optional[str] = Field(default=None, description="Wazuh API username")
    wazuh_api_password: Optional[str] = Field(default=None, description="Wazuh API password")

    qualys_api_url: Optional[str] = Field(default=None, description="Qualys API URL")
    qualys_username: Optional[str] = Field(default=None, description="Qualys username")
    qualys_password: Optional[str] = Field(default=None, description="Qualys password")

    tenable_access_key: Optional[str] = Field(default=None, description="Tenable access key")
    tenable_secret_key: Optional[str] = Field(default=None, description="Tenable secret key")

    # Security
    jwt_secret_key: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        description="JWT secret key",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=30, description="JWT token expiration in minutes")

    # API Authentication
    api_keys: list[str] = Field(
        default_factory=list, description="List of valid API keys for authentication"
    )
    require_auth_in_dev: bool = Field(
        default=False, description="Require API key authentication in development mode"
    )

    # Docker
    docker_host: str = Field(
        default="unix:///var/run/docker.sock", description="Docker daemon socket"
    )

    # Deployment
    ansible_vault_password: Optional[str] = Field(
        default=None, description="Ansible vault password"
    )
    ssh_key_path: Optional[str] = Field(default=None, description="SSH private key path")

    # Monitoring
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    grafana_port: int = Field(default=3001, description="Grafana dashboard port")

    # Notifications
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    smtp_host: Optional[str] = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    alert_email: Optional[str] = Field(
        default=None, description="Email address for critical alerts"
    )

    # Feature flags
    enable_auto_deployment: bool = Field(
        default=False, description="Enable automatic deployment without human approval"
    )
    enable_auto_rollback: bool = Field(
        default=True, description="Enable automatic rollback on anomaly detection"
    )
    enable_ml_prioritization: bool = Field(
        default=False, description="Enable ML-based vulnerability prioritization"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()
