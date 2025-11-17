"""
VulnZero - Remediation Job Model
Tracks async remediation jobs (Celery tasks)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, Enum,
    Index, CheckConstraint, Boolean
)
import enum

from shared.models.base import Base


class JobType(str, enum.Enum):
    """Job type enumeration"""
    VULNERABILITY_SCAN = "vulnerability_scan"
    VULNERABILITY_ENRICHMENT = "vulnerability_enrichment"
    PRIORITY_CALCULATION = "priority_calculation"
    PATCH_GENERATION = "patch_generation"
    PATCH_VALIDATION = "patch_validation"
    DIGITAL_TWIN_TEST = "digital_twin_test"
    DEPLOYMENT = "deployment"
    POST_DEPLOYMENT_MONITORING = "post_deployment_monitoring"
    ROLLBACK = "rollback"
    ASSET_DISCOVERY = "asset_discovery"
    REPORT_GENERATION = "report_generation"
    DATA_CLEANUP = "data_cleanup"
    ML_MODEL_TRAINING = "ml_model_training"


class JobStatus(str, enum.Enum):
    """Job status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class JobPriority(str, enum.Enum):
    """Job priority levels"""
    CRITICAL = "critical"  # Priority 0 - Execute immediately
    HIGH = "high"          # Priority 1
    NORMAL = "normal"      # Priority 5
    LOW = "low"            # Priority 9


