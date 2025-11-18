"""
Tenable.io Scanner Integration

Integrates with Tenable.io API to fetch vulnerability data.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from services.aggregator.scanners.base import (
    BaseScanner,
    ScanResult,
    RawVulnerability,
    AuthenticationError,
    ScannerError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class TenableScanner(BaseScanner):
    """
    Tenable.io vulnerability scanner integration.

    Configuration required:
    - api_url: Tenable API endpoint (default: https://cloud.tenable.com)
    - access_key: API access key
    - secret_key: API secret key
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url", "https://cloud.tenable.com").rstrip("/")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "X-ApiKeys": f"accessKey={self.access_key}; secretKey={self.secret_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def authenticate(self) -> bool:
        """
        Test authentication with Tenable API.

        Returns:
            bool: True if authentication successful
        """
        try:
            # Test auth by fetching user info
            response = await self.client.get(f"{self.api_url}/session")

            if response.status_code == 200:
                self.logger.info("Tenable authentication successful")
                return True
            elif response.status_code == 401:
                raise AuthenticationError("Tenable authentication failed: Invalid API keys")
            else:
                raise AuthenticationError(
                    f"Tenable authentication failed: {response.status_code}"
                )

        except httpx.HTTPError as e:
            raise AuthenticationError(f"Tenable authentication error: {e}")

    async def scan(self, target: Optional[str] = None) -> ScanResult:
        """
        Fetch vulnerabilities from Tenable.io.

        Args:
            target: Optional filter criteria (not used for Tenable full export)

        Returns:
            ScanResult with detected vulnerabilities
        """
        scan_id = f"tenable-scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.utcnow()
        vulnerabilities: List[RawVulnerability] = []
        errors: List[str] = []

        try:
            # Export vulnerabilities using Tenable export API
            # Step 1: Initiate export
            export_payload = {
                "num_assets": 5000,
                "filters": {
                    "severity": ["critical", "high", "medium", "low"],
                },
            }

            if target:
                # Add tag filter if target is specified
                export_payload["filters"]["tag.name"] = [target]

            export_response = await self.client.post(
                f"{self.api_url}/vulns/export",
                json=export_payload,
            )

            if export_response.status_code == 429:
                raise RateLimitError("Tenable API rate limit exceeded")

            if export_response.status_code != 200:
                errors.append(f"Tenable export failed: {export_response.status_code}")
                return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

            export_uuid = export_response.json().get("export_uuid")

            # Step 2: Check export status
            # In production, you'd poll this endpoint
            status_response = await self.client.get(
                f"{self.api_url}/vulns/export/{export_uuid}/status"
            )

            if status_response.status_code == 200:
                status_data = status_response.json()

                # Step 3: Download chunks (simplified for MVP)
                # In production, handle pagination properly
                chunks_available = status_data.get("chunks_available", [])

                for chunk_id in chunks_available[:10]:  # Limit to first 10 chunks for MVP
                    chunk_response = await self.client.get(
                        f"{self.api_url}/vulns/export/{export_uuid}/chunks/{chunk_id}"
                    )

                    if chunk_response.status_code == 200:
                        chunk_data = chunk_response.json()

                        for vuln in chunk_data:
                            raw_vuln = RawVulnerability(
                                scanner_id="tenable",
                                scanner_vuln_id=str(vuln.get("plugin_id", "")),
                                raw_data=vuln,
                                discovered_at=datetime.utcnow(),
                                scanner_type="tenable",
                            )
                            vulnerabilities.append(raw_vuln)

                self.logger.info(f"Tenable scan found {len(vulnerabilities)} vulnerabilities")

        except RateLimitError:
            errors.append("Rate limit exceeded")
            self.logger.warning("Tenable API rate limit exceeded")
        except Exception as e:
            errors.append(str(e))
            self.logger.error(f"Tenable scan error: {e}")

        return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

    async def get_vulnerability_details(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific plugin from Tenable.

        Args:
            vuln_id: Tenable plugin ID

        Returns:
            Dict with vulnerability details
        """
        try:
            response = await self.client.get(
                f"{self.api_url}/plugins/plugin/{vuln_id}"
            )

            if response.status_code == 200:
                plugin_data = response.json()
                attributes = plugin_data.get("attributes", [])

                # Extract key attributes
                details = {
                    "plugin_id": plugin_data.get("id"),
                    "plugin_name": plugin_data.get("name"),
                    "family_name": plugin_data.get("family_name"),
                }

                for attr in attributes:
                    attr_name = attr.get("attribute_name")
                    attr_value = attr.get("attribute_value")
                    details[attr_name] = attr_value

                return details

            return {}

        except Exception as e:
            self.logger.error(f"Error fetching Tenable plugin details: {e}")
            return {}

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
