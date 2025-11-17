"""
VulnZero - Asset Model
Stores infrastructure assets (servers, containers, cloud resources)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON, Enum,
    Index, CheckConstraint, Boolean
)
from sqlalchemy.orm import relationship
import enum

from shared.models.base import Base


class AssetType(str, enum.Enum):
    """Asset type enumeration"""
    SERVER = "server"
    CONTAINER = "container"
    CLOUD = "cloud"
    NETWORK_DEVICE = "network_device"
    DATABASE = "database"
    APPLICATION = "application"
    OTHER = "other"


class AssetStatus(str, enum.Enum):
    """Asset status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Asset(Base):
    """
    Asset Model - Stores infrastructure components.

    This table represents all infrastructure assets that can have vulnerabilities,
    including servers, containers, cloud resources, and network devices.
    """

    __tablename__ = "assets"

    # ========================================================================
    # Basic Information
    # ========================================================================
    asset_id = Column(
        String(200),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique asset identifier (UUID, hostname, or custom ID)"
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable asset name"
    )

    type = Column(
        Enum(AssetType),
        nullable=False,
        index=True,
        comment="Asset type: server, container, cloud, etc."
    )

    status = Column(
        Enum(AssetStatus),
        nullable=False,
        default=AssetStatus.ACTIVE,
        index=True,
        comment="Asset status: active, inactive, maintenance, decommissioned"
    )

    description = Column(
        Text,
        nullable=True,
        comment="Asset description or notes"
    )

    # ========================================================================
    # Network Information
    # ========================================================================
    hostname = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Hostname or FQDN"
    )

    ip_address = Column(
        String(45),  # IPv6 can be up to 45 chars
        nullable=True,
        index=True,
        comment="Primary IP address (IPv4 or IPv6)"
    )

    mac_address = Column(
        String(17),
        nullable=True,
        comment="MAC address"
    )

    # ========================================================================
    # Operating System Information
    # ========================================================================
    os_type = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Operating system type (linux, windows, macos, etc.)"
    )

    os_name = Column(
        String(100),
        nullable=True,
        comment="Operating system name (Ubuntu, RHEL, Windows Server, etc.)"
    )

    os_version = Column(
        String(100),
        nullable=True,
        comment="Operating system version (22.04, 9.1, etc.)"
    )

    kernel_version = Column(
        String(100),
        nullable=True,
        comment="Kernel version"
    )

    architecture = Column(
        String(50),
        nullable=True,
        comment="System architecture (x86_64, arm64, etc.)"
    )

    # ========================================================================
    # Cloud/Container Information
    # ========================================================================
    cloud_provider = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Cloud provider (AWS, Azure, GCP, etc.)"
    )

    cloud_region = Column(
        String(50),
        nullable=True,
        comment="Cloud region"
    )

    cloud_instance_id = Column(
        String(200),
        nullable=True,
        comment="Cloud instance identifier"
    )

    container_image = Column(
        String(500),
        nullable=True,
        comment="Container image name and tag"
    )

    container_id = Column(
        String(100),
        nullable=True,
        comment="Container ID"
    )

    # ========================================================================
    # Location & Organization
    # ========================================================================
    location = Column(
        String(200),
        nullable=True,
        comment="Physical or logical location"
    )

    environment = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Environment: production, staging, development, testing"
    )

    business_unit = Column(
        String(200),
        nullable=True,
        comment="Business unit or department"
    )

    owner = Column(
        String(200),
        nullable=True,
        comment="Asset owner or responsible team"
    )

    cost_center = Column(
        String(100),
        nullable=True,
        comment="Cost center for billing"
    )

    # ========================================================================
    # Criticality & Risk
    # ========================================================================
    criticality = Column(
        Integer,
        nullable=False,
        default=5,
        comment="Business criticality (1=low, 10=critical)"
    )

    is_public_facing = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether asset is accessible from internet"
    )

    compliance_required = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether asset requires compliance (SOC2, HIPAA, etc.)"
    )

    # ========================================================================
    # Scanning Information
    # ========================================================================
    last_scanned = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Last vulnerability scan timestamp"
    )

    scan_frequency = Column(
        Integer,
        nullable=False,
        default=6,
        comment="Scan frequency in hours"
    )

    vulnerability_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of active vulnerabilities"
    )

    critical_vuln_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of critical vulnerabilities"
    )

    high_vuln_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of high severity vulnerabilities"
    )

    # ========================================================================
    # Connectivity & Access
    # ========================================================================
    ssh_port = Column(
        Integer,
        nullable=True,
        comment="SSH port number (default: 22)"
    )

    ssh_user = Column(
        String(100),
        nullable=True,
        comment="SSH username for remote access"
    )

    ansible_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether Ansible can manage this asset"
    )

    # ========================================================================
    # Metadata
    # ========================================================================
    tags = Column(
        JSON,
        nullable=True,
        comment="Custom tags for organization (key-value pairs)"
    )

    asset_metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata (flexible schema)"
    )

    installed_packages = Column(
        JSON,
        nullable=True,
        comment="List of installed software packages"
    )

    running_services = Column(
        JSON,
        nullable=True,
        comment="List of running services"
    )

    notes = Column(
        Text,
        nullable=True,
        comment="Additional notes"
    )

    # ========================================================================
    # Relationships
    # ========================================================================
    # One asset can have multiple deployments
    deployments = relationship("Deployment", back_populates="asset", cascade="all, delete-orphan")

    # ========================================================================
    # Table Constraints
    # ========================================================================
    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_asset_type_status", "type", "status"),
        Index("ix_asset_env_criticality", "environment", "criticality"),
        Index("ix_asset_os_type_version", "os_type", "os_version"),
        Index("ix_asset_public_facing_env", "is_public_facing", "environment"),

        # Check constraints
        CheckConstraint("criticality >= 1 AND criticality <= 10", name="check_asset_criticality_range"),
        CheckConstraint("scan_frequency > 0", name="check_scan_frequency_positive"),
        CheckConstraint("vulnerability_count >= 0", name="check_vuln_count_non_negative"),

        {"comment": "Stores infrastructure assets (servers, containers, cloud resources)"}
    )

    def __repr__(self) -> str:
        """String representation"""
        return f"<Asset(id={self.id}, asset_id={self.asset_id}, name={self.name}, type={self.type})>"

    @property
    def is_active(self) -> bool:
        """Check if asset is active"""
        return self.status == AssetStatus.ACTIVE

    @property
    def is_critical(self) -> bool:
        """Check if asset is business critical (criticality >= 8)"""
        return self.criticality >= 8

    @property
    def has_vulnerabilities(self) -> bool:
        """Check if asset has any vulnerabilities"""
        return self.vulnerability_count > 0

    @property
    def has_critical_vulnerabilities(self) -> bool:
        """Check if asset has critical vulnerabilities"""
        return self.critical_vuln_count > 0

    @property
    def scan_overdue(self) -> bool:
        """Check if asset scan is overdue"""
        if not self.last_scanned:
            return True
        hours_since_scan = (datetime.utcnow() - self.last_scanned).total_seconds() / 3600
        return hours_since_scan > self.scan_frequency

    @property
    def risk_score(self) -> float:
        """
        Calculate asset risk score based on multiple factors.
        Higher score = higher risk
        """
        score = 0.0

        # Factor 1: Criticality (0-50 points)
        score += (self.criticality / 10) * 50

        # Factor 2: Vulnerability count (0-30 points)
        vuln_score = min(self.vulnerability_count * 2, 30)
        score += vuln_score

        # Factor 3: Public facing (0-20 points)
        if self.is_public_facing:
            score += 20

        # Factor 4: Critical vulnerabilities (bonus)
        if self.critical_vuln_count > 0:
            score += self.critical_vuln_count * 5

        return min(score, 100)  # Cap at 100
