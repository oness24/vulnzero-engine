"""
Event Definitions for VulnZero
===============================

Domain events for asynchronous communication between services.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    """Event types in the VulnZero system"""

    # Vulnerability events
    VULNERABILITY_DETECTED = "vulnerability.detected"
    VULNERABILITY_ANALYZED = "vulnerability.analyzed"
    VULNERABILITY_PRIORITIZED = "vulnerability.prioritized"
    VULNERABILITY_REMEDIATED = "vulnerability.remediated"
    VULNERABILITY_VERIFIED = "vulnerability.verified"

    # Patch events
    PATCH_GENERATED = "patch.generated"
    PATCH_TESTED = "patch.tested"
    PATCH_APPROVED = "patch.approved"
    PATCH_REJECTED = "patch.rejected"
    PATCH_DEPLOYED = "patch.deployed"

    # Deployment events
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_SUCCEEDED = "deployment.succeeded"
    DEPLOYMENT_FAILED = "deployment.failed"
    DEPLOYMENT_ROLLED_BACK = "deployment.rolled_back"

    # Asset events
    ASSET_DISCOVERED = "asset.discovered"
    ASSET_UPDATED = "asset.updated"
    ASSET_DECOMMISSIONED = "asset.decommissioned"
    ASSET_SCANNED = "asset.scanned"

    # Scan events
    SCAN_STARTED = "scan.started"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"


class Event(BaseModel):
    """
    Base event class for all domain events.

    Attributes:
        event_id: Unique identifier for this event
        event_type: Type of event (from EventType enum)
        timestamp: When the event occurred
        source_service: Service that published the event
        data: Event-specific data payload
        correlation_id: Optional ID to correlate related events
        metadata: Additional metadata
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_service: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class VulnerabilityEvent(Event):
    """
    Event for vulnerability lifecycle changes.

    Data fields:
        vulnerability_id: ID of the vulnerability
        cve_id: CVE identifier
        severity: Severity level (critical, high, medium, low)
        asset_id: Affected asset
        status: Current status
        priority_score: Calculated priority score
    """

    event_type: EventType = Field(
        ...,
        description="Must be a vulnerability-related event type"
    )

    @property
    def vulnerability_id(self) -> int:
        return self.data["vulnerability_id"]

    @property
    def cve_id(self) -> Optional[str]:
        return self.data.get("cve_id")

    @property
    def severity(self) -> str:
        return self.data["severity"]


class PatchEvent(Event):
    """
    Event for patch lifecycle changes.

    Data fields:
        patch_id: ID of the patch
        vulnerability_id: Related vulnerability
        patch_type: Type of patch (code, config, version_upgrade)
        status: Current status
        confidence_score: Confidence in patch quality
        test_status: Testing status
    """

    event_type: EventType = Field(
        ...,
        description="Must be a patch-related event type"
    )

    @property
    def patch_id(self) -> int:
        return self.data["patch_id"]

    @property
    def vulnerability_id(self) -> int:
        return self.data["vulnerability_id"]

    @property
    def patch_type(self) -> str:
        return self.data["patch_type"]


class DeploymentEvent(Event):
    """
    Event for deployment lifecycle changes.

    Data fields:
        deployment_id: ID of the deployment
        patch_id: Related patch
        asset_id: Target asset
        status: Current status
        deployment_method: How it was deployed
        error: Error message if failed
    """

    event_type: EventType = Field(
        ...,
        description="Must be a deployment-related event type"
    )

    @property
    def deployment_id(self) -> int:
        return self.data["deployment_id"]

    @property
    def patch_id(self) -> int:
        return self.data["patch_id"]

    @property
    def asset_id(self) -> int:
        return self.data["asset_id"]


class AssetEvent(Event):
    """
    Event for asset lifecycle changes.

    Data fields:
        asset_id: ID of the asset
        asset_type: Type of asset
        hostname: Asset hostname
        environment: Deployment environment
        is_public_facing: Whether asset is public
    """

    event_type: EventType = Field(
        ...,
        description="Must be an asset-related event type"
    )

    @property
    def asset_id(self) -> int:
        return self.data["asset_id"]

    @property
    def asset_type(self) -> str:
        return self.data["asset_type"]


class ScanEvent(Event):
    """
    Event for vulnerability scan lifecycle.

    Data fields:
        scan_id: ID of the scan
        asset_id: Scanned asset
        scanner_source: Scanner that performed scan
        vulnerabilities_found: Number of vulnerabilities found
        scan_duration: How long the scan took
    """

    event_type: EventType = Field(
        ...,
        description="Must be a scan-related event type"
    )

    @property
    def scan_id(self) -> str:
        return self.data["scan_id"]

    @property
    def asset_id(self) -> int:
        return self.data["asset_id"]


# Event factory functions for common scenarios
def create_vulnerability_detected_event(
    vulnerability_id: int,
    cve_id: Optional[str],
    severity: str,
    asset_id: int,
    source_service: str = "scanner-service",
    correlation_id: Optional[str] = None,
) -> VulnerabilityEvent:
    """Create a vulnerability detected event"""
    return VulnerabilityEvent(
        event_type=EventType.VULNERABILITY_DETECTED,
        source_service=source_service,
        correlation_id=correlation_id,
        data={
            "vulnerability_id": vulnerability_id,
            "cve_id": cve_id,
            "severity": severity,
            "asset_id": asset_id,
        },
    )


def create_patch_generated_event(
    patch_id: int,
    vulnerability_id: int,
    patch_type: str,
    confidence_score: float,
    source_service: str = "patch-engine",
    correlation_id: Optional[str] = None,
) -> PatchEvent:
    """Create a patch generated event"""
    return PatchEvent(
        event_type=EventType.PATCH_GENERATED,
        source_service=source_service,
        correlation_id=correlation_id,
        data={
            "patch_id": patch_id,
            "vulnerability_id": vulnerability_id,
            "patch_type": patch_type,
            "confidence_score": confidence_score,
        },
    )


def create_deployment_succeeded_event(
    deployment_id: int,
    patch_id: int,
    asset_id: int,
    deployment_method: str,
    source_service: str = "deployment-service",
    correlation_id: Optional[str] = None,
) -> DeploymentEvent:
    """Create a deployment succeeded event"""
    return DeploymentEvent(
        event_type=EventType.DEPLOYMENT_SUCCEEDED,
        source_service=source_service,
        correlation_id=correlation_id,
        data={
            "deployment_id": deployment_id,
            "patch_id": patch_id,
            "asset_id": asset_id,
            "deployment_method": deployment_method,
        },
    )
