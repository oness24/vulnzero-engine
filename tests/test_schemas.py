"""
Tests for Pydantic schemas
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from shared.models.schemas import (
    VulnerabilityCreate,
    VulnerabilityUpdate,
    AssetCreate,
    AssetUpdate,
    PatchApproval,
    PatchRejection,
    DeploymentRollback,
    UserLogin,
    VulnerabilityFilter,
)
from shared.models.models import (
    VulnerabilitySeverity,
    VulnerabilityStatus,
    AssetType,
)


def test_vulnerability_create_schema():
    """Test VulnerabilityCreate schema validation"""
    data = {
        "cve_id": "CVE-2024-0001",
        "title": "Test Vulnerability",
        "description": "A test vulnerability description",
        "severity": "critical",
        "cvss_score": 9.8,
        "affected_package": "test-package",
        "vulnerable_version": "1.0.0",
        "fixed_version": "1.0.1",
    }

    vuln = VulnerabilityCreate(**data)

    assert vuln.cve_id == "CVE-2024-0001"
    assert vuln.severity == VulnerabilitySeverity.CRITICAL
    assert vuln.cvss_score == 9.8


def test_vulnerability_create_invalid_cvss():
    """Test that CVSS score is validated"""
    with pytest.raises(ValidationError):
        VulnerabilityCreate(
            cve_id="CVE-2024-0001",
            title="Test",
            severity="high",
            cvss_score=11.0,  # Invalid - must be 0-10
        )


def test_vulnerability_update_schema():
    """Test VulnerabilityUpdate schema"""
    data = {
        "status": "remediated",
        "priority_score": 85.5,
    }

    update = VulnerabilityUpdate(**data)

    assert update.status == VulnerabilityStatus.REMEDIATED
    assert update.priority_score == 85.5


def test_asset_create_schema():
    """Test AssetCreate schema validation"""
    data = {
        "asset_id": "server-001",
        "type": "server",
        "hostname": "web-server-01",
        "ip_address": "192.168.1.100",
        "os_type": "Ubuntu",
        "os_version": "22.04",
        "criticality": 8,
        "environment": "production",
    }

    asset = AssetCreate(**data)

    assert asset.asset_id == "server-001"
    assert asset.type == AssetType.SERVER
    assert asset.criticality == 8


def test_asset_create_invalid_criticality():
    """Test that criticality is validated to be 1-10"""
    with pytest.raises(ValidationError):
        AssetCreate(
            asset_id="server-001",
            type="server",
            hostname="test",
            criticality=15,  # Invalid - must be 1-10
        )


def test_asset_update_partial():
    """Test that AssetUpdate allows partial updates"""
    data = {
        "hostname": "new-hostname",
    }

    update = AssetUpdate(**data)

    assert update.hostname == "new-hostname"
    assert update.ip_address is None  # Optional field


def test_patch_approval_schema():
    """Test PatchApproval schema"""
    data = {
        "approved_by": "admin_user",
        "notes": "Patch looks good, approved for deployment",
    }

    approval = PatchApproval(**data)

    assert approval.approved_by == "admin_user"
    assert approval.notes == "Patch looks good, approved for deployment"


def test_patch_rejection_schema():
    """Test PatchRejection schema"""
    data = {
        "rejection_reason": "Patch failed validation tests",
        "rejected_by": "security_team",
    }

    rejection = PatchRejection(**data)

    assert rejection.rejection_reason == "Patch failed validation tests"
    assert rejection.rejected_by == "security_team"


def test_deployment_rollback_schema():
    """Test DeploymentRollback schema"""
    data = {
        "reason": "Service experiencing errors after deployment",
        "requested_by": "ops_engineer",
    }

    rollback = DeploymentRollback(**data)

    assert rollback.reason == "Service experiencing errors after deployment"
    assert rollback.requested_by == "ops_engineer"


def test_user_login_schema():
    """Test UserLogin schema"""
    data = {
        "username": "testuser",
        "password": "securepassword123",
    }

    login = UserLogin(**data)

    assert login.username == "testuser"
    assert login.password == "securepassword123"


def test_vulnerability_filter_schema():
    """Test VulnerabilityFilter schema with pagination"""
    data = {
        "page": 2,
        "page_size": 25,
        "severity": "critical",
        "min_cvss": 7.0,
        "sort_by": "cvss_score",
        "sort_order": "desc",
    }

    filters = VulnerabilityFilter(**data)

    assert filters.page == 2
    assert filters.page_size == 25
    assert filters.severity == VulnerabilitySeverity.CRITICAL
    assert filters.min_cvss == 7.0


def test_vulnerability_filter_pagination_validation():
    """Test that pagination parameters are validated"""
    # Page must be >= 1
    with pytest.raises(ValidationError):
        VulnerabilityFilter(page=0)

    # Page size must be between 1 and 100
    with pytest.raises(ValidationError):
        VulnerabilityFilter(page_size=150)


def test_schema_from_orm_model(sample_vulnerability):
    """Test that schemas can be created from ORM models"""
    from shared.models.schemas import VulnerabilityResponse

    # This tests the from_attributes config
    response = VulnerabilityResponse.model_validate(sample_vulnerability)

    assert response.id == sample_vulnerability.id
    assert response.cve_id == sample_vulnerability.cve_id
    assert response.severity == sample_vulnerability.severity
