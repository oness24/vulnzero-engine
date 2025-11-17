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

    # Application
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

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

    # Redis
    redis_url: str = Field(description="Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=50, description="Max Redis connections")

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

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", description="Anthropic model")
    anthropic_max_tokens: int = Field(default=4096, description="Max tokens for Anthropic")

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
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"


# Global settings instance
settings = Settings()
