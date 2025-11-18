"""
VulnZero - Application Settings
Configuration management using Pydantic Settings
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn
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
    # Application
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of API workers")
    api_secret_key: str = Field(description="Secret key for JWT signing")
    api_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000", description="Comma-separated CORS origins")
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Database
    database_url: str = Field(description="Database connection URL")
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max database overflow connections")
    database_echo: bool = Field(default=False, description="Echo SQL queries")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format"""
        if not v or not v.strip():
            raise ValueError("database_url is required and cannot be empty")
        if not v.startswith('postgresql'):
            raise ValueError("database_url must use PostgreSQL (postgresql:// or postgresql+asyncpg://)")
        return v

    # Redis
    redis_url: str = Field(description="Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=50, description="Max Redis connections")

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format"""
        if not v or not v.strip():
            raise ValueError("redis_url is required and cannot be empty")
        if not v.startswith('redis://'):
            raise ValueError("redis_url must start with redis://")
        return v

    # Celery
    celery_broker_url: str = Field(description="Celery broker URL")
    celery_result_backend: str = Field(description="Celery result backend URL")
    celery_task_track_started: bool = Field(default=True, description="Track task started events")
    celery_task_time_limit: int = Field(default=3600, description="Task time limit in seconds")
    celery_task_soft_time_limit: int = Field(default=3300, description="Task soft time limit in seconds")

    # AI/LLM Configuration
    llm_provider: str = Field(default="openai", description="LLM provider (openai or anthropic)")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_max_tokens: int = Field(default=4096, description="Max tokens for OpenAI")
    openai_temperature: float = Field(default=0.2, description="Temperature for OpenAI")

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate OpenAI API key if LLM provider is OpenAI"""
        # Check if this is the primary LLM provider
        if v and len(v) < 20:
            raise ValueError("openai_api_key must be at least 20 characters if provided")
        return v

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")
    anthropic_max_tokens: int = Field(default=4096, description="Max tokens for Anthropic")

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate Anthropic API key"""
        if v and len(v) < 20:
            raise ValueError("anthropic_api_key must be at least 20 characters if provided")
        return v

    # Vulnerability Scanners
    # Wazuh
    wazuh_api_url: Optional[str] = Field(default=None, description="Wazuh API URL")
    wazuh_api_user: Optional[str] = Field(default=None, description="Wazuh API user")
    wazuh_api_password: Optional[str] = Field(default=None, description="Wazuh API password")
    wazuh_verify_ssl: bool = Field(default=True, description="Verify SSL for Wazuh")

    # Qualys
    qualys_api_url: Optional[str] = Field(default=None, description="Qualys API URL")
    qualys_username: Optional[str] = Field(default=None, description="Qualys username")
    qualys_password: Optional[str] = Field(default=None, description="Qualys password")

    # Tenable
    tenable_access_key: Optional[str] = Field(default=None, description="Tenable access key")
    tenable_secret_key: Optional[str] = Field(default=None, description="Tenable secret key")

    # NVD
    nvd_api_key: Optional[str] = Field(default=None, description="NVD API key")
    nvd_api_url: str = Field(default="https://services.nvd.nist.gov/rest/json/cves/2.0", description="NVD API URL")

    # EPSS
    epss_api_url: str = Field(default="https://api.first.org/data/v1/epss", description="EPSS API URL")

    # Docker
    docker_host: str = Field(default="unix:///var/run/docker.sock", description="Docker host")
    docker_api_version: str = Field(default="auto", description="Docker API version")
    docker_timeout: int = Field(default=300, description="Docker timeout in seconds")

    # Kubernetes
    kubernetes_config_path: Optional[str] = Field(default=None, description="Kubernetes config path")
    kubernetes_namespace: str = Field(default="vulnzero", description="Kubernetes namespace")

    # Ansible
    ansible_private_key_path: Optional[str] = Field(default=None, description="Ansible private key path")
    ansible_host_key_checking: bool = Field(default=False, description="Ansible host key checking")
    ansible_timeout: int = Field(default=300, description="Ansible timeout in seconds")

    # Terraform
    terraform_binary_path: str = Field(default="/usr/local/bin/terraform", description="Terraform binary path")
    terraform_workspace_dir: str = Field(default="/var/lib/vulnzero/terraform", description="Terraform workspace dir")

    # AWS
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_s3_bucket: Optional[str] = Field(default=None, description="AWS S3 bucket")

    # Monitoring
    prometheus_multiproc_dir: str = Field(default="/tmp/prometheus_multiproc", description="Prometheus multiproc dir")
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    grafana_url: str = Field(default="http://localhost:3001", description="Grafana URL")
    grafana_api_key: Optional[str] = Field(default=None, description="Grafana API key")

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317", description="OTEL endpoint")
    otel_service_name: str = Field(default="vulnzero", description="OTEL service name")
    otel_traces_exporter: str = Field(default="otlp", description="OTEL traces exporter")
    otel_metrics_exporter: str = Field(default="otlp", description="OTEL metrics exporter")

    # Notifications
    # Slack
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL")
    slack_channel: str = Field(default="#vulnzero-alerts", description="Slack channel")

    # Email
    smtp_host: Optional[str] = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default=None, description="SMTP user")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    smtp_from: Optional[str] = Field(default=None, description="SMTP from address")
    smtp_tls: bool = Field(default=True, description="SMTP TLS")

    # PagerDuty
    pagerduty_api_key: Optional[str] = Field(default=None, description="PagerDuty API key")
    pagerduty_service_id: Optional[str] = Field(default=None, description="PagerDuty service ID")

    # Security
    allowed_hosts: str = Field(default="localhost,127.0.0.1,0.0.0.0", description="Allowed hosts")
    trusted_proxies: str = Field(default="127.0.0.1", description="Trusted proxies")

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parse allowed hosts into a list"""
        return [host.strip() for host in self.allowed_hosts.split(",")]

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    rate_limit_per_hour: int = Field(default=1000, description="Rate limit per hour")

    # Deployment Settings
    deployment_strategy: str = Field(default="canary", description="Deployment strategy")
    deployment_health_check_timeout: int = Field(default=300, description="Health check timeout")
    deployment_rollback_enabled: bool = Field(default=True, description="Enable rollback")
    deployment_max_parallel: int = Field(default=10, description="Max parallel deployments")

    @field_validator("deployment_strategy")
    @classmethod
    def validate_deployment_strategy(cls, v: str) -> str:
        """Validate deployment strategy"""
        allowed = ["blue-green", "canary", "rolling", "all-at-once"]
        if v not in allowed:
            raise ValueError(f"deployment_strategy must be one of {allowed}")
        return v

    # Digital Twin Testing
    testing_timeout: int = Field(default=600, description="Testing timeout in seconds")
    testing_parallel_limit: int = Field(default=5, description="Parallel testing limit")
    testing_container_cpu_limit: int = Field(default=2, description="Container CPU limit")
    testing_container_memory_limit: str = Field(default="4g", description="Container memory limit")

    # Patch Generation
    patch_confidence_threshold: float = Field(default=0.8, description="Patch confidence threshold")
    patch_validation_enabled: bool = Field(default=True, description="Enable patch validation")
    patch_cache_ttl: int = Field(default=86400, description="Patch cache TTL in seconds")

    # Monitoring & Rollback
    monitoring_window_seconds: int = Field(default=900, description="Monitoring window in seconds")
    anomaly_detection_threshold: float = Field(default=2.0, description="Anomaly detection threshold")
    auto_rollback_enabled: bool = Field(default=True, description="Enable auto rollback")
    rollback_on_error_rate_increase: float = Field(default=0.5, description="Rollback on error rate increase")

    # Scanning
    scan_interval_hours: int = Field(default=6, description="Scan interval in hours")
    scan_timeout: int = Field(default=3600, description="Scan timeout in seconds")
    vulnerability_cache_ttl: int = Field(default=3600, description="Vulnerability cache TTL")

    # Audit & Compliance
    audit_log_retention_days: int = Field(default=90, description="Audit log retention days")
    enable_audit_logging: bool = Field(default=True, description="Enable audit logging")
    audit_log_path: str = Field(default="/var/log/vulnzero/audit.log", description="Audit log path")

    # Feature Flags
    feature_auto_remediation: bool = Field(default=True, description="Enable auto remediation")
    feature_manual_approval_required: bool = Field(default=False, description="Require manual approval")
    feature_critical_vuln_auto_approve: bool = Field(default=True, description="Auto approve critical vulns")
    feature_ml_prioritization: bool = Field(default=True, description="Enable ML prioritization")

    # Development/Testing
    enable_swagger_ui: bool = Field(default=True, description="Enable Swagger UI")
    enable_redoc: bool = Field(default=True, description="Enable ReDoc")
    mock_scanner_apis: bool = Field(default=False, description="Mock scanner APIs")
    mock_llm_apis: bool = Field(default=False, description="Mock LLM APIs")

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() == "development"
        return self.environment == "development"


# Global settings instance
settings = Settings()
