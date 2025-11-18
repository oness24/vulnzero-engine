"""
Tests for vulnerability prioritization
"""

import pytest
from shared.models.models import Vulnerability, VulnerabilitySeverity
from services.aggregator.prioritizer import VulnerabilityPrioritizer


def create_test_vulnerability(**kwargs) -> Vulnerability:
    """Helper to create test vulnerability"""
    defaults = {
        "cve_id": "CVE-2024-0001",
        "title": "Test Vulnerability",
        "severity": VulnerabilitySeverity.HIGH,
        "cvss_score": 7.5,
        "epss_score": 0.5,
        "exploit_available": False,
    }
    defaults.update(kwargs)
    return Vulnerability(**defaults)


def test_prioritizer_initialization():
    """Test prioritizer initialization"""
    prioritizer = VulnerabilityPrioritizer()

    assert prioritizer.weights is not None
    assert "cvss_score" in prioritizer.weights
    assert "epss_score" in prioritizer.weights
    assert sum(prioritizer.weights.values()) == pytest.approx(1.0)


def test_calculate_priority_critical_vulnerability():
    """Test priority calculation for critical vulnerability"""
    prioritizer = VulnerabilityPrioritizer()

    vuln = create_test_vulnerability(
        severity=VulnerabilitySeverity.CRITICAL,
        cvss_score=10.0,
        epss_score=0.9,
        exploit_available=True,
    )

    score = prioritizer.calculate_priority_score(vuln, asset_criticality=10.0)

    # Should be very high priority
    assert score > 90.0
    assert score <= 100.0


def test_calculate_priority_low_vulnerability():
    """Test priority calculation for low severity vulnerability"""
    prioritizer = VulnerabilityPrioritizer()

    vuln = create_test_vulnerability(
        severity=VulnerabilitySeverity.LOW,
        cvss_score=2.0,
        epss_score=0.1,
        exploit_available=False,
    )

    score = prioritizer.calculate_priority_score(vuln, asset_criticality=1.0)

    # Should be low priority
    assert score < 30.0


def test_priority_increases_with_cvss():
    """Test that priority increases with CVSS score"""
    prioritizer = VulnerabilityPrioritizer()

    low_cvss = create_test_vulnerability(cvss_score=3.0)
    high_cvss = create_test_vulnerability(cvss_score=9.0)

    score_low = prioritizer.calculate_priority_score(low_cvss)
    score_high = prioritizer.calculate_priority_score(high_cvss)

    assert score_high > score_low


def test_priority_increases_with_epss():
    """Test that priority increases with EPSS score"""
    prioritizer = VulnerabilityPrioritizer()

    low_epss = create_test_vulnerability(epss_score=0.1)
    high_epss = create_test_vulnerability(epss_score=0.9)

    score_low = prioritizer.calculate_priority_score(low_epss)
    score_high = prioritizer.calculate_priority_score(high_epss)

    assert score_high > score_low


def test_priority_increases_with_exploit_available():
    """Test that known exploits increase priority"""
    prioritizer = VulnerabilityPrioritizer()

    no_exploit = create_test_vulnerability(exploit_available=False)
    with_exploit = create_test_vulnerability(exploit_available=True)

    score_no_exploit = prioritizer.calculate_priority_score(no_exploit)
    score_with_exploit = prioritizer.calculate_priority_score(with_exploit)

    assert score_with_exploit > score_no_exploit


def test_priority_increases_with_asset_criticality():
    """Test that asset criticality affects priority"""
    prioritizer = VulnerabilityPrioritizer()

    vuln = create_test_vulnerability()

    score_low_criticality = prioritizer.calculate_priority_score(vuln, asset_criticality=1.0)
    score_high_criticality = prioritizer.calculate_priority_score(vuln, asset_criticality=10.0)

    assert score_high_criticality > score_low_criticality


