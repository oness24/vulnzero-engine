"""
Tests for vulnerability normalizer and deduplicator
"""

import pytest
from datetime import datetime, timedelta

from services.aggregator.normalizer import VulnerabilityNormalizer, DataDeduplicator
from services.aggregator.scanner_adapter import RawVulnerability
from shared.models.models import VulnerabilitySeverity, AssetType


def test_normalize_vulnerability_basic():
    """Test basic vulnerability normalization"""
    normalizer = VulnerabilityNormalizer()

    raw_vuln = RawVulnerability(
        scanner_id="test-1",
        scanner_name="TestScanner",
        cve_id="CVE-2024-0001",
        title="Test Vulnerability",
        description="Test description",
        severity="critical",
        cvss_score=9.8,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        affected_package="test-package",
        vulnerable_version="1.0.0",
        fixed_version="1.0.1",
        affected_assets=["asset-1"],
        discovered_at=datetime.utcnow(),
        raw_data={"test": "data"},
    )

    vuln = normalizer.normalize_vulnerability(raw_vuln)

    assert vuln.cve_id == "CVE-2024-0001"
    assert vuln.title == "Test Vulnerability"
    assert vuln.severity == VulnerabilitySeverity.CRITICAL
    assert vuln.cvss_score == 9.8
    assert vuln.scanner_source == "TestScanner"


def test_normalize_vulnerability_with_enrichment():
    """Test vulnerability normalization with enriched data"""
    normalizer = VulnerabilityNormalizer()

    raw_vuln = RawVulnerability(
        scanner_id="test-2",
        scanner_name="TestScanner",
        cve_id="CVE-2024-0002",
        title="Test",
        description=None,
        severity="high",
        cvss_score=None,
        cvss_vector=None,
        affected_package="pkg",
        vulnerable_version=None,
        fixed_version=None,
        affected_assets=[],
        discovered_at=datetime.utcnow(),
        raw_data={},
    )

    enriched_data = {
        "cvss_score": 8.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N",
        "epss_score": 0.75,
        "exploit_available": True,
        "nvd_data": {"references": ["https://example.com"]},
    }

    vuln = normalizer.normalize_vulnerability(raw_vuln, enriched_data)

    assert vuln.cvss_score == 8.5
    assert vuln.epss_score == 0.75
    assert vuln.exploit_available is True
    assert vuln.nvd_data == {"references": ["https://example.com"]}


def test_normalize_vulnerability_without_cve():
    """Test normalization when CVE ID is missing"""
    normalizer = VulnerabilityNormalizer()

    raw_vuln = RawVulnerability(
        scanner_id="test-3",
        scanner_name="TestScanner",
        cve_id=None,
        title="Test",
        description="Test",
        severity="medium",
        cvss_score=5.0,
        cvss_vector=None,
        affected_package="pkg",
        vulnerable_version=None,
        fixed_version=None,
        affected_assets=[],
        discovered_at=datetime.utcnow(),
        raw_data={},
    )

    vuln = normalizer.normalize_vulnerability(raw_vuln)

    # Should create a synthetic ID
    assert vuln.cve_id.startswith("NO-CVE-")
    assert "test-3" in vuln.cve_id


def test_normalize_asset():
    """Test asset normalization"""
    normalizer = VulnerabilityNormalizer()

    asset_data = {
        "name": "web-server-01",
        "type": "server",
        "ip": "192.168.1.100",
        "os": "Ubuntu",
        "os_version": "22.04",
        "tags": {"env": "production"},
    }

    asset = normalizer.normalize_asset("asset-001", asset_data, "Wazuh")

    assert asset.asset_id == "asset-001"
    assert asset.hostname == "web-server-01"
    assert asset.type == AssetType.SERVER
    assert asset.ip_address == "192.168.1.100"
    assert asset.os_type == "Ubuntu"
    assert asset.tags["scanner"] == "Wazuh"
    assert asset.tags["env"] == "production"


