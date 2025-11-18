"""
Unit Tests for Pydantic Schemas

Tests data validation for API request/response schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from services.api_gateway.schemas.vulnerability import (
    VulnerabilityCreate,
    VulnerabilityUpdate,
    VulnerabilityResponse
)
from services.api_gateway.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse
)
from services.api_gateway.schemas.patch import (
    PatchCreate,
    PatchUpdate,
    PatchResponse
)


class TestVulnerabilitySchemas:
    """Test Vulnerability schemas"""

    def test_vulnerability_create_valid(self):
        """Test creating vulnerability with valid data"""
        data = {
            "cve_id": "CVE-2024-12345",
            "title": "Test Vulnerability",
            "description": "Test description",
            "severity": "critical",
            "cvss_score": 9.5,
            "affected_package": "test-package",
            "affected_version": "1.0.0"
        }
        vuln = VulnerabilityCreate(**data)

        assert vuln.cve_id == "CVE-2024-12345"
        assert vuln.severity == "critical"
        assert vuln.cvss_score == 9.5

    def test_vulnerability_create_invalid_cvss(self):
        """Test validation fails for invalid CVSS score"""
        data = {
            "cve_id": "CVE-2024-12345",
            "title": "Test",
            "severity": "high",
            "cvss_score": 11.0,  # Invalid: > 10.0
            "affected_package": "test"
        }

        with pytest.raises(ValidationError) as exc:
            VulnerabilityCreate(**data)

        assert "cvss_score" in str(exc.value)

    def test_vulnerability_create_missing_required(self):
        """Test validation fails when required fields missing"""
        data = {
            "cve_id": "CVE-2024-12345",
            # Missing title and other required fields
        }

        with pytest.raises(ValidationError):
            VulnerabilityCreate(**data)

    def test_vulnerability_update_partial(self):
        """Test partial update with only some fields"""
        data = {
            "status": "patched",
            "priority_score": 85.0
        }
        update = VulnerabilityUpdate(**data)

        assert update.status == "patched"
        assert update.priority_score == 85.0
        assert update.title is None  # Other fields should be None


class TestAssetSchemas:
    """Test Asset schemas"""

    def test_asset_create_valid(self):
        """Test creating asset with valid data"""
        data = {
            "hostname": "test-server",
            "ip_address": "192.168.1.100",
            "asset_type": "server",
            "os_type": "Ubuntu",
            "os_version": "22.04"
        }
        asset = AssetCreate(**data)

        assert asset.hostname == "test-server"
        assert asset.ip_address == "192.168.1.100"
        assert asset.asset_type == "server"

    def test_asset_create_invalid_ip(self):
        """Test validation fails for invalid IP address"""
        data = {
            "hostname": "test-server",
            "ip_address": "999.999.999.999",  # Invalid IP
            "asset_type": "server"
        }

        with pytest.raises(ValidationError) as exc:
            AssetCreate(**data)

        assert "ip_address" in str(exc.value)

    def test_asset_create_with_metadata(self):
        """Test creating asset with metadata"""
        data = {
            "hostname": "test-server",
            "asset_type": "server",
            "metadata": {
                "environment": "production",
                "region": "us-east-1",
                "tags": ["web", "api"]
            }
        }
        asset = AssetCreate(**data)

        assert asset.metadata["environment"] == "production"
        assert "tags" in asset.metadata


class TestPatchSchemas:
    """Test Patch schemas"""

    def test_patch_create_valid(self):
        """Test creating patch with valid data"""
        data = {
            "vulnerability_id": 1,
            "title": "Fix for CVE-2024-12345",
            "description": "Security patch",
            "patch_type": "script_execution",
            "patch_content": "#!/bin/bash\\necho 'patching'",
            "confidence_score": 85.5
        }
        patch = PatchCreate(**data)

        assert patch.vulnerability_id == 1
        assert patch.patch_type == "script_execution"
        assert patch.confidence_score == 85.5

    def test_patch_create_invalid_confidence(self):
        """Test validation fails for invalid confidence score"""
        data = {
            "vulnerability_id": 1,
            "title": "Test Patch",
            "patch_type": "script_execution",
            "patch_content": "test",
            "confidence_score": 150.0  # Invalid: > 100
        }

        with pytest.raises(ValidationError) as exc:
            PatchCreate(**data)

        assert "confidence_score" in str(exc.value)

    def test_patch_update_status(self):
        """Test updating patch status"""
        data = {
            "status": "approved"
        }
        update = PatchUpdate(**data)

        assert update.status == "approved"


class TestSchemaValidation:
    """Test general schema validation rules"""

    def test_empty_string_not_allowed(self):
        """Test empty strings are rejected for required fields"""
        data = {
            "cve_id": "",  # Empty string
            "title": "Test",
            "severity": "high",
            "cvss_score": 7.5,
            "affected_package": "test"
        }

        with pytest.raises(ValidationError):
            VulnerabilityCreate(**data)

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored with default config"""
        data = {
            "cve_id": "CVE-2024-12345",
            "title": "Test",
            "severity": "high",
            "cvss_score": 7.5,
            "affected_package": "test",
            "extra_field": "should be ignored"  # Extra field
        }

        # Should not raise error, extra field ignored
        vuln = VulnerabilityCreate(**data)
        assert not hasattr(vuln, 'extra_field')

    def test_type_coercion(self):
        """Test type coercion for compatible types"""
        data = {
            "cve_id": "CVE-2024-12345",
            "title": "Test",
            "severity": "high",
            "cvss_score": "7.5",  # String instead of float
            "affected_package": "test"
        }

        vuln = VulnerabilityCreate(**data)
        assert isinstance(vuln.cvss_score, float)
        assert vuln.cvss_score == 7.5