class RemediationJob(Base):
    """
    Remediation Job Model - Tracks async background jobs.

    This table tracks all async remediation jobs processed by Celery workers,
    providing visibility into job status, progress, and results.
    """

    __tablename__ = "remediation_jobs"

    # ========================================================================
    # Job Identification
    # ========================================================================
    job_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique job identifier (Celery task ID)"
    )

    job_type = Column(
        Enum(JobType),
        nullable=False,
        index=True,
        comment="Type of remediation job"
    )

    job_name = Column(
        String(200),
        nullable=False,
        comment="Human-readable job name"
    )

    # ========================================================================
    # Status & Timing
    # ========================================================================
    status = Column(
        Enum(JobStatus),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
        comment="Current job status"
    )

    priority = Column(
        Enum(JobPriority),
        nullable=False,
        default=JobPriority.NORMAL,
        index=True,
        comment="Job priority level"
    )

    priority_score = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Numeric priority (0=highest, 9=lowest)"
    )

    created_at_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When job was created"
    )

    queued_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When job was added to queue"
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When job execution started"
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When job completed (success or failure)"
    )

    duration_seconds = Column(
        Float,
        nullable=True,
        comment="Total execution duration in seconds"
    )

    timeout_seconds = Column(
        Integer,
        nullable=False,
        default=3600,
        comment="Maximum execution time allowed (seconds)"
    )

    # ========================================================================
    # Progress Tracking
    # ========================================================================
    progress_percent = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Job progress percentage (0-100)"
    )

    progress_message = Column(
        String(500),
        nullable=True,
        comment="Current progress message"
    )

    steps_total = Column(
        Integer,
        nullable=True,
        comment="Total number of steps in job"
    )

    steps_completed = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of steps completed"
    )

    # ========================================================================
    # Worker Information
    # ========================================================================
    worker_id = Column(
        String(200),
        nullable=True,
        index=True,
        comment="ID of the Celery worker processing the job"
    )

    worker_hostname = Column(
        String(200),
        nullable=True,
        comment="Hostname of the worker machine"
    )

    queue_name = Column(
        String(100),
        nullable=False,
        default="default",
        index=True,
        comment="Celery queue name"
    )

    # ========================================================================
    # Input & Output
    # ========================================================================
    input_params = Column(
        JSON,
        nullable=True,
        comment="Input parameters for the job"
    )

    result = Column(
        JSON,
        nullable=True,
        comment="Job result data (on success)"
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error message (on failure)"
    )

    error_traceback = Column(
        Text,
        nullable=True,
        comment="Full error traceback (on failure)"
    )

    # ========================================================================
    # Retry Logic
    # ========================================================================
    retry_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of retry attempts"
    )

    max_retries = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum number of retries allowed"
    )

    retry_delay_seconds = Column(
        Integer,
        nullable=False,
        default=60,
        comment="Delay between retries (seconds)"
    )

    last_retry_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When last retry was attempted"
    )

    # ========================================================================
    # Dependencies
    # ========================================================================
    parent_job_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Parent job ID (for job chains)"
    )

    depends_on = Column(
        JSON,
        nullable=True,
        comment="List of job IDs this job depends on"
    )

    # ========================================================================
    # Resource References
    # ========================================================================
    vulnerability_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Related vulnerability ID (if applicable)"
    )

    asset_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Related asset ID (if applicable)"
    )

    patch_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Related patch ID (if applicable)"
    )

    deployment_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="Related deployment ID (if applicable)"
    )

    # ========================================================================
    # Performance Metrics
    # ========================================================================
    cpu_time_seconds = Column(
        Float,
        nullable=True,
        comment="CPU time consumed (seconds)"
    )

    memory_peak_mb = Column(
        Integer,
        nullable=True,
        comment="Peak memory usage (MB)"
    )

    # ========================================================================
    # Scheduling
    # ========================================================================
    scheduled_for = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When job is scheduled to run (for delayed jobs)"
    )

    is_periodic = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a periodic/recurring job"
    )

    cron_expression = Column(
        String(100),
        nullable=True,
        comment="Cron expression for periodic jobs"
    )

    # ========================================================================
    # Metadata
    # ========================================================================
    tags = Column(
        JSON,
        nullable=True,
        comment="Custom tags for filtering/organization"
    )

    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata"
    )

    logs = Column(
        Text,
        nullable=True,
        comment="Job execution logs"
    )

    notes = Column(
        Text,
        nullable=True,
        comment="Additional notes"
    )

    # ========================================================================
    # Notifications
    # ========================================================================
    notify_on_completion = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Send notification when job completes"
    )

    notification_sent = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether notification was sent"
    )

    notification_channels = Column(
        JSON,
        nullable=True,
        comment="Channels to notify (slack, email, etc.)"
    )

    # ========================================================================
    # Table Constraints
    # ========================================================================
    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_job_status_priority", "status", "priority_score"),
        Index("ix_job_type_status", "job_type", "status"),
        Index("ix_job_created_status", "created_at_timestamp", "status"),
        Index("ix_job_worker_status", "worker_id", "status"),
        Index("ix_job_scheduled", "scheduled_for", "status"),
        Index("ix_job_queue_status", "queue_name", "status"),

        # Check constraints
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_progress_range"),
        CheckConstraint("priority_score >= 0 AND priority_score <= 9", name="check_priority_range"),
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint("steps_completed >= 0", name="check_steps_completed_non_negative"),

        {"comment": "Tracks async remediation jobs processed by Celery workers"}
    )

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"<RemediationJob(id={self.id}, job_id={self.job_id}, "
            f"type={self.job_type}, status={self.status})>"
        )

    @property
    def is_complete(self) -> bool:
        """Check if job is complete"""
        return self.status in [JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT]

    @property
    def is_successful(self) -> bool:
        """Check if job completed successfully"""
        return self.status == JobStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        """Check if job failed"""
        return self.status in [JobStatus.FAILED, JobStatus.TIMEOUT]

    @property
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status == JobStatus.RUNNING

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.is_failed and self.retry_count < self.max_retries

    @property
    def is_timed_out(self) -> bool:
        """Check if job timed out"""
        if self.started_at and not self.completed_at:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds()
            return elapsed > self.timeout_seconds
        return False

    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes"""
        if self.duration_seconds:
            return self.duration_seconds / 60
        return 0.0

    @property
    def age_hours(self) -> float:
        """Calculate age of job in hours"""
        if self.created_at:
            return (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return 0.0

    def calculate_duration(self) -> None:
        """Calculate and set duration based on start and end times"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()

    def update_progress(self, percent: int, message: Optional[str] = None) -> None:
        """
        Update job progress.

        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
        """
        self.progress_percent = max(0, min(100, percent))
        if message:
            self.progress_message = message
