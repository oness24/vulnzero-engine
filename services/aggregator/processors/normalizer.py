"""
Vulnerability Data Normalizer

Converts scanner-specific vulnerability data to unified VulnZero schema.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from pydantic import BaseModel, Field
from services.aggregator.scanners.base import RawVulnerability
from shared.models.vulnerability import VulnerabilitySeverity, VulnerabilityStatus

logger = logging.getLogger(__name__)


class NormalizedVulnerability(BaseModel):
    """Normalized vulnerability data in VulnZero schema"""

    cve_id: str
    title: str
    description: Optional[str] = None
    severity: VulnerabilitySeverity
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    affected_package: Optional[str] = None
    affected_version: Optional[str] = None
    fixed_version: Optional[str] = None
    asset_identifier: Optional[str] = None  # IP, hostname, or asset ID
    discovered_at: datetime
    status: VulnerabilityStatus = VulnerabilityStatus.NEW
    source_scanner: str
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class VulnerabilityNormalizer:
    """
    Normalize vulnerability data from different scanner formats.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def normalize(self, raw_vuln: RawVulnerability) -> Optional[NormalizedVulnerability]:
        """
        Normalize raw vulnerability to VulnZero schema.

        Args:
            raw_vuln: Raw vulnerability from scanner

        Returns:
            NormalizedVulnerability or None if normalization fails
        """
        try:
            scanner_type = raw_vuln.scanner_type.lower()

            if scanner_type == "wazuh":
                return self._normalize_wazuh(raw_vuln)
            elif scanner_type == "qualys":
                return self._normalize_qualys(raw_vuln)
            elif scanner_type == "tenable":
                return self._normalize_tenable(raw_vuln)
            elif scanner_type in ["csv", "json"]:
                return self._normalize_generic(raw_vuln)
            else:
                self.logger.warning(f"Unknown scanner type: {scanner_type}")
                return None

        except Exception as e:
            self.logger.error(f"Normalization error for {raw_vuln.scanner_vuln_id}: {e}")
            return None

    def _normalize_wazuh(self, raw_vuln: RawVulnerability) -> NormalizedVulnerability:
        """Normalize Wazuh vulnerability data"""
        data = raw_vuln.raw_data

        # Extract CVE ID
        cve_id = data.get("cve", "UNKNOWN")

        # Map Wazuh severity (usually in severity field)
        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
        }
        severity = severity_map.get(
            data.get("severity", "").lower(),
            VulnerabilitySeverity.MEDIUM
        )

        # Extract CVSS score
        cvss_score = self._extract_cvss_score(data.get("cvss", {}).get("score"))

        return NormalizedVulnerability(
            cve_id=cve_id,
            title=data.get("title", cve_id),
            description=data.get("description"),
            severity=severity,
            cvss_score=cvss_score,
            cvss_vector=data.get("cvss", {}).get("vector"),
            affected_package=data.get("package"),
            affected_version=data.get("version"),
            asset_identifier=data.get("agent_id") or data.get("agent_name"),
            discovered_at=raw_vuln.discovered_at,
            status=VulnerabilityStatus.NEW,
            source_scanner="wazuh",
            raw_data=data,
        )

    def _normalize_qualys(self, raw_vuln: RawVulnerability) -> NormalizedVulnerability:
        """Normalize Qualys vulnerability data"""
        data = raw_vuln.raw_data

        # Qualys uses QID, may have CVE references
        qid = data.get("qid", "")
        cve_id = self._extract_cve_from_qualys(data) or f"QID-{qid}"

        # Map Qualys severity (1-5 scale)
        severity_int = int(data.get("severity", 3))
        severity_map = {
            5: VulnerabilitySeverity.CRITICAL,
            4: VulnerabilitySeverity.HIGH,
            3: VulnerabilitySeverity.MEDIUM,
            2: VulnerabilitySeverity.LOW,
            1: VulnerabilitySeverity.INFO,
        }
        severity = severity_map.get(severity_int, VulnerabilitySeverity.MEDIUM)

        # CVSS score from Qualys
        cvss_score = self._extract_cvss_score(data.get("cvss_base"))

        return NormalizedVulnerability(
            cve_id=cve_id,
            title=data.get("title", cve_id),
            description=data.get("diagnosis"),
            severity=severity,
            cvss_score=cvss_score,
            affected_package=None,  # Qualys doesn't always specify packages
            asset_identifier=data.get("ip"),
            discovered_at=raw_vuln.discovered_at,
            status=VulnerabilityStatus.NEW,
            source_scanner="qualys",
            raw_data=data,
        )

    def _normalize_tenable(self, raw_vuln: RawVulnerability) -> NormalizedVulnerability:
        """Normalize Tenable vulnerability data"""
        data = raw_vuln.raw_data

        # Extract CVE ID
        cve_id = data.get("cve", [None])[0] if isinstance(data.get("cve"), list) else data.get("cve", "UNKNOWN")
        if not cve_id or cve_id == "UNKNOWN":
            cve_id = f"PLUGIN-{data.get('plugin_id', '')}"

        # Map Tenable severity
        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
            "info": VulnerabilitySeverity.INFO,
        }
        severity = severity_map.get(
            data.get("severity", "").lower(),
            VulnerabilitySeverity.MEDIUM
        )

        # Extract CVSS score
        cvss_score = self._extract_cvss_score(data.get("cvss_base_score"))

        return NormalizedVulnerability(
            cve_id=cve_id,
            title=data.get("plugin_name", cve_id),
            description=data.get("description"),
            severity=severity,
            cvss_score=cvss_score,
            cvss_vector=data.get("cvss_vector"),
            affected_package=None,
            asset_identifier=data.get("asset", {}).get("hostname") or data.get("asset", {}).get("ipv4"),
            discovered_at=raw_vuln.discovered_at,
            status=VulnerabilityStatus.NEW,
            source_scanner="tenable",
            raw_data=data,
        )

    def _normalize_generic(self, raw_vuln: RawVulnerability) -> NormalizedVulnerability:
        """Normalize generic CSV/JSON vulnerability data"""
        data = raw_vuln.raw_data

        # Try to extract CVE ID from common field names
        cve_id = (
            data.get("cve_id") or
            data.get("cve") or
            data.get("vulnerability_id") or
            data.get("id") or
            "UNKNOWN"
        )

        # Try to map severity
        severity_str = (
            data.get("severity") or
            data.get("risk") or
            data.get("criticality") or
            "medium"
        ).lower()

        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
            "info": VulnerabilitySeverity.INFO,
            "informational": VulnerabilitySeverity.INFO,
        }
        severity = severity_map.get(severity_str, VulnerabilitySeverity.MEDIUM)

        # Extract CVSS score
        cvss_score = self._extract_cvss_score(
            data.get("cvss_score") or
            data.get("cvss") or
            data.get("score")
        )

        return NormalizedVulnerability(
            cve_id=cve_id,
            title=data.get("title") or data.get("name") or cve_id,
            description=data.get("description") or data.get("summary"),
            severity=severity,
            cvss_score=cvss_score,
            affected_package=data.get("package") or data.get("component"),
            affected_version=data.get("version") or data.get("current_version"),
            fixed_version=data.get("fixed_version") or data.get("patched_version"),
            asset_identifier=data.get("asset") or data.get("host") or data.get("ip"),
            discovered_at=raw_vuln.discovered_at,
            status=VulnerabilityStatus.NEW,
            source_scanner=raw_vuln.scanner_type,
            raw_data=data,
        )

    def _extract_cvss_score(self, score_value: Any) -> Optional[float]:
        """Extract CVSS score from various formats"""
        if score_value is None:
            return None

        try:
            score = float(score_value)
            # Validate CVSS score range
            if 0.0 <= score <= 10.0:
                return round(score, 1)
        except (ValueError, TypeError):
            pass

        return None

    def _extract_cve_from_qualys(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract first CVE ID from Qualys data"""
        cve_list = data.get("cve_list", "")

        if isinstance(cve_list, str) and cve_list:
            cves = cve_list.split(",")
            if cves and cves[0].strip():
                return cves[0].strip()

        return None
