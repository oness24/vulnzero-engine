"""
Vulnerability Enrichment Service

Orchestrates enrichment from multiple sources (NVD, EPSS, Exploit-DB).
"""

from typing import List, Dict, Any
import asyncio
import logging

from services.aggregator.enrichment.nvd_client import NVDClient
from services.aggregator.enrichment.epss_client import EPSSClient
from services.aggregator.enrichment.exploit_db_client import ExploitDBClient
from services.aggregator.processors.normalizer import NormalizedVulnerability

logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Enriches vulnerabilities with data from external sources.
    """

    def __init__(self, nvd_api_key: str = None):
        """
        Initialize enrichment service.

        Args:
            nvd_api_key: Optional NVD API key for higher rate limits
        """
        self.nvd_client = NVDClient(api_key=nvd_api_key)
        self.epss_client = EPSSClient()
        self.exploit_client = ExploitDBClient()
        self.logger = logging.getLogger(__name__)

    async def enrich_vulnerability(
        self, vulnerability: NormalizedVulnerability
    ) -> Dict[str, Any]:
        """
        Enrich a single vulnerability with external data.

        Args:
            vulnerability: Normalized vulnerability

        Returns:
            Dict with enrichment data
        """
        cve_id = vulnerability.cve_id

        # Skip if not a valid CVE ID
        if not cve_id.startswith("CVE-"):
            self.logger.debug(f"Skipping enrichment for non-CVE: {cve_id}")
            return {}

        enrichment_data = {}

        try:
            # Fetch enrichment data concurrently
            nvd_task = self.nvd_client.get_cve_details(cve_id)
            epss_task = self.epss_client.get_epss_score(cve_id)
            exploit_task = self.exploit_client.check_exploit_availability(cve_id)

            # Wait for all tasks
            nvd_data, epss_data, exploit_data = await asyncio.gather(
                nvd_task, epss_task, exploit_task,
                return_exceptions=True
            )

            # Handle NVD data
            if isinstance(nvd_data, dict) and nvd_data:
                enrichment_data.update(nvd_data)

            # Handle EPSS data
            if isinstance(epss_data, dict) and epss_data:
                enrichment_data["epss_score"] = epss_data.get("epss_score")
                enrichment_data["epss_percentile"] = epss_data.get("epss_percentile")

            # Handle exploit data
            if isinstance(exploit_data, dict):
                enrichment_data["exploit_available"] = exploit_data.get("exploit_available", False)
                enrichment_data["exploit_maturity"] = exploit_data.get("exploit_maturity", "none")
                enrichment_data["in_cisa_kev"] = exploit_data.get("in_cisa_kev", False)

            self.logger.info(f"Enriched {cve_id} with {len(enrichment_data)} fields")

        except Exception as e:
            self.logger.error(f"Enrichment error for {cve_id}: {e}")

        return enrichment_data

    async def enrich_vulnerabilities(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple vulnerabilities.

        Args:
            vulnerabilities: List of normalized vulnerabilities

        Returns:
            List of enrichment data dicts
        """
        # Limit concurrent enrichment to avoid overwhelming APIs
        semaphore = asyncio.Semaphore(5)

        async def enrich_with_limit(vuln):
            async with semaphore:
                return await self.enrich_vulnerability(vuln)

        # Enrich all vulnerabilities concurrently (with limit)
        enrichment_tasks = [
            enrich_with_limit(vuln) for vuln in vulnerabilities
        ]

        enrichment_results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = [
            result for result in enrichment_results
            if isinstance(result, dict)
        ]

        self.logger.info(f"Enriched {len(valid_results)}/{len(vulnerabilities)} vulnerabilities")

        return valid_results

    async def close(self):
        """Close all clients"""
        await self.nvd_client.client.aclose()
        await self.epss_client.client.aclose()
        await self.exploit_client.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
