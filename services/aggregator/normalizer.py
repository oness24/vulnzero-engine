"""
Data normalization engine for vulnerability data
"""

from typing import Dict, Any, List
from datetime import datetime
import structlog

from services.aggregator.scanner_adapter import RawVulnerability
from shared.models.models import (
    Vulnerability,
    Asset,
    AssetVulnerability,
    VulnerabilitySeverity,
    VulnerabilityStatus,
    AssetType,
)

logger = structlog.get_logger()


class VulnerabilityNormalizer:
    """Normalizes raw vulnerability data into database models"""

    def __init__(self):
        self.severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
            "info": VulnerabilitySeverity.INFO,
        }

    def normalize_vulnerability(
        self,
        raw_vuln: RawVulnerability,
        enriched_data: Dict[str, Any] | None = None,
    ) -> Vulnerability:
        """
        Normalize raw vulnerability into database model

        Args:
            raw_vuln: Raw vulnerability from scanner
            enriched_data: Optional enriched CVE data from NVD

        Returns:
            Vulnerability model instance
        """
        # Map severity
        severity = self.severity_map.get(
            raw_vuln.severity.lower(),
            VulnerabilitySeverity.MEDIUM,
        )

        # Create vulnerability model
        vulnerability = Vulnerability(
            cve_id=raw_vuln.cve_id or f"NO-CVE-{raw_vuln.scanner_id}",
            title=raw_vuln.title,
            description=raw_vuln.description,
            severity=severity,
            status=VulnerabilityStatus.NEW,
            cvss_score=raw_vuln.cvss_score,
            cvss_vector=raw_vuln.cvss_vector,
            affected_package=raw_vuln.affected_package,
            vulnerable_version=raw_vuln.vulnerable_version,
            fixed_version=raw_vuln.fixed_version,
            scanner_source=raw_vuln.scanner_name,
            raw_scanner_data=raw_vuln.raw_data,
            discovered_at=raw_vuln.discovered_at,
        )

        # Add enriched data if available
        if enriched_data:
            vulnerability.nvd_data = enriched_data.get("nvd_data")
            vulnerability.epss_score = enriched_data.get("epss_score")
            vulnerability.exploit_available = enriched_data.get("exploit_available", False)
            vulnerability.exploit_details = enriched_data.get("exploit_details")

            # Update CVSS if better data available
            if enriched_data.get("cvss_score") and not vulnerability.cvss_score:
                vulnerability.cvss_score = enriched_data["cvss_score"]
            if enriched_data.get("cvss_vector") and not vulnerability.cvss_vector:
                vulnerability.cvss_vector = enriched_data["cvss_vector"]

        return vulnerability

    def normalize_asset(
        self,
        asset_id: str,
        asset_data: Dict[str, Any],
        scanner_name: str,
    ) -> Asset:
        """
        Normalize asset data into database model

        Args:
            asset_id: Unique asset identifier
            asset_data: Raw asset data from scanner
            scanner_name: Name of scanner

        Returns:
            Asset model instance
        """
        # Determine asset type
        asset_type = AssetType.SERVER  # Default
        if "type" in asset_data:
            type_map = {
                "server": AssetType.SERVER,
                "container": AssetType.CONTAINER,
                "vm": AssetType.VIRTUAL_MACHINE,
                "cloud": AssetType.CLOUD_INSTANCE,
            }
            asset_type = type_map.get(
                asset_data["type"].lower(),
                AssetType.SERVER,
            )

        asset = Asset(
            asset_id=asset_id,
            type=asset_type,
            hostname=asset_data.get("name", asset_id),
            ip_address=asset_data.get("ip"),
            os_type=asset_data.get("os", "Unknown"),
            os_version=asset_data.get("os_version"),
            tags={"scanner": scanner_name, **asset_data.get("tags", {})},
            last_scanned=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )

        return asset

    def create_asset_vulnerability_link(
        self,
        vulnerability: Vulnerability,
        asset: Asset,
    ) -> AssetVulnerability:
        """
        Create link between vulnerability and asset

        Args:
            vulnerability: Vulnerability instance
            asset: Asset instance

        Returns:
            AssetVulnerability link
        """
        return AssetVulnerability(
            asset_id=asset.id,
            vulnerability_id=vulnerability.id,
            detected_at=datetime.utcnow(),
        )


