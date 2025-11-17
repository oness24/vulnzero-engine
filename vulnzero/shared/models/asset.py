"""Asset database model."""
from enum import Enum
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class AssetType(str, Enum):
    """Asset type enum."""

    SERVER = "server"
    CONTAINER = "container"
    CLOUD_INSTANCE = "cloud_instance"
    VIRTUAL_MACHINE = "virtual_machine"
    KUBERNETES_POD = "kubernetes_pod"


class AssetStatus(str, Enum):
    """Asset status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Asset(Base, TimestampMixin):
    """Asset database model representing infrastructure components."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Asset identification
    asset_id: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, index=True)

    # Asset type and details
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AssetType.SERVER
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=AssetStatus.ACTIVE, index=True
    )

    # Operating system
    os_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "ubuntu", "rhel"
    os_version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "22.04", "8.5"
    os_architecture: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "x86_64"

    # Package manager
    package_manager: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "apt", "yum", "dnf"

    # Criticality and classification
    criticality: Mapped[str] = mapped_column(
        String(20), nullable=False, default="medium"
    )  # low, medium, high, critical
    environment: Mapped[str] = mapped_column(
        String(50), nullable=False, default="production"
    )  # development, staging, production

    # Tags and metadata
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON object

    # Connectivity
    ssh_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22)
    ssh_user: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Cloud provider information (if applicable)
    cloud_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # aws, gcp, azure
    cloud_region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cloud_instance_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    vulnerabilities: Mapped[list["AssetVulnerability"]] = relationship(
        "AssetVulnerability", back_populates="asset", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["Deployment"]] = relationship(
        "Deployment", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(hostname='{self.hostname}', type='{self.asset_type}', status='{self.status}')>"


class AssetVulnerability(Base, TimestampMixin):
    """Association table between Assets and Vulnerabilities."""

    __tablename__ = "asset_vulnerabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    vulnerability_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Detection details
    detected_at: Mapped[str] = mapped_column(nullable=False)
    resolved_at: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="vulnerabilities")
    vulnerability: Mapped["Vulnerability"] = relationship(
        "Vulnerability", back_populates="affected_assets"
    )

    def __repr__(self) -> str:
        return f"<AssetVulnerability(asset_id={self.asset_id}, vulnerability_id={self.vulnerability_id})>"
