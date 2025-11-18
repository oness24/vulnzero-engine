"""
VulnZero - Deployment Model
Stores deployment history and tracking information
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, Enum,
    ForeignKey, Index, CheckConstraint, Boolean
)
from sqlalchemy.orm import relationship
import enum

from shared.models.base import Base


class DeploymentStatus(str, enum.Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PRE_CHECK_RUNNING = "pre_check_running"
    PRE_CHECK_PASSED = "pre_check_passed"
    PRE_CHECK_FAILED = "pre_check_failed"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class DeploymentStrategy(str, enum.Enum):
    """Deployment strategy enumeration"""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    ALL_AT_ONCE = "all_at_once"


class Deployment(Base):
    """
    Deployment Model - Stores deployment history and tracking.

    This table tracks all patch deployments to assets, including
    pre-deployment checks, execution logs, and rollback information.
    """

    __tablename__ = "deployments"

    # ========================================================================
    # Foreign Keys
    # ========================================================================
    patch_id = Column(
        Integer,
        ForeignKey("patches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the patch being deployed"
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the target asset"
    )

    # ========================================================================
    # Deployment Information
    # ========================================================================
    deployment_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique deployment identifier (UUID)"
    )

    status = Column(
        Enum(DeploymentStatus),
        nullable=False,
        default=DeploymentStatus.PENDING,
        index=True,
        comment="Current deployment status"
    )

    strategy = Column(
        Enum(DeploymentStrategy),
        nullable=False,
        default=DeploymentStrategy.ALL_AT_ONCE,
        comment="Deployment strategy used"
    )

    deployment_method = Column(
        String(100),
        nullable=False,
        comment="Deployment method: ansible, ssh, terraform, etc."
    )

    # ========================================================================
    # Timing Information
    # ========================================================================
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When deployment is scheduled to start"
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When deployment actually started"
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When deployment completed (success or failure)"
    )

    duration_seconds = Column(
        Float,
        nullable=True,
        comment="Total deployment duration in seconds"
    )

    # ========================================================================
    # Pre-Deployment Checks
    # ========================================================================
    pre_check_passed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether pre-deployment checks passed"
    )

    pre_check_results = Column(
        JSON,
        nullable=True,
        comment="Detailed results of pre-deployment checks"
    )

    pre_check_errors = Column(
        JSON,
        nullable=True,
        comment="Pre-check errors, if any"
    )

    # ========================================================================
    # Execution Information
    # ========================================================================
    execution_logs = Column(
        Text,
        nullable=True,
        comment="Deployment execution logs (stdout/stderr)"
    )

    exit_code = Column(
        Integer,
        nullable=True,
        comment="Exit code from deployment script"
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if deployment failed"
    )

    # ========================================================================
    # Post-Deployment Validation
    # ========================================================================
    post_validation_passed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether post-deployment validation passed"
    )

    post_validation_results = Column(
        JSON,
        nullable=True,
        comment="Results of post-deployment health checks"
    )

    # ========================================================================
    # Metrics & Monitoring
    # ========================================================================
    baseline_metrics = Column(
        JSON,
        nullable=True,
        comment="Baseline metrics collected before deployment"
    )

    post_deployment_metrics = Column(
        JSON,
        nullable=True,
        comment="Metrics collected after deployment"
    )

    anomalies_detected = Column(
        JSON,
        nullable=True,
        comment="List of anomalies detected during monitoring"
    )

    monitoring_duration_seconds = Column(
        Integer,
        nullable=False,
        default=900,  # 15 minutes
        comment="How long to monitor after deployment (seconds)"
    )

    # ========================================================================
    # Rollback Information
    # ========================================================================
    rollback_needed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether rollback was needed"
    )

    rollback_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for rollback"
    )

    rollback_triggered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When rollback was triggered"
    )

    rollback_completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When rollback completed"
    )

    rollback_logs = Column(
        Text,
        nullable=True,
        comment="Rollback execution logs"
    )

    rollback_success = Column(
        Boolean,
        nullable=True,
        comment="Whether rollback was successful"
    )

    # ========================================================================
    # Canary Deployment Information
    # ========================================================================
    canary_percentage = Column(
        Integer,
        nullable=True,
        comment="Percentage for canary deployment (10%, 50%, 100%)"
    )

    canary_phase = Column(
        Integer,
        nullable=True,
        comment="Current phase in canary deployment"
    )

    canary_wait_time = Column(
        Integer,
        nullable=True,
        comment="Wait time between canary phases (seconds)"
    )

    # ========================================================================
    # Approval & Execution
    # ========================================================================
    requires_approval = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether deployment requires manual approval"
    )

    approved_by = Column(
        String(200),
        nullable=True,
        comment="User who approved the deployment"
    )

    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When deployment was approved"
    )

    executed_by = Column(
        String(200),
        nullable=False,
        default="system",
        comment="Who/what executed the deployment (user or system)"
    )

    cancelled_by = Column(
        String(200),
        nullable=True,
        comment="User who cancelled the deployment"
    )

    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When deployment was cancelled"
    )

    cancellation_reason = Column(
        Text,
        nullable=True,
        comment="Reason for cancellation"
    )

    # ========================================================================
    # Backup Information
    # ========================================================================
    backup_created = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether backup was created before deployment"
    )

    backup_location = Column(
        String(500),
        nullable=True,
        comment="Location of backup (file path, S3 URL, etc.)"
    )

    backup_size_bytes = Column(
        Integer,
        nullable=True,
        comment="Size of backup in bytes"
    )

    # ========================================================================
    # Notifications
    # ========================================================================
    notifications_sent = Column(
        JSON,
        nullable=True,
        comment="List of notifications sent (Slack, email, etc.)"
    )

    # ========================================================================
    # Metadata
    # ========================================================================
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )

    parent_deployment_id = Column(
        Integer,
        ForeignKey("deployments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Reference to parent deployment (for retries)"
    )

    tags = Column(
        JSON,
        nullable=True,
        comment="Custom tags"
    )

    deployment_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata"
    )

    notes = Column(
        Text,
        nullable=True,
        comment="Deployment notes"
    )

    # ========================================================================
    # Relationships
    # ========================================================================
    patch = relationship("Patch", back_populates="deployments")
    asset = relationship("Asset", back_populates="deployments")

    # ========================================================================
    # Table Constraints
    # ========================================================================
    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_deployment_patch_status", "patch_id", "status"),
        Index("ix_deployment_asset_status", "asset_id", "status"),
        Index("ix_deployment_status_started", "status", "started_at"),
        Index("ix_deployment_strategy_status", "strategy", "status"),
        Index("ix_deployment_scheduled", "scheduled_at", "status"),

        # Check constraints
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        CheckConstraint("duration_seconds >= 0", name="check_duration_non_negative"),
        CheckConstraint(
            "canary_percentage IS NULL OR (canary_percentage >= 0 AND canary_percentage <= 100)",
            name="check_canary_percentage_range"
        ),

        {"comment": "Stores deployment history and tracking information"}
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<Deployment(id={self.id}, deployment_id={self.deployment_id}, status={self.status})>"

    @property
    def is_complete(self) -> bool:
        """Check if deployment is complete (success, failed, or rolled back)"""
        return self.status in [
            DeploymentStatus.SUCCESS,
            DeploymentStatus.FAILED,
            DeploymentStatus.ROLLED_BACK,
            DeploymentStatus.CANCELLED
        ]

    @property
    def is_successful(self) -> bool:
        """Check if deployment was successful"""
        return self.status == DeploymentStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if deployment failed"""
        return self.status == DeploymentStatus.FAILED

    @property
    def is_in_progress(self) -> bool:
        """Check if deployment is currently in progress"""
        return self.status in [
            DeploymentStatus.DEPLOYING,
            DeploymentStatus.PRE_CHECK_RUNNING,
            DeploymentStatus.ROLLING_BACK
        ]

    @property
    def needs_rollback(self) -> bool:
        """Check if deployment needs rollback"""
        return self.rollback_needed and self.status not in [
            DeploymentStatus.ROLLED_BACK,
            DeploymentStatus.ROLLING_BACK
        ]

    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes"""
        if self.duration_seconds:
            return self.duration_seconds / 60
        return 0.0

    def calculate_duration(self) -> None:
        """Calculate and set duration based on start and end times"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()