class DataDeduplicator:
    """Handles deduplication of vulnerabilities from multiple scanners"""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def deduplicate_vulnerabilities(
        self,
        vulnerabilities: List[RawVulnerability],
    ) -> List[RawVulnerability]:
        """
        Deduplicate vulnerabilities from multiple scanners

        Vulnerabilities are considered duplicates if they have:
        1. Same CVE ID
        2. Same affected package
        3. Same affected assets

        Args:
            vulnerabilities: List of raw vulnerabilities

        Returns:
            Deduplicated list of vulnerabilities
        """
        seen: Dict[str, RawVulnerability] = {}

        for vuln in vulnerabilities:
            # Create deduplication key
            key = self._create_dedup_key(vuln)

            if key in seen:
                # Merge with existing vulnerability
                seen[key] = self._merge_vulnerabilities(seen[key], vuln)
                self.logger.info(
                    "vulnerability_deduplicated",
                    cve_id=vuln.cve_id,
                    scanner=vuln.scanner_name,
                )
            else:
                seen[key] = vuln

        return list(seen.values())

    def _create_dedup_key(self, vuln: RawVulnerability) -> str:
        """
        Create a unique key for deduplication

        Args:
            vuln: Raw vulnerability

        Returns:
            Deduplication key
        """
        # Use CVE ID + affected package as key
        cve_id = vuln.cve_id or "no-cve"
        package = vuln.affected_package or "no-package"
        return f"{cve_id}:{package}"

    def _merge_vulnerabilities(
        self,
        existing: RawVulnerability,
        new: RawVulnerability,
    ) -> RawVulnerability:
        """
        Merge two duplicate vulnerabilities

        Strategy:
        - Keep most recent discovery time
        - Combine affected assets
        - Prefer higher CVSS score
        - Merge scanner data

        Args:
            existing: Existing vulnerability
            new: New vulnerability to merge

        Returns:
            Merged vulnerability
        """
        # Combine affected assets
        combined_assets = list(set(existing.affected_assets + new.affected_assets))

        # Use higher CVSS score if available
        cvss_score = existing.cvss_score or new.cvss_score
        if existing.cvss_score and new.cvss_score:
            cvss_score = max(existing.cvss_score, new.cvss_score)

        # Use most recent discovery
        discovered_at = max(existing.discovered_at, new.discovered_at)

        # Merge scanner data
        merged_raw_data = {
            **existing.raw_data,
            "merged_scanners": [existing.scanner_name, new.scanner_name],
            new.scanner_name: new.raw_data,
        }

        return RawVulnerability(
            scanner_id=existing.scanner_id,
            scanner_name=f"{existing.scanner_name},{new.scanner_name}",
            cve_id=existing.cve_id or new.cve_id,
            title=existing.title,
            description=existing.description or new.description,
            severity=self._choose_higher_severity(existing.severity, new.severity),
            cvss_score=cvss_score,
            cvss_vector=existing.cvss_vector or new.cvss_vector,
            affected_package=existing.affected_package,
            vulnerable_version=existing.vulnerable_version,
            fixed_version=existing.fixed_version or new.fixed_version,
            affected_assets=combined_assets,
            discovered_at=discovered_at,
            raw_data=merged_raw_data,
        )

    def _choose_higher_severity(self, sev1: str, sev2: str) -> str:
        """Choose the higher severity level"""
        severity_order = ["critical", "high", "medium", "low", "info"]
        try:
            idx1 = severity_order.index(sev1.lower())
        except ValueError:
            idx1 = 4  # Default to info

        try:
            idx2 = severity_order.index(sev2.lower())
        except ValueError:
            idx2 = 4

        return severity_order[min(idx1, idx2)]
