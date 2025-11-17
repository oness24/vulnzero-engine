"""CVE data fetcher for vulnerability information."""
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx


@dataclass
class CVEData:
    """CVE vulnerability data."""

    cve_id: str
    description: str
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    severity: str
    published_date: Optional[str]
    modified_date: Optional[str]
    references: List[str]
    cpe_configurations: List[Dict]
    weaknesses: List[str]


class CVEFetcher:
    """Fetches CVE data from NVD (National Vulnerability Database)."""

    NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize CVE fetcher.

        Args:
            api_key: NVD API key (optional, but recommended for higher rate limits)
        """
        self.api_key = api_key
        self.client = httpx.Client(timeout=30.0)

        # Rate limiting (without API key: 5 requests per 30 seconds)
        # With API key: 50 requests per 30 seconds
        self.rate_limit_delay = 6.0 if not api_key else 0.6

    def fetch_cve(self, cve_id: str) -> Optional[CVEData]:
        """
        Fetch CVE data from NVD API.

        Args:
            cve_id: CVE identifier (e.g., CVE-2024-0001)

        Returns:
            CVEData if found, None otherwise
        """
        try:
            # Respect rate limiting
            time.sleep(self.rate_limit_delay)

            headers = {}
            if self.api_key:
                headers["apiKey"] = self.api_key

            response = self.client.get(
                self.NVD_API_BASE, params={"cveId": cve_id}, headers=headers
            )

            response.raise_for_status()
            data = response.json()

            if not data.get("vulnerabilities"):
                return None

            vuln_data = data["vulnerabilities"][0]
            cve_item = vuln_data["cve"]

            # Extract description
            descriptions = cve_item.get("descriptions", [])
            description = next(
                (d["value"] for d in descriptions if d["lang"] == "en"),
                "No description available",
            )

            # Extract CVSS scores
            cvss_score = None
            cvss_vector = None
            severity = "unknown"

            metrics = cve_item.get("metrics", {})
            if "cvssMetricV31" in metrics:
                cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
                cvss_score = cvss_data.get("baseScore")
                cvss_vector = cvss_data.get("vectorString")
                severity = cvss_data.get("baseSeverity", "unknown").lower()
            elif "cvssMetricV2" in metrics:
                cvss_data = metrics["cvssMetricV2"][0]["cvssData"]
                cvss_score = cvss_data.get("baseScore")
                cvss_vector = cvss_data.get("vectorString")
                # Map V2 score to severity
                if cvss_score:
                    if cvss_score >= 7.0:
                        severity = "high"
                    elif cvss_score >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"

            # Extract references
            references = [ref["url"] for ref in cve_item.get("references", [])]

            # Extract CPE configurations
            configurations = cve_item.get("configurations", [])
            cpe_configs = []
            for config in configurations:
                for node in config.get("nodes", []):
                    cpe_configs.extend(node.get("cpeMatch", []))

            # Extract weaknesses (CWE)
            weaknesses = []
            for weakness in cve_item.get("weaknesses", []):
                for desc in weakness.get("description", []):
                    if desc["lang"] == "en":
                        weaknesses.append(desc["value"])

            return CVEData(
                cve_id=cve_id,
                description=description,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                severity=severity,
                published_date=cve_item.get("published"),
                modified_date=cve_item.get("lastModified"),
                references=references,
                cpe_configurations=cpe_configs,
                weaknesses=weaknesses,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise RuntimeError(f"NVD API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch CVE data: {e}")

    def extract_affected_packages(self, cve_data: CVEData) -> List[Dict[str, str]]:
        """
        Extract affected package information from CVE data.

        Args:
            cve_data: CVE data

        Returns:
            List of affected packages with version information
        """
        packages = []

        for cpe in cve_data.cpe_configurations:
            if not cpe.get("vulnerable", True):
                continue

            criteria = cpe.get("criteria", "")
            # Parse CPE format: cpe:2.3:a:vendor:product:version:...
            parts = criteria.split(":")

            if len(parts) >= 6:
                package_info = {
                    "vendor": parts[3],
                    "product": parts[4],
                    "version": parts[5],
                    "version_start_including": cpe.get("versionStartIncluding"),
                    "version_end_excluding": cpe.get("versionEndExcluding"),
                    "version_start_excluding": cpe.get("versionStartExcluding"),
                    "version_end_including": cpe.get("versionEndIncluding"),
                }
                packages.append(package_info)

        return packages

    def get_package_manager_for_os(self, os_type: str) -> str:
        """
        Determine package manager based on OS type.

        Args:
            os_type: Operating system type

        Returns:
            Package manager name
        """
        os_to_pm = {
            "ubuntu": "apt",
            "debian": "apt",
            "rhel": "yum",
            "centos": "yum",
            "rocky": "dnf",
            "almalinux": "dnf",
            "fedora": "dnf",
            "suse": "zypper",
            "opensuse": "zypper",
            "amazon": "yum",
        }

        return os_to_pm.get(os_type.lower(), "apt")

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
