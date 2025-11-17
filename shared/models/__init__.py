"""Database models for VulnZero"""

from shared.models.database import Base, get_db, init_db, drop_db, engine, AsyncSessionLocal
from shared.models.models import (
    Vulnerability,
    Asset,
    AssetVulnerability,
    Patch,
    Deployment,
    AuditLog,
    RemediationJob,
    VulnerabilityStatus,
    VulnerabilitySeverity,
    AssetType,
    TestStatus,
    DeploymentStatus,
    DeploymentMethod,
    JobStatus,
)

__all__ = [
    # Database
    "Base",
    "get_db",
    "init_db",
    "drop_db",
    "engine",
    "AsyncSessionLocal",
    # Models
    "Vulnerability",
    "Asset",
    "AssetVulnerability",
    "Patch",
    "Deployment",
    "AuditLog",
    "RemediationJob",
    # Enums
    "VulnerabilityStatus",
    "VulnerabilitySeverity",
    "AssetType",
    "TestStatus",
    "DeploymentStatus",
    "DeploymentMethod",
    "JobStatus",
]
