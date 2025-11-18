"""
VulnZero - Database Models
SQLAlchemy ORM models for all database tables
"""

from shared.models.base import Base
from shared.models.vulnerability import Vulnerability, VulnerabilityStatus
from shared.models.asset import Asset, AssetType, AssetStatus
from shared.models.patch import Patch, PatchType, PatchStatus
from shared.models.deployment import Deployment, DeploymentStatus, DeploymentStrategy
from shared.models.audit_log import AuditLog, AuditAction, AuditResourceType
from shared.models.remediation_job import RemediationJob, JobType, JobStatus

__all__ = [
    # Database
    "Base",
    # Models
    "Vulnerability",
    "Asset",
    "Patch",
    "Deployment",
    "AuditLog",
    "RemediationJob",
    # Enums - Vulnerability
    "VulnerabilityStatus",
    # Enums - Asset
    "AssetType",
    "AssetStatus",
    # Enums - Patch
    "PatchType",
    "PatchStatus",
    # Enums - Deployment
    "DeploymentStatus",
    "DeploymentStrategy",
    # Enums - Audit
    "AuditAction",
    "AuditResourceType",
    # Enums - Remediation Job
    "JobType",
    "JobStatus",
]