def test_deduplicate_no_duplicates():
    """Test deduplication with no duplicates"""
    deduplicator = DataDeduplicator()

    vulnerabilities = [
        RawVulnerability(
            scanner_id=f"test-{i}",
            scanner_name="TestScanner",
            cve_id=f"CVE-2024-000{i}",
            title=f"Test {i}",
            description="Test",
            severity="high",
            cvss_score=7.5,
            cvss_vector=None,
            affected_package=f"package-{i}",
            vulnerable_version=None,
            fixed_version=None,
            affected_assets=[],
            discovered_at=datetime.utcnow(),
            raw_data={},
        )
        for i in range(5)
    ]

    deduplicated = deduplicator.deduplicate_vulnerabilities(vulnerabilities)

    assert len(deduplicated) == 5


def test_deduplicate_with_duplicates():
    """Test deduplication with duplicate vulnerabilities"""
    deduplicator = DataDeduplicator()

    # Create duplicate vulnerabilities (same CVE + package, different scanners)
    vuln1 = RawVulnerability(
        scanner_id="scanner1-cve1",
        scanner_name="Scanner1",
        cve_id="CVE-2024-0001",
        title="Test Vulnerability",
        description="From Scanner 1",
        severity="high",
        cvss_score=7.5,
        cvss_vector=None,
        affected_package="openssl",
        vulnerable_version="1.0.0",
        fixed_version="1.0.1",
        affected_assets=["asset-1", "asset-2"],
        discovered_at=datetime.utcnow() - timedelta(days=1),
        raw_data={"scanner": "scanner1"},
    )

    vuln2 = RawVulnerability(
        scanner_id="scanner2-cve1",
        scanner_name="Scanner2",
        cve_id="CVE-2024-0001",
        title="Test Vulnerability",
        description="From Scanner 2",
        severity="critical",  # Higher severity
        cvss_score=9.0,  # Higher CVSS
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        affected_package="openssl",
        vulnerable_version="1.0.0",
        fixed_version="1.0.1",
        affected_assets=["asset-2", "asset-3"],  # Overlap + new asset
        discovered_at=datetime.utcnow(),
        raw_data={"scanner": "scanner2"},
    )

    deduplicated = deduplicator.deduplicate_vulnerabilities([vuln1, vuln2])

    assert len(deduplicated) == 1
    merged = deduplicated[0]

    # Should have combined assets
    assert len(merged.affected_assets) == 3
    assert set(merged.affected_assets) == {"asset-1", "asset-2", "asset-3"}

    # Should use higher CVSS score
    assert merged.cvss_score == 9.0

    # Should use higher severity
    assert merged.severity == "critical"

    # Should track merged scanners
    assert "merged_scanners" in merged.raw_data


def test_deduplicate_preserves_order():
    """Test that deduplication preserves insertion order"""
    deduplicator = DataDeduplicator()

    vulnerabilities = []
    for i in range(10):
        vuln = RawVulnerability(
            scanner_id=f"test-{i}",
            scanner_name="TestScanner",
            cve_id=f"CVE-2024-{i:04d}",
            title=f"Test {i}",
            description="Test",
            severity="medium",
            cvss_score=5.0,
            cvss_vector=None,
            affected_package=f"pkg-{i}",
            vulnerable_version=None,
            fixed_version=None,
            affected_assets=[],
            discovered_at=datetime.utcnow(),
            raw_data={},
        )
        vulnerabilities.append(vuln)

    deduplicated = deduplicator.deduplicate_vulnerabilities(vulnerabilities)

    # Order should be preserved
    for i, vuln in enumerate(deduplicated):
        assert vuln.cve_id == f"CVE-2024-{i:04d}"


def test_severity_comparison():
    """Test severity comparison in deduplication"""
    deduplicator = DataDeduplicator()

    test_cases = [
        ("critical", "high", "critical"),
        ("high", "medium", "high"),
        ("medium", "low", "medium"),
        ("low", "info", "low"),
        ("critical", "low", "critical"),
    ]

    for sev1, sev2, expected in test_cases:
        result = deduplicator._choose_higher_severity(sev1, sev2)
        assert result == expected
