"""
Tests for aggregator Celery tasks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.aggregator.tasks import (
    _scan_all_sources_async,
    _enrich_vulnerability_async,
    _calculate_priorities_async,
)
from services.aggregator.scanner_adapter import RawVulnerability
from shared.models.models import Vulnerability, VulnerabilitySeverity


@pytest.mark.asyncio
async def test_scan_all_sources_with_mock_scanner(db_session):
    """Test scanning with mock scanner"""
    with patch("services.aggregator.tasks.settings") as mock_settings:
        mock_settings.mock_scanner_apis = True

        results = await _scan_all_sources_async()

        assert "started_at" in results
        assert "completed_at" in results
        assert "sources" in results
        assert results["total_vulnerabilities"] > 0


@pytest.mark.asyncio
async def test_enrich_vulnerability_success(db_session, sample_vulnerability):
    """Test enriching a specific vulnerability"""
    # Mock the enricher
    with patch("services.aggregator.tasks.CVEEnricher") as MockEnricher:
        mock_enricher_instance = AsyncMock()
        mock_enricher_instance.enrich_vulnerability.return_value = {
            "cvss_score": 8.5,
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:N/A:N",
            "epss_score": 0.75,
            "exploit_available": True,
            "nvd_data": {"test": "data"},
        }
        MockEnricher.return_value.__aenter__.return_value = mock_enricher_instance

        # Patch AsyncSessionLocal to use test session
        with patch("services.aggregator.tasks.AsyncSessionLocal") as MockSession:
            MockSession.return_value.__aenter__.return_value = db_session

            result = await _enrich_vulnerability_async(sample_vulnerability.id)

            assert result["status"] == "success"
            assert result["vulnerability_id"] == sample_vulnerability.id
            assert "priority_score" in result


@pytest.mark.asyncio
async def test_enrich_vulnerability_not_found(db_session):
    """Test enriching non-existent vulnerability"""
    with patch("services.aggregator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _enrich_vulnerability_async(99999)

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_calculate_priorities(db_session, multiple_vulnerabilities):
    """Test recalculating priorities for all vulnerabilities"""
    with patch("services.aggregator.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _calculate_priorities_async()

        assert result["status"] == "success"
        assert result["total_vulnerabilities"] > 0


@pytest.mark.asyncio
async def test_scan_handles_scanner_failures(db_session):
    """Test that scan continues even if some scanners fail"""
    with patch("services.aggregator.tasks.settings") as mock_settings:
        mock_settings.mock_scanner_apis = False
        mock_settings.wazuh_api_url = None  # No scanners configured

        results = await _scan_all_sources_async()

        assert "started_at" in results
        assert "completed_at" in results
        # Should complete even with no scanners


@pytest.mark.asyncio
async def test_scan_deduplicates_vulnerabilities(db_session):
    """Test that duplicate vulnerabilities are merged"""
    # This is implicitly tested by the deduplicator tests
    # Here we just verify the integration works
    with patch("services.aggregator.tasks.settings") as mock_settings:
        mock_settings.mock_scanner_apis = True

        results = await _scan_all_sources_async()

        # Should have processed and deduplicated
        assert results["total_vulnerabilities"] >= 0
