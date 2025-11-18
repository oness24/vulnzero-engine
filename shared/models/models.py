"""
Database models for VulnZero
"""

from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey,
    Index, CheckConstraint, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.models.database import Base


# Enums
class VulnerabilityStatus(str, PyEnum):
    """Vulnerability remediation status"""
    NEW = "new"
    ANALYZING = "analyzing"
    PATCH_GENERATED = "patch_generated"
    TESTING = "testing"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    REMEDIATED = "remediated"
    FAILED = "failed"
    REJECTED = "rejected"


class VulnerabilitySeverity(str, PyEnum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AssetType(str, PyEnum):
    """Asset types"""
    SERVER = "server"
    CONTAINER = "container"
    CLOUD_INSTANCE = "cloud_instance"
    VIRTUAL_MACHINE = "virtual_machine"
    NETWORK_DEVICE = "network_device"


class TestStatus(str, PyEnum):
    """Patch test status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeploymentStatus(str, PyEnum):
    """Deployment status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentMethod(str, PyEnum):
    """Deployment methods"""
    ANSIBLE = "ansible"
    TERRAFORM = "terraform"
    SSH = "ssh"
    KUBERNETES = "kubernetes"
    MANUAL = "manual"


class JobStatus(str, PyEnum):
    """Job status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class UserRole(str, PyEnum):
    """User roles for access control"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


# Models
class User(Base):
    """User model - authentication and authorization"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Role-based access control
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False,
        index=True
    )

    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index("ix_user_role_active", "role", "is_active"),
    )



class Vulnerability(Base):
    """Vulnerability model - stores detected vulnerabilities"""
    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cve_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    severity: Mapped[VulnerabilitySeverity] = mapped_column(
        Enum(VulnerabilitySeverity),
        nullable=False,
        index=True
    )
    status: Mapped[VulnerabilityStatus] = mapped_column(
        Enum(VulnerabilityStatus),
        default=VulnerabilityStatus.NEW,
        nullable=False,
        index=True
    )

    cvss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cvss_vector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    epss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)

    # Vulnerability details
    affected_package: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    vulnerable_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # External references
    nvd_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exploit_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exploit_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Scanner information
    scanner_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_scanner_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    remediated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    patches: Mapped[list["Patch"]] = relationship("Patch", back_populates="vulnerability", cascade="all, delete-orphan")
    affected_assets: Mapped[list["AssetVulnerability"]] = relationship(
        "AssetVulnerability",
        back_populates="vulnerability",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_vuln_severity_status", "severity", "status"),
        Index("ix_vuln_priority_score", "priority_score"),
    )


class Asset(Base):
    """Asset model - infrastructure components"""
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    type: Mapped[AssetType] = mapped_column(Enum(AssetType), nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)

    # OS Information
    os_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os_architecture: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Asset metadata
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    criticality: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1-10 scale
    environment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # prod, staging, dev

    # Connection details (encrypted in production)
    ssh_user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_scanned: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    vulnerabilities: Mapped[list["AssetVulnerability"]] = relationship(
        "AssetVulnerability",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="asset")

    __table_args__ = (
        Index("ix_asset_type_active", "type", "is_active"),
        CheckConstraint("criticality >= 1 AND criticality <= 10", name="check_criticality_range"),
    )


class AssetVulnerability(Base):
    """Association table for assets and vulnerabilities"""
    __tablename__ = "asset_vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    vulnerability_id: Mapped[int] = mapped_column(Integer, ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False)

    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="vulnerabilities")
    vulnerability: Mapped["Vulnerability"] = relationship("Vulnerability", back_populates="affected_assets")

    __table_args__ = (
        Index("ix_asset_vuln_unique", "asset_id", "vulnerability_id", unique=True),
    )


class Patch(Base):
    """Patch model - generated remediation patches"""
    __tablename__ = "patches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    vulnerability_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Patch content
    patch_type: Mapped[str] = mapped_column(String(50), nullable=False)  # script, ansible, terraform
    patch_content: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LLM generation details
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validation
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Testing
    test_status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus),
        default=TestStatus.PENDING,
        nullable=False,
        index=True
    )
    test_results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Approval
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    vulnerability: Mapped["Vulnerability"] = relationship("Vulnerability", back_populates="patches")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="patch")

    __table_args__ = (
        Index("ix_patch_test_status", "test_status"),
        Index("ix_patch_confidence", "confidence_score"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="check_confidence_range"),
    )


class Deployment(Base):
    """Deployment model - tracks patch deployments"""
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deployment_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    patch_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Deployment details
    deployment_method: Mapped[DeploymentMethod] = mapped_column(
        Enum(DeploymentMethod),
        nullable=False
    )
    deployment_strategy: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus),
        default=DeploymentStatus.PENDING,
        nullable=False,
        index=True
    )

    # Execution details
    execution_logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Monitoring
    baseline_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    post_deployment_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    anomalies_detected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Rollback
    rollback_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rolled_back_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    patch: Mapped["Patch"] = relationship("Patch", back_populates="deployments")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="deployments")

    __table_args__ = (
        Index("ix_deployment_status_started", "status", "started_at"),
    )


class AuditLog(Base):
    """Audit log model - immutable audit trail"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Actor (user or system)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, system, api
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Result
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_timestamp_actor", "timestamp", "actor_id"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )


class RemediationJob(Base):
    """Remediation job model - async job tracking"""
    __tablename__ = "remediation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=5, nullable=False, index=True)

    # Job data
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Celery task info
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index("ix_job_status_priority", "status", "priority"),
        Index("ix_job_type_status", "job_type", "status"),
        CheckConstraint("priority >= 1 AND priority <= 10", name="check_priority_range"),
    )
