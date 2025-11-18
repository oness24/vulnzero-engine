"""
Mock scanner adapter for testing
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

from services.aggregator.scanner_adapter import (
    ScannerAdapter,
    RawVulnerability,
)


class MockAdapter(ScannerAdapter):
    """Mock scanner adapter for testing"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize mock adapter

        Args:
            config: Configuration (can include num_vulnerabilities for testing)
        """
        super().__init__(config)
        self.num_vulnerabilities = config.get("num_vulnerabilities", 10)
        self.authenticated = False

    async def authenticate(self) -> bool:
        """Mock authentication - always succeeds"""
        self.authenticated = True
        return True

    async def fetch_vulnerabilities(
        self,
        since: Optional[datetime] = None,
        severity_filter: Optional[List[str]] = None,
    ) -> List[RawVulnerability]:
        """
        Generate mock vulnerabilities for testing

        Args:
            since: Filter by discovery time
            severity_filter: Filter by severity

        Returns:
            List of mock vulnerabilities
        """
        if not self.authenticated:
            await self.authenticate()

        vulnerabilities = []
        severities = ["critical", "high", "medium", "low"]
        packages = ["openssl", "apache2", "nginx", "postgresql", "redis"]

        for i in range(self.num_vulnerabilities):
            severity = random.choice(severities)
            package = random.choice(packages)
            discovered_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))

            # Apply filters
            if since and discovered_at < since:
                continue
            if severity_filter and severity not in severity_filter:
                continue

            vuln = RawVulnerability(
                scanner_id=f"mock-{i}",
                scanner_name="Mock",
                cve_id=f"CVE-2024-{1000 + i}",
                title=f"Mock {severity} vulnerability in {package}",
                description=f"This is a mock {severity} vulnerability for testing",
                severity=severity,
                cvss_score=self._get_cvss_for_severity(severity),
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                affected_package=package,
                vulnerable_version="1.0.0",
                fixed_version="1.0.1",
                affected_assets=[f"mock-asset-{j}" for j in range(random.randint(1, 5))],
                discovered_at=discovered_at,
                raw_data={"mock": True, "index": i},
            )
            vulnerabilities.append(vuln)

        return vulnerabilities

    async def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        """
        Get mock asset details

        Args:
            asset_id: Asset identifier

        Returns:
            Mock asset details
        """
        return {
            "id": asset_id,
            "name": f"Mock Asset {asset_id}",
            "type": "server",
            "os": "Ubuntu 22.04",
            "ip": f"192.168.1.{random.randint(1, 255)}",
        }

    def _get_cvss_for_severity(self, severity: str) -> float:
        """Get appropriate CVSS score for severity"""
        cvss_ranges = {
            "critical": (9.0, 10.0),
            "high": (7.0, 8.9),
            "medium": (4.0, 6.9),
            "low": (0.1, 3.9),
        }
        min_score, max_score = cvss_ranges.get(severity, (5.0, 5.0))
        return round(random.uniform(min_score, max_score), 1)
