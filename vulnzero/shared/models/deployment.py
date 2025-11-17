"""Deployment database model."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class DeploymentStatus(str, Enum):
    """Deployment status enum."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class DeploymentStrategy(str, Enum):
    """Deployment strategy enum."""

    IMMEDIATE = "immediate"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"


class Deployment(Base, TimestampMixin):
    """Deployment database model."""

    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    deployment_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    # Foreign keys
    patch_id: Mapped[int] = mapped_column(
        ForeignKey("patches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Deployment details
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DeploymentStatus.PENDING, index=True
    )
    strategy: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DeploymentStrategy.IMMEDIATE
    )
    deployment_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ansible"
    )  # ansible, terraform, ssh, etc.

    # Execution details
    started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Execution logs
    execution_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Exit codes and results
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rollback information
    rollback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rollback_performed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    rollback_successful: Mapped[Optional[bool]] = mapped_column(nullable=True)

    # Monitoring and validation
    pre_deployment_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    post_deployment_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    anomalies_detected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Approval
    initiated_by: Mapped[str] = mapped_column(String(200), nullable=False, default="system")
    manual_approval_required: Mapped[bool] = mapped_column(default=False)

    # Relationships
    patch: Mapped["Patch"] = relationship("Patch", back_populates="deployments")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="deployments")

    def __repr__(self) -> str:
        return f"<Deployment(deployment_id='{self.deployment_id}', status='{self.status}')>"
