"""Patch database model."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class PatchStatus(str, Enum):
    """Patch status enum."""

    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    TESTING = "testing"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class PatchType(str, Enum):
    """Patch type enum."""

    PACKAGE_UPDATE = "package_update"
    CONFIG_CHANGE = "config_change"
    SCRIPT_EXECUTION = "script_execution"
    WORKAROUND = "workaround"
    CUSTOM = "custom"


class Patch(Base, TimestampMixin):
    """Patch database model."""

    __tablename__ = "patches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patch_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    # Foreign keys
    vulnerability_id: Mapped[int] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Patch details
    patch_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PatchType.PACKAGE_UPDATE
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PatchStatus.GENERATED, index=True
    )

    # Patch content
    patch_content: Mapped[str] = mapped_column(Text, nullable=False)  # The actual script/config
    rollback_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI generation metadata
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "gpt-4"
    llm_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Validation and confidence
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    validation_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    syntax_check_passed: Mapped[bool] = mapped_column(default=False)
    security_check_passed: Mapped[bool] = mapped_column(default=False)

    # Testing results
    test_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    test_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    test_completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Approval workflow
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deployment tracking
    deployment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    deployed_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    vulnerability: Mapped["Vulnerability"] = relationship("Vulnerability", back_populates="patches")
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="patch", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patch(patch_id='{self.patch_id}', status='{self.status}', confidence={self.confidence_score})>"
