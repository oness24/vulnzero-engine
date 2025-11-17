"""Audit log database model."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditAction(str, Enum):
    """Audit action types."""

    # Vulnerability actions
    VULNERABILITY_DISCOVERED = "vulnerability_discovered"
    VULNERABILITY_UPDATED = "vulnerability_updated"
    VULNERABILITY_REMEDIATED = "vulnerability_remediated"

    # Patch actions
    PATCH_GENERATED = "patch_generated"
    PATCH_VALIDATED = "patch_validated"
    PATCH_APPROVED = "patch_approved"
    PATCH_REJECTED = "patch_rejected"

    # Deployment actions
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCESS = "deployment_success"
    DEPLOYMENT_FAILED = "deployment_failed"
    DEPLOYMENT_ROLLED_BACK = "deployment_rolled_back"

    # Asset actions
    ASSET_REGISTERED = "asset_registered"
    ASSET_UPDATED = "asset_updated"
    ASSET_DECOMMISSIONED = "asset_decommissioned"

    # System actions
    SCAN_INITIATED = "scan_initiated"
    SCAN_COMPLETED = "scan_completed"
    CONFIGURATION_CHANGED = "configuration_changed"

    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    MANUAL_OVERRIDE = "manual_override"


class AuditLog(Base):
    """Immutable audit log for all system actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Timestamp (immutable - no updated_at)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow, index=True)

    # Actor (who/what performed the action)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, system, service
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Details and context
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON with additional context

    # Result
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Compliance and security
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info"
    )  # critical, high, medium, low, info

    def __repr__(self) -> str:
        return f"<AuditLog(action='{self.action}', resource='{self.resource_type}:{self.resource_id}')>"
