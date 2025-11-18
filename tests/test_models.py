"""
Tests for database models
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.models import (
    Vulnerability,
    Asset,
    Patch,
    Deployment,
    AssetVulnerability,
    AuditLog,
    RemediationJob,
    VulnerabilityStatus,
    VulnerabilitySeverity,
    AssetType,
    TestStatus,
    DeploymentStatus,
    JobStatus,
)


@pytest.mark.asyncio
async def test_create_vulnerability(db_session: AsyncSession):
    """Test creating a vulnerability"""
    vulnerability = Vulnerability(
        cve_id="CVE-2024-TEST",
        title="Test Vulnerability",
        description="A test vulnerability",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=7.5,
        priority_score=75.0,
    )

    db_session.add(vulnerability)
    await db_session.commit()
    await db_session.refresh(vulnerability)

    assert vulnerability.id is not None
    assert vulnerability.cve_id == "CVE-2024-TEST"
    assert vulnerability.status == VulnerabilityStatus.NEW
    assert vulnerability.created_at is not None


@pytest.mark.asyncio
async def test_vulnerability_uniqueness(db_session: AsyncSession):
    """Test that CVE IDs must be unique"""
    vuln1 = Vulnerability(
        cve_id="CVE-2024-UNIQUE",
        title="First",
        severity=VulnerabilitySeverity.HIGH,
    )
    db_session.add(vuln1)
    await db_session.commit()

    vuln2 = Vulnerability(
        cve_id="CVE-2024-UNIQUE",
        title="Second",
        severity=VulnerabilitySeverity.HIGH,
    )
    db_session.add(vuln2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_asset(db_session: AsyncSession):
    """Test creating an asset"""
    asset = Asset(
        asset_id="server-001",
        type=AssetType.SERVER,
        hostname="web-server-01",
        ip_address="10.0.0.1",
        os_type="Ubuntu",
        os_version="22.04",
        criticality=7,
    )

    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)

    assert asset.id is not None
    assert asset.asset_id == "server-001"
    assert asset.is_active is True
    assert asset.created_at is not None


@pytest.mark.asyncio
async def test_asset_vulnerability_relationship(
    db_session: AsyncSession,
    sample_vulnerability: Vulnerability,
    sample_asset: Asset,
):
    """Test many-to-many relationship between assets and vulnerabilities"""
    # Create association
    asset_vuln = AssetVulnerability(
        asset_id=sample_asset.id,
        vulnerability_id=sample_vulnerability.id,
    )
    db_session.add(asset_vuln)
    await db_session.commit()

    # Query to verify
    query = select(AssetVulnerability).where(
        AssetVulnerability.asset_id == sample_asset.id
    )
    result = await db_session.execute(query)
    associations = result.scalars().all()

    assert len(associations) == 1
    assert associations[0].vulnerability_id == sample_vulnerability.id


@pytest.mark.asyncio
async def test_create_patch(db_session: AsyncSession, sample_vulnerability: Vulnerability):
    """Test creating a patch"""
    patch = Patch(
        patch_id="patch-test-001",
        vulnerability_id=sample_vulnerability.id,
        patch_type="script",
        patch_content="#!/bin/bash\necho 'test patch'",
        llm_provider="openai",
        llm_model="gpt-4",
        confidence_score=0.85,
    )

    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    assert patch.id is not None
    assert patch.patch_id == "patch-test-001"
    assert patch.test_status == TestStatus.PENDING
    assert patch.validation_passed is False


@pytest.mark.asyncio
async def test_patch_confidence_score_range(db_session: AsyncSession, sample_vulnerability: Vulnerability):
    """Test that confidence score is validated to be between 0 and 1"""
    # Valid score
    patch = Patch(
        patch_id="patch-valid",
        vulnerability_id=sample_vulnerability.id,
        patch_type="script",
        patch_content="test",
        llm_provider="openai",
        llm_model="gpt-4",
        confidence_score=0.95,
    )
    db_session.add(patch)
    await db_session.commit()

    # Invalid score - this should be caught by check constraint
    patch_invalid = Patch(
        patch_id="patch-invalid",
        vulnerability_id=sample_vulnerability.id,
        patch_type="script",
        patch_content="test",
        llm_provider="openai",
        llm_model="gpt-4",
        confidence_score=1.5,  # Invalid!
    )
    db_session.add(patch_invalid)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_create_deployment(
    db_session: AsyncSession,
    sample_patch: Patch,
    sample_asset: Asset,
):
    """Test creating a deployment"""
    from shared.models.models import DeploymentMethod

    deployment = Deployment(
        deployment_id="deploy-test-001",
        patch_id=sample_patch.id,
        asset_id=sample_asset.id,
        deployment_method=DeploymentMethod.ANSIBLE,
        deployment_strategy="canary",
    )

    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    assert deployment.id is not None
    assert deployment.status == DeploymentStatus.PENDING
    assert deployment.rollback_required is False


@pytest.mark.asyncio
async def test_deployment_relationships(
    db_session: AsyncSession,
    sample_deployment: Deployment,
):
    """Test deployment relationships to patch and asset"""
    # Query deployment with relationships
    query = (
        select(Deployment)
        .where(Deployment.id == sample_deployment.id)
    )
    result = await db_session.execute(query)
    deployment = result.scalar_one()

    # Access relationships (should be loaded)
    assert deployment.patch_id is not None
    assert deployment.asset_id is not None


@pytest.mark.asyncio
async def test_create_audit_log(db_session: AsyncSession):
    """Test creating an audit log entry"""
    audit_log = AuditLog(
        actor_type="user",
        actor_id="admin",
        action="create_vulnerability",
        resource_type="vulnerability",
        resource_id="1",
        success=True,
    )

    db_session.add(audit_log)
    await db_session.commit()
    await db_session.refresh(audit_log)

    assert audit_log.id is not None
    assert audit_log.timestamp is not None
    assert audit_log.success is True


@pytest.mark.asyncio
async def test_create_remediation_job(db_session: AsyncSession):
    """Test creating a remediation job"""
    job = RemediationJob(
        job_id="job-test-001",
        job_type="scan_vulnerabilities",
        priority=8,
        input_data={"scanner": "wazuh"},
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.id is not None
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 0
    assert job.max_retries == 3


@pytest.mark.asyncio
async def test_cascade_delete_vulnerability(
    db_session: AsyncSession,
    sample_vulnerability: Vulnerability,
    sample_patch: Patch,
):
    """Test that deleting a vulnerability cascades to patches"""
    vuln_id = sample_vulnerability.id

    # Delete vulnerability
    await db_session.delete(sample_vulnerability)
    await db_session.commit()

    # Verify patch is also deleted (cascade)
    query = select(Patch).where(Patch.vulnerability_id == vuln_id)
    result = await db_session.execute(query)
    patches = result.scalars().all()

    assert len(patches) == 0  # Should be deleted due to cascade
