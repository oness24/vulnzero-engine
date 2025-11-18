"""
Tests for patch generator
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.patch_generator.generator import PatchGenerator
from shared.models.models import Vulnerability, Asset, VulnerabilitySeverity, AssetType


@pytest.fixture
def sample_vulnerability():
    """Create sample vulnerability"""
    return Vulnerability(
        id=1,
        cve_id="CVE-2024-1234",
        title="Test Vulnerability",
        description="Test vulnerability description",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=8.5,
        epss_score=0.7,
        status="new",
    )


@pytest.fixture
def sample_asset():
    """Create sample asset"""
    return Asset(
        id=1,
        name="test-server-01",
        asset_type=AssetType.SERVER,
        ip_address="192.168.1.100",
        criticality=8.0,
        metadata={
            "os_type": "ubuntu",
            "os_version": "22.04",
            "environment": "production",
        },
    )


@pytest.fixture
def mock_llm_patch_data():
    """Mock LLM patch data"""
    return {
        "patch_script": "#!/bin/bash\nset -euo pipefail\napt-get install -y nginx",
        "rollback_script": "#!/bin/bash\nset -euo pipefail\napt-get install -y --allow-downgrades nginx=1.18.0-0",
        "validation_script": "#!/bin/bash\ndpkg -l nginx",
        "confidence_score": 85,
        "estimated_duration_minutes": 5,
        "requires_restart": False,
        "risk_assessment": "low",
        "prerequisites": ["root access"],
        "affected_services": ["nginx"],
        "notes": "Test patch",
    }


@pytest.mark.asyncio
async def test_generate_patch_with_llm(sample_vulnerability, sample_asset, mock_llm_patch_data):
    """Test generating patch with LLM"""
    generator = PatchGenerator(llm_provider="openai")

    with patch.object(generator.llm_client, "generate_patch", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_patch_data

        result = await generator.generate_patch(sample_vulnerability, sample_asset, use_llm=True)

        # Verify LLM was called
        mock_generate.assert_called_once()

        # Verify result structure
        assert "patch_script" in result
        assert "rollback_script" in result
        assert "confidence_score" in result
        assert "validation_result" in result
        assert "analysis" in result
        assert result["generation_method"] == "llm"


@pytest.mark.asyncio
async def test_generate_patch_without_llm(sample_vulnerability, sample_asset):
    """Test generating patch without LLM (template-based)"""
    generator = PatchGenerator()

    result = await generator.generate_patch(sample_vulnerability, sample_asset, use_llm=False)

    # Verify result
    assert "patch_script" in result
    assert "rollback_script" in result
    assert result["generation_method"] == "template"
    assert "apt-get" in result["patch_script"]  # Ubuntu uses apt


@pytest.mark.asyncio
async def test_generate_patch_validation(sample_vulnerability, sample_asset, mock_llm_patch_data):
    """Test that generated patches are validated"""
    generator = PatchGenerator()

    with patch.object(generator.llm_client, "generate_patch", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_patch_data

        result = await generator.generate_patch(sample_vulnerability, sample_asset, use_llm=True)

        # Should have validation results
        assert "validation_result" in result
        assert "is_safe" in result["validation_result"]
        assert "risk_level" in result["validation_result"]


@pytest.mark.asyncio
async def test_generate_patch_analysis(sample_vulnerability, sample_asset, mock_llm_patch_data):
    """Test that generated patches are analyzed"""
    generator = PatchGenerator()

    with patch.object(generator.llm_client, "generate_patch", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_patch_data

        result = await generator.generate_patch(sample_vulnerability, sample_asset, use_llm=True)

        # Should have analysis results
        assert "analysis" in result
        assert "requires_restart" in result["analysis"]
        assert "affected_services" in result["analysis"]
        assert "estimated_duration" in result["analysis"]


@pytest.mark.asyncio
async def test_build_context_with_asset(sample_vulnerability, sample_asset):
    """Test building context with asset"""
    generator = PatchGenerator()

    context = generator._build_context(sample_vulnerability, sample_asset)

    assert context["os_type"] == "ubuntu"
    assert context["os_version"] == "22.04"
    assert context["package_manager"] == "apt"
    assert context["asset_criticality"] == 8.0
    assert context["is_production"] is True
    assert context["is_critical"] is True


@pytest.mark.asyncio
async def test_build_context_without_asset(sample_vulnerability):
    """Test building context without asset"""
    generator = PatchGenerator()

    context = generator._build_context(sample_vulnerability, None)

    # Should have defaults
    assert context["os_type"] == "ubuntu"
    assert context["package_manager"] == "apt"
    assert context["asset_criticality"] == 5.0
    assert context["is_production"] is False


def test_calculate_confidence_high_validation():
    """Test confidence calculation with high validation score"""
    generator = PatchGenerator()

    validation_result = {
        "is_safe": True,
        "risk_level": "low",
        "score": 95.0,
    }

    confidence = generator._calculate_confidence(90, validation_result, use_llm=True)

    # Should be high confidence
    assert confidence > 80
    assert confidence <= 95  # Capped at 95


def test_calculate_confidence_unsafe_patch():
    """Test confidence calculation with unsafe patch"""
    generator = PatchGenerator()

    validation_result = {
        "is_safe": False,
        "risk_level": "critical",
        "score": 30.0,
    }

    confidence = generator._calculate_confidence(90, validation_result, use_llm=True)

    # Should be very low confidence
    assert confidence < 30


def test_calculate_confidence_medium_risk():
    """Test confidence calculation with medium risk"""
    generator = PatchGenerator()

    validation_result = {
        "is_safe": True,
        "risk_level": "medium",
        "score": 70.0,
    }

    confidence = generator._calculate_confidence(75, validation_result, use_llm=False)

    # Should be moderate confidence
    assert 40 < confidence < 80


@pytest.mark.asyncio
async def test_generate_template_patch_rhel():
    """Test template patch generation for RHEL"""
    generator = PatchGenerator()

    vulnerability = Vulnerability(
        cve_id="CVE-2024-1234",
        title="Test",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=8.0,
    )

    asset = Asset(
        name="rhel-server",
        asset_type=AssetType.SERVER,
        criticality=5.0,
        metadata={"os_type": "rhel", "os_version": "8.5"},
    )

    context = generator._build_context(vulnerability, asset)
    result = generator._generate_template_patch(vulnerability, context)

    # Should use yum/dnf
    assert "dnf" in result["patch_script"] or "yum" in result["patch_script"]


@pytest.mark.asyncio
async def test_generate_template_patch_opensuse():
    """Test template patch generation for openSUSE"""
    generator = PatchGenerator()

    vulnerability = Vulnerability(
        cve_id="CVE-2024-1234",
        title="Test",
        severity=VulnerabilitySeverity.HIGH,
        cvss_score=8.0,
    )

    asset = Asset(
        name="suse-server",
        asset_type=AssetType.SERVER,
        criticality=5.0,
        metadata={"os_type": "opensuse", "os_version": "15.3"},
    )

    context = generator._build_context(vulnerability, asset)
    result = generator._generate_template_patch(vulnerability, context)

    # Should use zypper
    assert "zypper" in result["patch_script"]


@pytest.mark.asyncio
async def test_regenerate_patch_with_fixes(sample_vulnerability, sample_asset):
    """Test regenerating patch with fixes"""
    generator = PatchGenerator()

    previous_validation = {
        "issues": ["Issue 1", "Issue 2"],
        "warnings": ["Warning 1"],
        "recommendations": ["Recommendation 1"],
    }

    with patch.object(generator, "generate_patch", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = {"confidence_score": 90}

        result = await generator.regenerate_patch_with_fixes(
            sample_vulnerability,
            sample_asset,
            previous_validation,
        )

        # Should call generate_patch with LLM
        mock_generate.assert_called_once_with(sample_vulnerability, sample_asset, use_llm=True)


@pytest.mark.asyncio
async def test_generate_patch_without_asset(sample_vulnerability, mock_llm_patch_data):
    """Test generating generic patch without specific asset"""
    generator = PatchGenerator()

    with patch.object(generator.llm_client, "generate_patch", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_patch_data

        result = await generator.generate_patch(sample_vulnerability, None, use_llm=True)

        # Should still work with default context
        assert "patch_script" in result
        assert result["generation_method"] == "llm"
