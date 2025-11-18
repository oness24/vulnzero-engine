"""
Tests for CVE enrichment service
"""

import pytest
from unittest.mock import AsyncMock, patch

from services.aggregator.enrichment import CVEEnricher


@pytest.mark.asyncio
async def test_cve_enricher_initialization():
    """Test CVE enricher initialization"""
    enricher = CVEEnricher(nvd_api_key="test-key")

    assert enricher.nvd_api_key == "test-key"
    assert enricher.nvd_base_url is not None
    assert enricher.epss_base_url is not None
    assert enricher.cache == {}


@pytest.mark.asyncio
async def test_enrich_vulnerability_invalid_cve():
    """Test enrichment with invalid CVE ID"""
    enricher = CVEEnricher()

    result = await enricher.enrich_vulnerability("INVALID-ID")

    assert result == {}


@pytest.mark.asyncio
async def test_enrich_vulnerability_caching():
    """Test that enrichment results are cached"""
    enricher = CVEEnricher()

    # Mock the fetch methods
    enricher._fetch_nvd_data = AsyncMock(return_value={
        "cvss_score": 7.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    })
    enricher._fetch_epss_score = AsyncMock(return_value=0.5)
    enricher._check_exploits = AsyncMock(return_value=False)

    # First call
    result1 = await enricher.enrich_vulnerability("CVE-2024-0001")
    assert enricher._fetch_nvd_data.call_count == 1

    # Second call - should use cache
    result2 = await enricher.enrich_vulnerability("CVE-2024-0001")
    assert enricher._fetch_nvd_data.call_count == 1  # Not called again

    assert result1["cve_id"] == result2["cve_id"]
    assert result1["cvss_score"] == result2["cvss_score"]


@pytest.mark.asyncio
async def test_parse_nvd_response():
    """Test parsing NVD API response"""
    enricher = CVEEnricher()

    nvd_data = {
        "metrics": {
            "cvssMetricV31": [
                {
                    "cvssData": {
                        "baseScore": 9.8,
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                    }
                }
            ]
        },
        "references": [
            {"url": "https://example.com/vuln1"},
            {"url": "https://example.com/vuln2"},
        ],
        "published": "2024-01-01T00:00:00.000",
        "descriptions": [
            {"value": "Test vulnerability description"}
        ],
    }

    result = enricher._parse_nvd_response(nvd_data)

    assert result["cvss_score"] == 9.8
    assert "CVSS:3.1" in result["cvss_vector"]
    assert len(result["references"]) == 2
    assert result["published_date"] == "2024-01-01T00:00:00.000"
    assert "vulnerability description" in result["description"]


@pytest.mark.asyncio
async def test_parse_nvd_response_cvss_v30_fallback():
    """Test parsing NVD response with CVSS v3.0 fallback"""
    enricher = CVEEnricher()

    nvd_data = {
        "metrics": {
            "cvssMetricV30": [
                {
                    "cvssData": {
                        "baseScore": 7.5,
                        "vectorString": "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
                    }
                }
            ]
        },
        "references": [],
    }

    result = enricher._parse_nvd_response(nvd_data)

    assert result["cvss_score"] == 7.5
    assert "CVSS:3.0" in result["cvss_vector"]


@pytest.mark.asyncio
async def test_check_exploits_returns_false_for_mvp():
    """Test that exploit checking returns False for MVP"""
    enricher = CVEEnricher()

    result = await enricher._check_exploits("CVE-2024-0001")

    # MVP implementation returns False
    assert result is False


@pytest.mark.asyncio
async def test_enricher_context_manager():
    """Test CVE enricher as async context manager"""
    async with CVEEnricher() as enricher:
        assert enricher is not None

    # Session should be closed after context
    if enricher.session:
        assert enricher.session.closed


@pytest.mark.asyncio
async def test_enrich_vulnerability_combines_all_sources():
    """Test that enrichment combines NVD and EPSS data"""
    enricher = CVEEnricher()

    # Mock all data sources
    enricher._fetch_nvd_data = AsyncMock(return_value={
        "cvss_score": 8.5,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-0001"],
        "published_date": "2024-01-01",
    })
    enricher._fetch_epss_score = AsyncMock(return_value=0.85)
    enricher._check_exploits = AsyncMock(return_value=True)

    result = await enricher.enrich_vulnerability("CVE-2024-0001")

    assert result["cve_id"] == "CVE-2024-0001"
    assert result["cvss_score"] == 8.5
    assert result["epss_score"] == 0.85
    assert result["exploit_available"] is True
    assert "nvd_data" in result
    assert len(result["nvd_data"]["references"]) > 0
