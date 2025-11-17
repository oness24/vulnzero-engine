"""
Qualys Scanner Integration

Integrates with Qualys API to fetch vulnerability data.
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
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


class QualysScanner(BaseScanner):
    """
    Qualys vulnerability scanner integration.

    Configuration required:
    - api_url: Qualys API endpoint (e.g., https://qualysapi.qualys.com)
    - username: API username
    - password: API password
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_url = config.get("api_url", "").rstrip("/")
        self.username = config.get("username")
        self.password = config.get("password")
        self.client = httpx.AsyncClient(
            auth=(self.username, self.password),
            timeout=60.0,
            headers={"X-Requested-With": "VulnZero"},
        )

    async def authenticate(self) -> bool:
        """
        Test authentication with Qualys API.

        Returns:
            bool: True if authentication successful
        """
        try:
            # Test auth with a simple API call
            response = await self.client.get(
                f"{self.api_url}/api/2.0/fo/knowledge_base/vuln/"
            )

            if response.status_code == 200:
                self.logger.info("Qualys authentication successful")
                return True
            elif response.status_code == 401:
                raise AuthenticationError("Qualys authentication failed: Invalid credentials")
            else:
                raise AuthenticationError(
                    f"Qualys authentication failed: {response.status_code}"
                )

        except httpx.HTTPError as e:
            raise AuthenticationError(f"Qualys authentication error: {e}")

    async def scan(self, target: Optional[str] = None) -> ScanResult:
        """
        Fetch vulnerabilities from Qualys.

        Args:
            target: Optional asset tag or IP range to filter

        Returns:
            ScanResult with detected vulnerabilities
        """
        scan_id = f"qualys-scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.utcnow()
        vulnerabilities: List[RawVulnerability] = []
        errors: List[str] = []

        try:
            # Fetch vulnerability data
            params = {
                "action": "list",
                "details": "All",
                "show_igs": "1",
                "truncation_limit": "1000",
            }

            if target:
                params["ips"] = target

            response = await self.client.get(
                f"{self.api_url}/api/2.0/fo/asset/host/vm/detection/",
                params=params,
            )

            if response.status_code == 429:
                raise RateLimitError("Qualys API rate limit exceeded")

            if response.status_code != 200:
                errors.append(f"Qualys API error: {response.status_code}")
                return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

            # Parse XML response
            try:
                root = ET.fromstring(response.content)
                hosts = root.findall(".//HOST")

                for host in hosts:
                    ip = host.findtext("IP", "")
                    detections = host.findall(".//DETECTION")

                    for detection in detections:
                        qid = detection.findtext("QID", "")
                        vulnerability_data = {
                            "qid": qid,
                            "ip": ip,
                            "type": detection.findtext("TYPE"),
                            "severity": detection.findtext("SEVERITY"),
                            "port": detection.findtext("PORT"),
                            "protocol": detection.findtext("PROTOCOL"),
                            "ssl": detection.findtext("SSL"),
                            "first_found": detection.findtext("FIRST_FOUND_DATETIME"),
                            "last_found": detection.findtext("LAST_FOUND_DATETIME"),
                            "status": detection.findtext("STATUS"),
                        }

                        raw_vuln = RawVulnerability(
                            scanner_id="qualys",
                            scanner_vuln_id=f"QID-{qid}",
                            raw_data=vulnerability_data,
                            discovered_at=datetime.utcnow(),
                            scanner_type="qualys",
                        )
                        vulnerabilities.append(raw_vuln)

                self.logger.info(f"Qualys scan found {len(vulnerabilities)} vulnerabilities")

            except ET.ParseError as e:
                errors.append(f"XML parsing error: {e}")
                self.logger.error(f"Failed to parse Qualys XML response: {e}")

        except RateLimitError:
            errors.append("Rate limit exceeded")
            self.logger.warning("Qualys API rate limit exceeded")
        except Exception as e:
            errors.append(str(e))
            self.logger.error(f"Qualys scan error: {e}")

        return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

    async def get_vulnerability_details(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific QID from Qualys.

        Args:
            vuln_id: Qualys QID (e.g., QID-12345)

        Returns:
            Dict with vulnerability details
        """
        try:
            # Extract QID number
            qid = vuln_id.replace("QID-", "")

            response = await self.client.get(
                f"{self.api_url}/api/2.0/fo/knowledge_base/vuln/",
                params={"action": "list", "details": "All", "ids": qid},
            )

            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                vuln = root.find(".//VULN")

                if vuln is not None:
                    return {
                        "qid": vuln.findtext("QID"),
                        "title": vuln.findtext("TITLE"),
                        "severity": vuln.findtext("SEVERITY_LEVEL"),
                        "category": vuln.findtext("CATEGORY"),
                        "cve_list": vuln.findtext("CVE_LIST", "").split(","),
                        "bugtraq_list": vuln.findtext("BUGTRAQ_LIST", ""),
                        "diagnosis": vuln.findtext("DIAGNOSIS"),
                        "consequence": vuln.findtext("CONSEQUENCE"),
                        "solution": vuln.findtext("SOLUTION"),
                        "pci_flag": vuln.findtext("PCI_FLAG"),
                    }

            return {}

        except Exception as e:
            self.logger.error(f"Error fetching Qualys vulnerability details: {e}")
            return {}

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
