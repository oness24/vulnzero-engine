"""
Wazuh Scanner Integration

Integrates with Wazuh API to fetch vulnerability data.
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


class WazuhScanner(BaseScanner):
    """
    Wazuh vulnerability scanner integration.

    Configuration required:
    - api_url: Wazuh API endpoint (e.g., https://wazuh.example.com:55000)
    - username: API username
    - password: API password
    - verify_ssl: Whether to verify SSL certificates (default: True)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url", "").rstrip("/")
        self.username = config.get("username")
        self.password = config.get("password")
        self.verify_ssl = config.get("verify_ssl", True)
        self.token: Optional[str] = None
        self.client = httpx.AsyncClient(
            verify=self.verify_ssl,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def authenticate(self) -> bool:
        """
        Authenticate with Wazuh API and get JWT token.

        Returns:
            bool: True if authentication successful
        """
        try:
            response = await self.client.post(
                f"{self.api_url}/security/user/authenticate",
                auth=(self.username, self.password),
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("data", {}).get("token")
                self.client.headers["Authorization"] = f"Bearer {self.token}"
                self.logger.info("Wazuh authentication successful")
                return True
            else:
                raise AuthenticationError(
                    f"Wazuh authentication failed: {response.status_code} - {response.text}"
                )

        except httpx.HTTPError as e:
            raise AuthenticationError(f"Wazuh authentication error: {e}")

    async def scan(self, target: Optional[str] = None) -> ScanResult:
        """
        Fetch vulnerabilities from Wazuh.

        Args:
            target: Optional agent ID to filter vulnerabilities

        Returns:
            ScanResult with detected vulnerabilities
        """
        scan_id = f"wazuh-scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.utcnow()
        vulnerabilities: List[RawVulnerability] = []
        errors: List[str] = []

        try:
            # Ensure authenticated
            if not self.token:
                await self.authenticate()

            # Fetch vulnerabilities
            params = {"limit": 500, "offset": 0}
            if target:
                params["agent_id"] = target

            response = await self.client.get(
                f"{self.api_url}/vulnerability",
                params=params,
            )

            if response.status_code == 429:
                raise RateLimitError("Wazuh API rate limit exceeded")

            if response.status_code != 200:
                errors.append(f"Wazuh API error: {response.status_code}")
                return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

            data = response.json()
            vuln_items = data.get("data", {}).get("affected_items", [])

            for item in vuln_items:
                raw_vuln = RawVulnerability(
                    scanner_id="wazuh",
                    scanner_vuln_id=item.get("cve", ""),
                    raw_data=item,
                    discovered_at=datetime.utcnow(),
                    scanner_type="wazuh",
                )
                vulnerabilities.append(raw_vuln)

            self.logger.info(f"Wazuh scan found {len(vulnerabilities)} vulnerabilities")

        except RateLimitError:
            errors.append("Rate limit exceeded")
            self.logger.warning("Wazuh API rate limit exceeded")
        except Exception as e:
            errors.append(str(e))
            self.logger.error(f"Wazuh scan error: {e}")

        return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

    async def get_vulnerability_details(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific CVE from Wazuh.

        Args:
            vuln_id: CVE ID (e.g., CVE-2023-12345)

        Returns:
            Dict with vulnerability details
        """
        try:
            if not self.token:
                await self.authenticate()

            response = await self.client.get(
                f"{self.api_url}/vulnerability/{vuln_id}"
            )

            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                self.logger.warning(f"Failed to get Wazuh details for {vuln_id}")
                return {}

        except Exception as e:
            self.logger.error(f"Error fetching Wazuh vulnerability details: {e}")
            return {}

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
