"""
VulnZero - Audit Log Model
Immutable audit trail for all system actions
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON, Enum, Index
)
import enum

from shared.models.base import Base


class AuditAction(str, enum.Enum):
    """Audit action enumeration"""
    # Vulnerability actions
    VULNERABILITY_DISCOVERED = "vulnerability_discovered"
    VULNERABILITY_UPDATED = "vulnerability_updated"
    VULNERABILITY_REMEDIATED = "vulnerability_remediated"
    VULNERABILITY_IGNORED = "vulnerability_ignored"

    # Patch actions
    PATCH_GENERATED = "patch_generated"
    PATCH_VALIDATED = "patch_validated"
    PATCH_TESTED = "patch_tested"
    PATCH_APPROVED = "patch_approved"
    PATCH_REJECTED = "patch_rejected"

    # Deployment actions
    DEPLOYMENT_SCHEDULED = "deployment_scheduled"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_ROLLED_BACK = "deployment_rolled_back"
    DEPLOYMENT_ROLLBACK_COMPLETED = "deployment_rollback_completed"
    DEPLOYMENT_ROLLBACK_FAILED = "deployment_rollback_failed"
    DEPLOYMENT_CANCELLED = "deployment_cancelled"

    # Asset actions
    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_SCANNED = "asset_scanned"
    ASSET_DECOMMISSIONED = "asset_decommissioned"

    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"

    # Configuration actions
    CONFIG_CHANGED = "config_changed"
    SCANNER_CONFIGURED = "scanner_configured"
    SETTINGS_UPDATED = "settings_updated"

    # Security actions
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ACCESS_DENIED = "access_denied"
    AUTH_FAILED = "auth_failed"

    # System actions
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    BACKUP_CREATED = "backup_created"
    RESTORE_PERFORMED = "restore_performed"


class AuditResourceType(str, enum.Enum):
    """Resource type enumeration"""
    VULNERABILITY = "vulnerability"
    ASSET = "asset"
    PATCH = "patch"
    DEPLOYMENT = "deployment"
    USER = "user"
    SCANNER = "scanner"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    REMEDIATION_JOB = "remediation_job"


class AuditLog(Base):
    """
    Audit Log Model - Immutable audit trail for all system actions.

    This table records all significant actions in the system for compliance,
    security, and debugging purposes. Records are immutable once created.
    """

    __tablename__ = "audit_logs"

    # Override updated_at to make it immutable (same as created_at)
    # Audit logs should never be updated
    updated_at = None

    # ========================================================================
    # Action Information
    # ========================================================================
    action = Column(
        Enum(AuditAction),
        nullable=False,
        index=True,
        comment="Action that was performed"
    )

    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the action occurred (high precision)"
    )

    # ========================================================================
    # Actor Information (Who)
    # ========================================================================
    actor_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of actor: user, system, api_client, service"
    )

    actor_id = Column(
        String(200),
        nullable=False,
        index=True,
        comment="Identifier of the actor (user ID, service name, etc.)"
    )

    actor_name = Column(
        String(200),
        nullable=True,
        comment="Human-readable name of the actor"
    )

    actor_ip = Column(
        String(45),
        nullable=True,
        index=True,
        comment="IP address of the actor (if applicable)"
    )

    actor_user_agent = Column(
        String(500),
        nullable=True,
        comment="User agent string (for web/API requests)"
    )

    # ========================================================================
    # Resource Information (What)
    # ========================================================================
    resource_type = Column(
        Enum(AuditResourceType),
        nullable=False,
        index=True,
        comment="Type of resource affected"
    )

    resource_id = Column(
        String(200),
        nullable=False,
        index=True,
        comment="ID of the resource affected"
    )

    resource_name = Column(
        String(500),
        nullable=True,
        comment="Human-readable name of the resource"
    )

    # ========================================================================
    # Action Details
    # ========================================================================
    description = Column(
        Text,
        nullable=False,
        comment="Human-readable description of the action"
    )

    success = Column(
        Integer,
        nullable=False,
        default=1,
        index=True,
        comment="Whether the action was successful (1=yes, 0=no)"
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if action failed"
    )

    # ========================================================================
    # Context & Details
    # ========================================================================
    details = Column(
        JSON,
        nullable=True,
        comment="Detailed information about the action (structured data)"
    )

    changes = Column(
        JSON,
        nullable=True,
        comment="Before/after state for updates (e.g., field changes)"
    )

    audit_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional context metadata"
    )

    # ========================================================================
    # Request Information (for API calls)
    # ========================================================================
    request_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Request ID for correlation (trace ID)"
    )

    request_method = Column(
        String(10),
        nullable=True,
        comment="HTTP method (GET, POST, PUT, DELETE)"
    )

    request_path = Column(
        String(1000),
        nullable=True,
        comment="Request path/endpoint"
    )

    request_params = Column(
        JSON,
        nullable=True,
        comment="Request parameters (sanitized, no sensitive data)"
    )

    response_status = Column(
        Integer,
        nullable=True,
        comment="HTTP response status code"
    )

    # ========================================================================
    # Performance Metrics
    # ========================================================================
    duration_ms = Column(
        Integer,
        nullable=True,
        comment="Duration of the action in milliseconds"
    )

    # ========================================================================
    # Security & Compliance
    # ========================================================================
    severity = Column(
        String(20),
        nullable=False,
        default="info",
        index=True,
        comment="Severity: critical, high, medium, low, info"
    )

    requires_attention = Column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Whether this log entry requires human attention (1=yes, 0=no)"
    )

    compliance_relevant = Column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Whether this is relevant for compliance reporting (1=yes, 0=no)"
    )

    # ========================================================================
    # Retention
    # ========================================================================
    retention_period_days = Column(
        Integer,
        nullable=False,
        default=2555,  # 7 years for compliance
        comment="How long to retain this log entry (days)"
    )

    # ========================================================================
    # Table Constraints
    # ========================================================================
    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_audit_timestamp_action", "timestamp", "action"),
        Index("ix_audit_actor_timestamp", "actor_id", "timestamp"),
        Index("ix_audit_resource_timestamp", "resource_type", "resource_id", "timestamp"),
        Index("ix_audit_action_success", "action", "success"),
        Index("ix_audit_severity_timestamp", "severity", "timestamp"),
        Index("ix_audit_request_id", "request_id"),

        # Partitioning hint (for future optimization)
        # Can be partitioned by timestamp for better performance
        {"comment": "Immutable audit trail for all system actions"}
    )

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"<AuditLog(id={self.id}, action={self.action}, "
            f"actor={self.actor_id}, resource={self.resource_type}:{self.resource_id})>"
        )

    @property
    def is_failure(self) -> bool:
        """Check if action failed"""
        return self.success == 0

    @property
    def is_critical(self) -> bool:
        """Check if entry is critical severity"""
        return self.severity == "critical"

    @property
    def age_hours(self) -> float:
        """Calculate age of log entry in hours"""
        if self.timestamp:
            return (datetime.utcnow() - self.timestamp).total_seconds() / 3600
        return 0.0

    @property
    def should_be_reviewed(self) -> bool:
        """Check if entry requires human review"""
        return bool(self.requires_attention) or self.is_failure

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @classmethod
    def log_action(
        cls,
        action: AuditAction,
        actor_id: str,
        resource_type: AuditResourceType,
        resource_id: str,
        description: str,
        actor_type: str = "system",
        success: bool = True,
        **kwargs
    ) -> "AuditLog":
        """
        Helper method to create an audit log entry.

        Args:
            action: The action being logged
            actor_id: ID of the entity performing the action
            resource_type: Type of resource being affected
            resource_id: ID of the resource
            description: Human-readable description
            actor_type: Type of actor (default: system)
            success: Whether action was successful
            **kwargs: Additional fields (details, metadata, etc.)

        Returns:
            AuditLog: Created audit log instance
        """
        return cls(
            action=action,
            timestamp=datetime.utcnow(),
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            success=1 if success else 0,
            **kwargs
        )
