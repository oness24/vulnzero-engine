"""
NVD (National Vulnerability Database) Client

Fetches CVE details from NVD API 2.0.
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class NVDClient:
    """
    Client for NVD API 2.0.

    API Documentation: https://nvd.nist.gov/developers/vulnerabilities
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NVD client.

        Args:
            api_key: Optional NVD API key for higher rate limits
        """
        self.base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self.api_key = api_key
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(days=1)  # Cache for 1 day

        headers = {"Accept": "application/json"}
        if api_key:
            headers["apiKey"] = api_key

        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
        )

        # Rate limiting: 5 requests per 30 seconds without key, 50 with key
        self.rate_limit = 50 if api_key else 5
        self.rate_window = 30  # seconds
        self.request_times: list = []

        self.logger = logging.getLogger(__name__)

    async def get_cve_details(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch CVE details from NVD.

        Args:
            cve_id: CVE identifier (e.g., CVE-2023-12345)

        Returns:
            Dict with CVE details or None if not found
        """
        # Check cache
        if cve_id in self.cache:
            if datetime.utcnow() < self.cache_expiry.get(cve_id, datetime.min):
                self.logger.debug(f"Cache hit for {cve_id}")
                return self.cache[cve_id]

        # Rate limiting
        await self._rate_limit()

        try:
            response = await self.client.get(
                self.base_url,
                params={"cveId": cve_id},
            )

            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get("vulnerabilities", [])

                if vulnerabilities:
                    cve_item = vulnerabilities[0].get("cve", {})
                    enriched_data = self._extract_cve_data(cve_item)

                    # Cache the result
                    self.cache[cve_id] = enriched_data
                    self.cache_expiry[cve_id] = datetime.utcnow() + self.cache_ttl

                    return enriched_data

            elif response.status_code == 404:
                self.logger.warning(f"CVE not found in NVD: {cve_id}")
                return None

            elif response.status_code == 429:
                self.logger.warning("NVD API rate limit exceeded, retrying...")
                await asyncio.sleep(60)  # Wait 1 minute
                return await self.get_cve_details(cve_id)

            else:
                self.logger.error(f"NVD API error: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching NVD data for {cve_id}: {e}")
            return None

    def _extract_cve_data(self, cve_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and structure CVE data from NVD response"""

        # Extract CVSS scores (v3.1, v3.0, v2.0)
        metrics = cve_item.get("metrics", {})
        cvss_v31 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {}) if metrics.get("cvssMetricV31") else {}
        cvss_v30 = metrics.get("cvssMetricV30", [{}])[0].get("cvssData", {}) if metrics.get("cvssMetricV30") else {}
        cvss_v2 = metrics.get("cvssMetricV2", [{}])[0].get("cvssData", {}) if metrics.get("cvssMetricV2") else {}

        # Use v3.1 if available, else v3.0, else v2.0
        cvss_score = (
            cvss_v31.get("baseScore") or
            cvss_v30.get("baseScore") or
            cvss_v2.get("baseScore")
        )
        cvss_vector = (
            cvss_v31.get("vectorString") or
            cvss_v30.get("vectorString") or
            cvss_v2.get("vectorString")
        )

        # Extract descriptions
        descriptions = cve_item.get("descriptions", [])
        description = next(
            (d.get("value") for d in descriptions if d.get("lang") == "en"),
            descriptions[0].get("value") if descriptions else ""
        )

        # Extract references
        references = cve_item.get("references", [])
        reference_urls = [ref.get("url") for ref in references]

        # Extract CWE (weakness) information
        weaknesses = cve_item.get("weaknesses", [])
        cwe_ids = []
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe_ids.append(desc.get("value"))

        # Published and modified dates
        published_date = cve_item.get("published")
        last_modified_date = cve_item.get("lastModified")

        return {
            "cve_id": cve_item.get("id"),
            "description": description,
            "cvss_score": cvss_score,
            "cvss_vector": cvss_vector,
            "cvss_v31": cvss_v31,
            "cvss_v30": cvss_v30,
            "cvss_v2": cvss_v2,
            "cwe_ids": cwe_ids,
            "references": reference_urls,
            "published_date": published_date,
            "last_modified_date": last_modified_date,
            "source": "nvd",
        }

    async def _rate_limit(self):
        """Implement rate limiting"""
        now = datetime.utcnow()

        # Remove old requests outside the window
        cutoff = now - timedelta(seconds=self.rate_window)
        self.request_times = [t for t in self.request_times if t > cutoff]

        # If at limit, wait
        if len(self.request_times) >= self.rate_limit:
            sleep_time = self.rate_window - (now - self.request_times[0]).total_seconds()
            if sleep_time > 0:
                self.logger.debug(f"Rate limit reached, sleeping for {sleep_time}s")
                await asyncio.sleep(sleep_time)
                # Clear old requests after sleep
                now = datetime.utcnow()
                cutoff = now - timedelta(seconds=self.rate_window)
                self.request_times = [t for t in self.request_times if t > cutoff]

        # Record this request
        self.request_times.append(now)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
