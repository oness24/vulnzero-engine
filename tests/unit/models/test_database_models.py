"""
Unit Tests for Database Models

Tests SQLAlchemy models, relationships, and constraints.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from shared.models import (
    Vulnerability, Asset, Patch, Deployment,
    VulnerabilityStatus, AssetType, AssetStatus,
    PatchType, PatchStatus, DeploymentStatus
)


class TestVulnerabilityModel:
    """Test Vulnerability model"""

    def test_create_vulnerability(self, test_db):
        """Test creating a vulnerability"""
        vuln = Vulnerability(
            cve_id="CVE-2024-99999",
            title="Test Vuln",
            description="Test description",
            severity="high",
            cvss_score=8.5,
            status=VulnerabilityStatus.NEW,
            affected_package="test-pkg",
            scanner_source="test"
        )

        test_db.add(vuln)
        test_db.commit()
        test_db.refresh(vuln)

        assert vuln.id is not None
        assert vuln.cve_id == "CVE-2024-99999"
        assert vuln.created_at is not None

    def test_vulnerability_unique_cve_id(self, test_db):
        """Test CVE ID uniqueness constraint"""
        vuln1 = Vulnerability(
            cve_id="CVE-2024-UNIQUE",
            title="Test 1",
            severity="high",
            cvss_score=7.0,
            scanner_source="test"
        )
        test_db.add(vuln1)
        test_db.commit()

        # Try to create duplicate
        vuln2 = Vulnerability(
            cve_id="CVE-2024-UNIQUE",  # Duplicate
            title="Test 2",
            severity="medium",
            cvss_score=5.0,
            scanner_source="test"
        )
        test_db.add(vuln2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_vulnerability_status_enum(self, test_db):
        """Test vulnerability status enum"""
        vuln = Vulnerability(
            cve_id="CVE-2024-STATUS",
            title="Test",
            severity="high",
            cvss_score=7.0,
            status=VulnerabilityStatus.NEW,
            scanner_source="test"
        )
        test_db.add(vuln)
        test_db.commit()

        assert vuln.status == VulnerabilityStatus.NEW

        # Update status
        vuln.status = VulnerabilityStatus.PATCHED
        test_db.commit()

        assert vuln.status == VulnerabilityStatus.PATCHED


class TestAssetModel:
    """Test Asset model"""

    def test_create_asset(self, test_db):
        """Test creating an asset"""
        asset = Asset(
            hostname="test-host",
            ip_address="10.0.0.1",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE,
            os_type="Ubuntu",
            os_version="22.04"
        )

        test_db.add(asset)
        test_db.commit()
        test_db.refresh(asset)

        assert asset.id is not None
        assert asset.hostname == "test-host"
        assert asset.status == AssetStatus.ACTIVE

    def test_asset_unique_hostname(self, test_db):
        """Test hostname uniqueness constraint"""
        asset1 = Asset(
            hostname="unique-host",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE
        )
        test_db.add(asset1)
        test_db.commit()

        # Try to create duplicate
        asset2 = Asset(
            hostname="unique-host",  # Duplicate
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE
        )
        test_db.add(asset2)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_asset_metadata_json(self, test_db):
        """Test JSON metadata field"""
        metadata = {
            "environment": "production",
            "region": "us-east-1",
            "tags": ["web", "critical"]
        }

        asset = Asset(
            hostname="meta-host",
            type=AssetType.SERVER,
            status=AssetStatus.ACTIVE,
            asset_metadata=metadata
        )

        test_db.add(asset)
        test_db.commit()
        test_db.refresh(asset)

        assert asset.asset_metadata["environment"] == "production"
        assert "web" in asset.asset_metadata["tags"]


class TestPatchModel:
    """Test Patch model"""

    def test_create_patch(self, test_db, sample_vulnerability):
        """Test creating a patch"""
        patch = Patch(
            vulnerability_id=sample_vulnerability.id,
            title="Fix for test vuln",
            description="Test patch",
            patch_type=PatchType.SCRIPT_EXECUTION,
            patch_content="#!/bin/bash\necho 'patched'",
            status=PatchStatus.PENDING_APPROVAL,
            confidence_score=85.0,
            llm_provider="openai"
        )

        test_db.add(patch)
        test_db.commit()
        test_db.refresh(patch)

        assert patch.id is not None
        assert patch.vulnerability_id == sample_vulnerability.id
        assert patch.status == PatchStatus.PENDING_APPROVAL

    def test_patch_vulnerability_relationship(self, test_db, sample_vulnerability):
        """Test relationship between Patch and Vulnerability"""
        patch = Patch(
            vulnerability_id=sample_vulnerability.id,
            title="Test patch",
            patch_type=PatchType.SCRIPT_EXECUTION,
            patch_content="test",
            status=PatchStatus.PENDING_APPROVAL,
            confidence_score=80.0
        )

        test_db.add(patch)
        test_db.commit()
        test_db.refresh(patch)

        # Access relationship
        assert patch.vulnerability is not None
        assert patch.vulnerability.cve_id == sample_vulnerability.cve_id

    def test_patch_confidence_score_range(self, test_db, sample_vulnerability):
        """Test confidence score is within valid range"""
        patch = Patch(
            vulnerability_id=sample_vulnerability.id,
            title="Test",
            patch_type=PatchType.SCRIPT_EXECUTION,
            patch_content="test",
            confidence_score=95.5
        )

        test_db.add(patch)
        test_db.commit()

        assert 0 <= patch.confidence_score <= 100


class TestDeploymentModel:
    """Test Deployment model"""

    def test_create_deployment(self, test_db, sample_patch):
        """Test creating a deployment"""
        deployment = Deployment(
            patch_id=sample_patch.id,
            strategy="rolling",
            status=DeploymentStatus.PENDING,
            total_assets=5,
            successful_assets=0,
            failed_assets=0
        )

        test_db.add(deployment)
        test_db.commit()
        test_db.refresh(deployment)

        assert deployment.id is not None
        assert deployment.patch_id == sample_patch.id
        assert deployment.strategy == "rolling"

    def test_deployment_patch_relationship(self, test_db, sample_patch):
        """Test relationship between Deployment and Patch"""
        deployment = Deployment(
            patch_id=sample_patch.id,
            strategy="canary",
            status=DeploymentStatus.PENDING,
            total_assets=10
        )

        test_db.add(deployment)
        test_db.commit()
        test_db.refresh(deployment)

        # Access relationship
        assert deployment.patch is not None
        assert deployment.patch.title == sample_patch.title

    def test_deployment_status_transitions(self, test_db, sample_patch):
        """Test deployment status transitions"""
        deployment = Deployment(
            patch_id=sample_patch.id,
            strategy="all-at-once",
            status=DeploymentStatus.PENDING,
            total_assets=3
        )

        test_db.add(deployment)
        test_db.commit()

        # Transition to in_progress
        deployment.status = DeploymentStatus.IN_PROGRESS
        deployment.started_at = datetime.utcnow()
        test_db.commit()

        assert deployment.status == DeploymentStatus.IN_PROGRESS
        assert deployment.started_at is not None

        # Transition to completed
        deployment.status = DeploymentStatus.COMPLETED
        deployment.completed_at = datetime.utcnow()
        deployment.successful_assets = 3
        test_db.commit()

        assert deployment.status == DeploymentStatus.COMPLETED
        assert deployment.completed_at is not None


class TestModelRelationships:
    """Test relationships between models"""

    def test_cascade_delete_vulnerability_patches(self, test_db, sample_vulnerability):
        """Test cascading delete from vulnerability to patches"""
        # Create patches
        patch1 = Patch(
            vulnerability_id=sample_vulnerability.id,
            title="Patch 1",
            patch_type=PatchType.SCRIPT_EXECUTION,
            patch_content="test1",
            confidence_score=80.0
        )
        patch2 = Patch(
            vulnerability_id=sample_vulnerability.id,
            title="Patch 2",
            patch_type=PatchType.SCRIPT_EXECUTION,
            patch_content="test2",
            confidence_score=85.0
        )

        test_db.add_all([patch1, patch2])
        test_db.commit()

        # Get patch count
        patch_count = test_db.query(Patch).filter_by(
            vulnerability_id=sample_vulnerability.id
        ).count()
        assert patch_count == 2

        # Delete vulnerability
        test_db.delete(sample_vulnerability)
        test_db.commit()

        # Check patches are deleted
        remaining_patches = test_db.query(Patch).filter_by(
            vulnerability_id=sample_vulnerability.id
        ).count()
        assert remaining_patches == 0

    def test_query_vulnerability_with_patches(self, test_db, sample_vulnerability):
        """Test querying vulnerability with related patches"""
        # Create patches
        for i in range(3):
            patch = Patch(
                vulnerability_id=sample_vulnerability.id,
                title=f"Patch {i}",
                patch_type=PatchType.SCRIPT_EXECUTION,
                patch_content=f"content {i}",
                confidence_score=80.0 + i
            )
            test_db.add(patch)
        test_db.commit()

        # Query with relationship
        vuln = test_db.query(Vulnerability).filter_by(
            id=sample_vulnerability.id
        ).first()

        # Check patches accessible through relationship
        assert len(vuln.patches) == 3
        assert all(p.vulnerability_id == vuln.id for p in vuln.patches)
