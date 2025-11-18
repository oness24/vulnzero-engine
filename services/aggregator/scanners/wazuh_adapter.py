"""
Wazuh vulnerability scanner adapter
"""

import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog

from services.aggregator.scanner_adapter import (
    ScannerAdapter,
    RawVulnerability,
    ScannerAuthenticationError,
    ScannerFetchError,
)

logger = structlog.get_logger()


class WazuhAdapter(ScannerAdapter):
    """Adapter for Wazuh vulnerability scanner"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Wazuh adapter

        Args:
            config: Configuration with api_url, username, password, verify_ssl
        """
        super().__init__(config)
        self.api_url = config.get("api_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.verify_ssl = config.get("verify_ssl", True)
        self.token = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    async def authenticate(self) -> bool:
        """
        Authenticate with Wazuh API

        Returns:
            True if authentication successful
        """
        try:
            session = await self._get_session()

            auth_url = f"{self.api_url}/security/user/authenticate"

            async with session.post(
                auth_url,
                auth=aiohttp.BasicAuth(self.username, self.password),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("data", {}).get("token")
                    logger.info("wazuh_authentication_successful")
                    return True
                else:
                    raise ScannerAuthenticationError(
                        f"Wazuh authentication failed: {response.status}"
                    )

        except Exception as e:
            logger.error("wazuh_authentication_failed", error=str(e))
            raise ScannerAuthenticationError(f"Wazuh authentication error: {e}")

    async def fetch_vulnerabilities(
        self,
        since: Optional[datetime] = None,
        severity_filter: Optional[List[str]] = None,
    ) -> List[RawVulnerability]:
        """
        Fetch vulnerabilities from Wazuh

        Args:
            since: Only fetch vulnerabilities discovered since this time
            severity_filter: Filter by severity levels

        Returns:
            List of raw vulnerabilities
        """
        if not self.token:
            await self.authenticate()

        try:
            session = await self._get_session()
            headers = {"Authorization": f"Bearer {self.token}"}

            # Wazuh vulnerability detection endpoint
            vuln_url = f"{self.api_url}/vulnerability"

            params: Dict[str, Any] = {
                "limit": 1000,
                "offset": 0,
            }

            vulnerabilities = []

            async with session.get(vuln_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    raw_vulns = data.get("data", {}).get("affected_items", [])

                    for vuln in raw_vulns:
                        # Parse Wazuh vulnerability data
                        raw_vuln = self._parse_wazuh_vulnerability(vuln)

                        # Apply filters
                        if since and raw_vuln.discovered_at < since:
                            continue

                        if severity_filter and raw_vuln.severity not in severity_filter:
                            continue

                        vulnerabilities.append(raw_vuln)

                    logger.info(
                        "wazuh_vulnerabilities_fetched",
                        count=len(vulnerabilities),
                    )

                    return vulnerabilities

                else:
                    raise ScannerFetchError(
                        f"Wazuh fetch failed: {response.status}"
                    )

        except Exception as e:
            logger.error("wazuh_fetch_failed", error=str(e))
            raise ScannerFetchError(f"Wazuh fetch error: {e}")

    def _parse_wazuh_vulnerability(self, vuln_data: Dict[str, Any]) -> RawVulnerability:
        """
        Parse Wazuh vulnerability data into RawVulnerability

        Args:
            vuln_data: Raw vulnerability data from Wazuh

        Returns:
            Parsed RawVulnerability
        """
        cve_id = vuln_data.get("cve")
        severity = vuln_data.get("severity", "medium")

        # Parse CVSS score
        cvss_score = None
        cvss_vector = None
        if "cvss" in vuln_data:
            cvss_data = vuln_data["cvss"]
            if isinstance(cvss_data, dict):
                cvss_score = cvss_data.get("cvss3", {}).get("base_score")
                cvss_vector = cvss_data.get("cvss3", {}).get("vector_string")

        # Get affected package
        package_name = vuln_data.get("package", {}).get("name")
        package_version = vuln_data.get("package", {}).get("version")

        # Affected assets (agents in Wazuh)
        affected_assets = []
        if "agent_id" in vuln_data:
            affected_assets.append(vuln_data["agent_id"])

        # Discovery time
        discovered_at = datetime.utcnow()
        if "detection_time" in vuln_data:
            try:
                discovered_at = datetime.fromisoformat(
                    vuln_data["detection_time"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        return RawVulnerability(
            scanner_id=f"wazuh-{cve_id}-{package_name}",
            scanner_name="Wazuh",
            cve_id=cve_id,
            title=vuln_data.get("title", f"Vulnerability in {package_name}"),
            description=vuln_data.get("description"),
            severity=self.normalize_severity(severity),
            cvss_score=cvss_score,
            cvss_vector=cvss_vector,
            affected_package=package_name,
            vulnerable_version=package_version,
            fixed_version=vuln_data.get("package", {}).get("fixed_version"),
            affected_assets=affected_assets,
            discovered_at=discovered_at,
            raw_data=vuln_data,
        )

    async def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        """
        Get Wazuh agent details

        Args:
            asset_id: Wazuh agent ID

        Returns:
            Agent details
        """
        if not self.token:
            await self.authenticate()

        try:
            session = await self._get_session()
            headers = {"Authorization": f"Bearer {self.token}"}

            agent_url = f"{self.api_url}/agents/{asset_id}"

            async with session.get(agent_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("affected_items", [{}])[0]
                else:
                    return {}

        except Exception as e:
            logger.error("wazuh_asset_fetch_failed", asset_id=asset_id, error=str(e))
            return {}

    async def close(self) -> None:
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
