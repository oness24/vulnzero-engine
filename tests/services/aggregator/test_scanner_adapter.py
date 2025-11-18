"""
Tests for scanner adapters
"""

import pytest
from datetime import datetime, timedelta

from services.aggregator.scanners.mock_adapter import MockAdapter
from services.aggregator.scanner_adapter import RawVulnerability


@pytest.mark.asyncio
async def test_mock_adapter_authentication():
    """Test mock adapter authentication"""
    adapter = MockAdapter({"num_vulnerabilities": 5})

    result = await adapter.authenticate()

    assert result is True
    assert adapter.authenticated is True


@pytest.mark.asyncio
async def test_mock_adapter_fetch_vulnerabilities():
    """Test fetching vulnerabilities from mock adapter"""
    adapter = MockAdapter({"num_vulnerabilities": 10})

    vulnerabilities = await adapter.fetch_vulnerabilities()

    assert len(vulnerabilities) == 10
    assert all(isinstance(v, RawVulnerability) for v in vulnerabilities)
    assert all(v.scanner_name == "Mock" for v in vulnerabilities)


@pytest.mark.asyncio
async def test_mock_adapter_severity_filter():
    """Test filtering vulnerabilities by severity"""
    adapter = MockAdapter({"num_vulnerabilities": 50})

    critical_vulns = await adapter.fetch_vulnerabilities(
        severity_filter=["critical"]
    )

    assert all(v.severity == "critical" for v in critical_vulns)
    assert len(critical_vulns) > 0  # Should have at least some critical


@pytest.mark.asyncio
async def test_mock_adapter_time_filter():
    """Test filtering vulnerabilities by discovery time"""
    adapter = MockAdapter({"num_vulnerabilities": 50})

    # Get vulnerabilities from last 10 days
    since = datetime.utcnow() - timedelta(days=10)
    recent_vulns = await adapter.fetch_vulnerabilities(since=since)

    assert all(v.discovered_at >= since for v in recent_vulns)


@pytest.mark.asyncio
async def test_mock_adapter_combined_filters():
    """Test combining multiple filters"""
    adapter = MockAdapter({"num_vulnerabilities": 100})

    since = datetime.utcnow() - timedelta(days=15)
    filtered_vulns = await adapter.fetch_vulnerabilities(
        since=since,
        severity_filter=["critical", "high"]
    )

    assert all(v.discovered_at >= since for v in filtered_vulns)
    assert all(v.severity in ["critical", "high"] for v in filtered_vulns)


@pytest.mark.asyncio
async def test_mock_adapter_get_asset_details():
    """Test getting asset details"""
    adapter = MockAdapter({})

    asset_details = await adapter.get_asset_details("test-asset-001")

    assert asset_details["id"] == "test-asset-001"
    assert "name" in asset_details
    assert "type" in asset_details
    assert "os" in asset_details


@pytest.mark.asyncio
async def test_mock_adapter_health_check():
    """Test scanner health check"""
    adapter = MockAdapter({})

    is_healthy = await adapter.health_check()

    assert is_healthy is True


def test_normalize_severity():
    """Test severity normalization"""
    adapter = MockAdapter({})

    assert adapter.normalize_severity("Critical") == "critical"
    assert adapter.normalize_severity("HIGH") == "high"
    assert adapter.normalize_severity("Medium") == "medium"
    assert adapter.normalize_severity("low") == "low"
    assert adapter.normalize_severity("informational") == "info"
    assert adapter.normalize_severity("unknown") == "medium"  # Default


@pytest.mark.asyncio
async def test_raw_vulnerability_structure():
    """Test that RawVulnerability has expected structure"""
    adapter = MockAdapter({"num_vulnerabilities": 1})

    vulnerabilities = await adapter.fetch_vulnerabilities()
    vuln = vulnerabilities[0]

    # Check all required fields
    assert vuln.scanner_id is not None
    assert vuln.scanner_name == "Mock"
    assert vuln.cve_id is not None
    assert vuln.title is not None
    assert vuln.severity in ["critical", "high", "medium", "low"]
    assert isinstance(vuln.cvss_score, (float, type(None)))
    assert isinstance(vuln.affected_assets, list)
    assert isinstance(vuln.discovered_at, datetime)
    assert isinstance(vuln.raw_data, dict)


@pytest.mark.asyncio
async def test_mock_adapter_context_manager():
    """Test mock adapter as async context manager"""
    async with MockAdapter({"num_vulnerabilities": 5}) as adapter:
        assert adapter.authenticated is True

        vulns = await adapter.fetch_vulnerabilities()
        assert len(vulns) == 5
