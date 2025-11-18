"""
VulnZero Configuration Settings
Centralized configuration management using Pydantic Settings
"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ========================================================================
    # Application Settings
    # ========================================================================
    app_name: str = Field(default="VulnZero", description="Application name")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    # ========================================================================
    # Database Configuration
    # ========================================================================
    database_url: str = Field(
        default="postgresql://vulnzero:vulnzero_dev_password@localhost:5432/vulnzero",
        description="PostgreSQL connection URL"
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Max overflow connections")
    database_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    database_echo: bool = Field(default=False, description="Echo SQL queries")

    # ========================================================================
    # Redis Configuration
    # ========================================================================
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    cache_ttl_short: int = Field(default=300, description="Short cache TTL (5 minutes)")
    cache_ttl_medium: int = Field(default=3600, description="Medium cache TTL (1 hour)")
    cache_ttl_long: int = Field(default=86400, description="Long cache TTL (24 hours)")

    # ========================================================================
    # Celery Configuration
    # ========================================================================
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )
    celery_task_time_limit: int = Field(default=3600, description="Task time limit in seconds")
    celery_worker_concurrency: int = Field(default=4, description="Worker concurrency")

    # ========================================================================
    # JWT Authentication
    # ========================================================================
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="JWT secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration")

    # ========================================================================
    # AI/LLM Configuration
    # ========================================================================
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")
    openai_max_tokens: int = Field(default=2000, description="Max tokens per request")
    openai_temperature: float = Field(default=0.3, description="Temperature for generation")
    openai_timeout: int = Field(default=60, description="API timeout in seconds")

    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")
    anthropic_max_tokens: int = Field(default=2000, description="Max tokens per request")
    anthropic_temperature: float = Field(default=0.3, description="Temperature for generation")

    llm_provider: str = Field(default="openai", description="LLM provider: openai or anthropic")
    llm_fallback_enabled: bool = Field(default=True, description="Enable LLM fallback")
    llm_max_retries: int = Field(default=3, description="Max retry attempts")
    llm_retry_delay: int = Field(default=2, description="Retry delay in seconds")

    # ========================================================================
    # Scanner Integration
    # ========================================================================
    wazuh_api_url: Optional[str] = Field(default=None, description="Wazuh API URL")
    wazuh_api_username: Optional[str] = Field(default=None, description="Wazuh username")
    wazuh_api_password: Optional[str] = Field(default=None, description="Wazuh password")
    wazuh_verify_ssl: bool = Field(default=True, description="Verify SSL for Wazuh")
    wazuh_timeout: int = Field(default=30, description="Wazuh API timeout")

    nvd_api_key: Optional[str] = Field(default=None, description="NVD API key")
    nvd_api_url: str = Field(
        default="https://services.nvd.nist.gov/rest/json/cves/2.0",
        description="NVD API URL"
    )
    nvd_rate_limit: int = Field(default=5, description="NVD rate limit per second")

    # ========================================================================
    # Monitoring & Metrics
    # ========================================================================
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    prometheus_metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")

    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    sentry_environment: str = Field(default="development", description="Sentry environment")
    sentry_traces_sample_rate: float = Field(default=0.1, description="Sentry traces sample rate")

    # ========================================================================
    # Notifications
    # ========================================================================
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from_email: str = Field(default="noreply@vulnzero.com", description="From email")
    smtp_use_tls: bool = Field(default=True, description="Use TLS for SMTP")

    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    slack_channel: str = Field(default="#vulnzero-alerts", description="Slack channel")

    # ========================================================================
    # Docker Configuration
    # ========================================================================
    docker_host: str = Field(default="unix:///var/run/docker.sock", description="Docker host")
    digital_twin_cpu_limit: int = Field(default=2, description="Digital twin CPU limit")
    digital_twin_memory_limit: str = Field(default="4g", description="Digital twin memory limit")
    digital_twin_timeout: int = Field(default=600, description="Digital twin timeout in seconds")

    # ========================================================================
    # Deployment Configuration
    # ========================================================================
    deployment_strategy: str = Field(
        default="blue-green",
        description="Deployment strategy: blue-green, canary, rolling, all-at-once"
    )
    deployment_timeout: int = Field(default=1800, description="Deployment timeout in seconds")
    deployment_rollback_enabled: bool = Field(default=True, description="Enable automatic rollback")
    deployment_approval_required: bool = Field(
        default=False,
        description="Require manual approval"
    )

    canary_initial_percentage: int = Field(default=10, description="Initial canary percentage")
    canary_increment: int = Field(default=40, description="Canary increment percentage")
    canary_wait_time: int = Field(default=900, description="Wait time between increments")

    # ========================================================================
    # Security Settings
    # ========================================================================
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute")
    rate_limit_burst: int = Field(default=10, description="Burst limit")

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="CORS allowed origins (comma-separated)"
    )
    cors_credentials: bool = Field(default=True, description="Allow credentials in CORS")

    session_secret_key: str = Field(
        default="your-session-secret-key-change-in-production",
        description="Session secret key"
    )
    session_cookie_secure: bool = Field(default=False, description="Secure session cookies")
    session_cookie_httponly: bool = Field(default=True, description="HTTPOnly session cookies")

    # ========================================================================
    # Machine Learning Configuration
    # ========================================================================
    ml_model_path: str = Field(
        default="/app/models/prioritization_model.pkl",
        description="ML model path"
    )
    ml_training_enabled: bool = Field(default=False, description="Enable ML training")
    ml_retraining_interval_days: int = Field(default=7, description="Retraining interval")

    # ========================================================================
    # Feature Flags
    # ========================================================================
    feature_auto_remediation: bool = Field(default=True, description="Enable auto remediation")
    feature_digital_twin_testing: bool = Field(default=True, description="Enable digital twin testing")
    feature_canary_deployments: bool = Field(default=True, description="Enable canary deployments")
    feature_ml_prioritization: bool = Field(default=True, description="Enable ML prioritization")
    feature_audit_logging: bool = Field(default=True, description="Enable audit logging")

    # ========================================================================
    # Testing Configuration
    # ========================================================================
    test_database_url: Optional[str] = Field(
        default=None,
        description="Test database URL"
    )
    pytest_workers: str = Field(default="auto", description="Pytest workers")
    coverage_threshold: int = Field(default=80, description="Coverage threshold percentage")

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    log_format: str = Field(default="json", description="Log format: json or text")
    log_file_path: str = Field(default="/app/logs/vulnzero.log", description="Log file path")
    log_to_file: bool = Field(default=True, description="Log to file")
    log_to_console: bool = Field(default=True, description="Log to console")

    # ========================================================================
    # Miscellaneous
    # ========================================================================
    timezone: str = Field(default="UTC", description="Application timezone")
    max_upload_size: int = Field(default=10485760, description="Max upload size in bytes (10MB)")
    temp_dir: str = Field(default="/tmp/vulnzero", description="Temporary directory")

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()
