"""
Test data factories

Provides factory classes for generating test data
"""

from datetime import datetime
from typing import Optional, List

from shared.models.models import (
    Vulnerability,
    Patch,
    Deployment,
    Asset,
    VulnerabilitySeverity,
    PatchStatus,
    DeploymentStatus,
)


class VulnerabilityFactory:
    """Factory for creating test vulnerabilities"""

    @staticmethod
    def create(
        cve_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        severity: VulnerabilitySeverity = VulnerabilitySeverity.MEDIUM,
        cvss_score: float = 5.0,
        affected_systems: Optional[List[str]] = None,
        **kwargs
    ) -> Vulnerability:
        """Create a test vulnerability"""
        import random

        if cve_id is None:
            cve_id = f"CVE-2024-{random.randint(1000, 9999)}"

        if title is None:
            title = f"Test Vulnerability {cve_id}"

        if description is None:
            description = f"Test description for {cve_id}"

        if affected_systems is None:
            affected_systems = ["Ubuntu 22.04", "Ubuntu 20.04"]

        return Vulnerability(
            cve_id=cve_id,
            title=title,
            description=description,
            severity=severity,
            cvss_score=cvss_score,
            affected_systems=affected_systems,
            source="test",
            remediation="Apply security update",
            published_date=datetime.utcnow(),
            **kwargs
        )

    @staticmethod
    def create_batch(count: int = 10) -> List[Vulnerability]:
        """Create multiple test vulnerabilities"""
        return [VulnerabilityFactory.create() for _ in range(count)]


class PatchFactory:
    """Factory for creating test patches"""

    @staticmethod
    def create(
        vulnerability_id: int,
        patch_script: Optional[str] = None,
        rollback_script: Optional[str] = None,
        validation_script: Optional[str] = None,
        status: PatchStatus = PatchStatus.PENDING,
        confidence_score: Optional[float] = None,
        **kwargs
    ) -> Patch:
        """Create a test patch"""
        if patch_script is None:
            patch_script = "#!/bin/bash\napt-get update && apt-get install -y security-patch"

        if rollback_script is None:
            rollback_script = "#!/bin/bash\napt-get remove -y security-patch"

        if validation_script is None:
            validation_script = "#!/bin/bash\ntest -f /usr/bin/security-patch"

        if confidence_score is None:
            confidence_score = 0.85

        return Patch(
            vulnerability_id=vulnerability_id,
            patch_script=patch_script,
            rollback_script=rollback_script,
            validation_script=validation_script,
            status=status,
            confidence_score=confidence_score,
            **kwargs
        )

    @staticmethod
    def create_tested(vulnerability_id: int) -> Patch:
        """Create a tested patch with test results"""
        patch = PatchFactory.create(vulnerability_id, status=PatchStatus.APPROVED)
        patch.test_results = {
            "smoke_tests": {"passed": 5, "failed": 0},
            "security_tests": {"passed": 3, "failed": 0},
            "performance_tests": {"passed": 2, "failed": 0},
        }
        return patch


class DeploymentFactory:
    """Factory for creating test deployments"""

    @staticmethod
    def create(
        patch_id: int,
        status: DeploymentStatus = DeploymentStatus.PENDING,
        strategy: str = "rolling",
        results: Optional[dict] = None,
        **kwargs
    ) -> Deployment:
        """Create a test deployment"""
        if results is None:
            results = {}

        return Deployment(
            patch_id=patch_id,
            status=status,
            strategy=strategy,
            results=results,
            **kwargs
        )

    @staticmethod
    def create_in_progress(patch_id: int, asset_ids: List[int]) -> Deployment:
        """Create an in-progress deployment"""
        return DeploymentFactory.create(
            patch_id=patch_id,
            status=DeploymentStatus.IN_PROGRESS,
            results={
                "total_assets": len(asset_ids),
                "successful": 0,
                "failed": 0,
                "assets": [{"id": aid, "status": "pending"} for aid in asset_ids],
            },
            started_at=datetime.utcnow(),
        )

    @staticmethod
    def create_completed(patch_id: int, asset_ids: List[int]) -> Deployment:
        """Create a completed deployment"""
        return DeploymentFactory.create(
            patch_id=patch_id,
            status=DeploymentStatus.COMPLETED,
            results={
                "total_assets": len(asset_ids),
                "successful": len(asset_ids),
                "failed": 0,
                "assets": [{"id": aid, "status": "success"} for aid in asset_ids],
            },
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )


class AssetFactory:
    """Factory for creating test assets"""

    @staticmethod
    def create(
        name: Optional[str] = None,
        ip_address: Optional[str] = None,
        hostname: Optional[str] = None,
        os_version: str = "Ubuntu 22.04",
        status: str = "active",
        **kwargs
    ) -> Asset:
        """Create a test asset"""
        import random

        if name is None:
            name = f"server-{random.randint(1, 999)}"

        if ip_address is None:
            ip_address = f"192.168.1.{random.randint(10, 250)}"

        if hostname is None:
            hostname = f"{name}.example.com"

        return Asset(
            name=name,
            ip_address=ip_address,
            hostname=hostname,
            os_version=os_version,
            status=status,
            **kwargs
        )

    @staticmethod
    def create_batch(count: int = 10) -> List[Asset]:
        """Create multiple test assets"""
        return [AssetFactory.create() for _ in range(count)]

    @staticmethod
    def create_cluster(name: str, count: int = 5) -> List[Asset]:
        """Create a cluster of related assets"""
        return [
            AssetFactory.create(
                name=f"{name}-{i}",
                ip_address=f"192.168.1.{100+i}",
                hostname=f"{name}-{i}.example.com",
            )
            for i in range(count)
        ]


# Helper function to create complete test scenarios
def create_complete_scenario(db_session):
    """
    Create a complete test scenario with vulnerability, patch, and assets
    """
    vulnerability = VulnerabilityFactory.create(severity=VulnerabilitySeverity.HIGH)
    db_session.add(vulnerability)

    assets = AssetFactory.create_batch(5)
    for asset in assets:
        db_session.add(asset)

    # Need to commit to get IDs
    db_session.commit()

    patch = PatchFactory.create_tested(vulnerability.id)
    db_session.add(patch)
    db_session.commit()

    deployment = DeploymentFactory.create_in_progress(
        patch.id,
        [asset.id for asset in assets]
    )
    db_session.add(deployment)
    db_session.commit()

    return {
        "vulnerability": vulnerability,
        "patch": patch,
        "assets": assets,
        "deployment": deployment,
    }
