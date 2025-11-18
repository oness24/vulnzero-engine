"""
EPSS (Exploit Prediction Scoring System) Client

Fetches exploit probability scores from FIRST.org EPSS API.
"""

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EPSSClient:
    """
    Client for EPSS API.

    EPSS provides probability scores (0-1) that a vulnerability will be exploited.
    API Documentation: https://www.first.org/epss/api
    """

    def __init__(self):
        """Initialize EPSS client"""
        self.base_url = "https://api.first.org/data/v1/epss"
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(days=1)  # Cache for 1 day (EPSS updates daily)

        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

        self.logger = logging.getLogger(__name__)

    async def get_epss_score(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch EPSS score for a CVE.

        Args:
            cve_id: CVE identifier (e.g., CVE-2023-12345)

        Returns:
            Dict with EPSS score and percentile, or None if not found
        """
        # Check cache
        if cve_id in self.cache:
            if datetime.utcnow() < self.cache_expiry.get(cve_id, datetime.min):
                self.logger.debug(f"EPSS cache hit for {cve_id}")
                return self.cache[cve_id]

        try:
            response = await self.client.get(
                self.base_url,
                params={"cve": cve_id},
            )

            if response.status_code == 200:
                data = response.json()
                epss_data = data.get("data", [])

                if epss_data:
                    item = epss_data[0]
                    result = {
                        "cve_id": item.get("cve"),
                        "epss_score": float(item.get("epss", 0)),
                        "epss_percentile": float(item.get("percentile", 0)),
                        "date": item.get("date"),
                        "source": "epss",
                    }

                    # Cache the result
                    self.cache[cve_id] = result
                    self.cache_expiry[cve_id] = datetime.utcnow() + self.cache_ttl

                    return result
                else:
                    self.logger.debug(f"No EPSS data for {cve_id}")
                    return None

            elif response.status_code == 404:
                self.logger.debug(f"CVE not found in EPSS: {cve_id}")
                return None

            else:
                self.logger.error(f"EPSS API error: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching EPSS data for {cve_id}: {e}")
            return None

    async def get_bulk_epss_scores(self, cve_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch EPSS scores for multiple CVEs (up to 30 at a time).

        Args:
            cve_ids: List of CVE identifiers

        Returns:
            Dict mapping CVE ID to EPSS data
        """
        results = {}

        # EPSS API supports bulk requests with comma-separated CVEs
        # But limited to ~30 CVEs per request
        batch_size = 30

        for i in range(0, len(cve_ids), batch_size):
            batch = cve_ids[i:i + batch_size]

            try:
                # Join CVE IDs with comma
                cve_param = ",".join(batch)

                response = await self.client.get(
                    self.base_url,
                    params={"cve": cve_param},
                )

                if response.status_code == 200:
                    data = response.json()
                    epss_data = data.get("data", [])

                    for item in epss_data:
                        cve_id = item.get("cve")
                        results[cve_id] = {
                            "cve_id": cve_id,
                            "epss_score": float(item.get("epss", 0)),
                            "epss_percentile": float(item.get("percentile", 0)),
                            "date": item.get("date"),
                            "source": "epss",
                        }

                        # Cache individual results
                        self.cache[cve_id] = results[cve_id]
                        self.cache_expiry[cve_id] = datetime.utcnow() + self.cache_ttl

                else:
                    self.logger.error(f"EPSS bulk API error: {response.status_code}")

            except Exception as e:
                self.logger.error(f"Error fetching bulk EPSS data: {e}")

        return results

    def interpret_epss_score(self, epss_score: float) -> str:
        """
        Interpret EPSS score into risk level.

        Args:
            epss_score: EPSS probability (0-1)

        Returns:
            Risk level string
        """
        if epss_score >= 0.5:
            return "Very High"
        elif epss_score >= 0.3:
            return "High"
        elif epss_score >= 0.1:
            return "Medium"
        elif epss_score >= 0.01:
            return "Low"
        else:
            return "Very Low"

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