def test_prioritize_batch():
    """Test batch prioritization"""
    prioritizer = VulnerabilityPrioritizer()

    vulnerabilities = [
        create_test_vulnerability(
            cve_id=f"CVE-2024-{i:04d}",
            cvss_score=5.0 + i,
        )
        for i in range(5)
    ]

    results = prioritizer.prioritize_batch(vulnerabilities)

    assert len(results) == 5

    # Should be sorted by priority (highest first)
    priorities = [score for _, score in results]
    assert priorities == sorted(priorities, reverse=True)

    # Highest CVSS should have highest priority
    highest_priority_vuln = results[0][0]
    assert highest_priority_vuln.cvss_score == 9.0


def test_get_risk_category():
    """Test risk categorization"""
    prioritizer = VulnerabilityPrioritizer()

    assert prioritizer.get_risk_category(95.0) == "critical"
    assert prioritizer.get_risk_category(75.0) == "high"
    assert prioritizer.get_risk_category(50.0) == "medium"
    assert prioritizer.get_risk_category(30.0) == "low"
    assert prioritizer.get_risk_category(10.0) == "informational"


def test_explain_priority():
    """Test priority explanation"""
    prioritizer = VulnerabilityPrioritizer()

    vuln = create_test_vulnerability(
        severity=VulnerabilitySeverity.CRITICAL,
        cvss_score=9.5,
        epss_score=0.8,
        exploit_available=True,
    )

    explanation = prioritizer.explain_priority(vuln, asset_criticality=8.0)

    assert "total_score" in explanation
    assert "risk_category" in explanation
    assert "feature_contributions" in explanation
    assert "top_factors" in explanation

    # Check feature contributions
    assert "cvss_score" in explanation["feature_contributions"]
    assert "epss_score" in explanation["feature_contributions"]

    # Each contribution should have value, weight, and contribution
    cvss_contrib = explanation["feature_contributions"]["cvss_score"]
    assert "value" in cvss_contrib
    assert "weight" in cvss_contrib
    assert "contribution" in cvss_contrib

    # Top factors should be a list
    assert isinstance(explanation["top_factors"], list)
    assert len(explanation["top_factors"]) <= 3


def test_extract_features_handles_missing_data():
    """Test that feature extraction handles missing data"""
    prioritizer = VulnerabilityPrioritizer()

    vuln = create_test_vulnerability(
        cvss_score=None,
        epss_score=None,
    )

    features = prioritizer._extract_features(vuln, asset_criticality=5.0)

    # Should have default values for missing data
    assert features["cvss_score"] == 0.0
    assert features["epss_score"] == 0.0
    assert features["severity"] > 0.0  # HIGH severity should still map
    assert features["asset_criticality"] == 0.5


def test_priority_score_range():
    """Test that priority scores are always in valid range"""
    prioritizer = VulnerabilityPrioritizer()

    # Test with extreme values
    test_cases = [
        {"cvss_score": 0.0, "epss_score": 0.0, "exploit_available": False},
        {"cvss_score": 10.0, "epss_score": 1.0, "exploit_available": True},
        {"cvss_score": 5.0, "epss_score": 0.5, "exploit_available": False},
    ]

    for kwargs in test_cases:
        vuln = create_test_vulnerability(**kwargs)
        score = prioritizer.calculate_priority_score(vuln)

        assert 0.0 <= score <= 100.0, f"Score {score} out of range for {kwargs}"


def test_batch_prioritization_with_asset_criticalities():
    """Test batch prioritization with asset-specific criticalities"""
    prioritizer = VulnerabilityPrioritizer()

    vulnerabilities = [
        create_test_vulnerability(
            cve_id=f"CVE-2024-{i:04d}",
            cvss_score=7.0,  # Same CVSS
        )
        for i in range(3)
    ]

    # Assign different asset criticalities
    asset_criticalities = {
        0: 10.0,  # Critical asset
        1: 5.0,   # Medium criticality
        2: 1.0,   # Low criticality
    }

    results = prioritizer.prioritize_batch(vulnerabilities, asset_criticalities)

    # Vulnerability on critical asset should have highest priority
    priorities = [score for _, score in results]
    assert priorities[0] > priorities[1] > priorities[2]
