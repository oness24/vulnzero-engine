"""
Vulnerability Deduplication

Identifies and merges duplicate vulnerabilities from multiple scanners.
"""

from typing import List, Dict, Set, Tuple
from collections import defaultdict
import logging

from services.aggregator.processors.normalizer import NormalizedVulnerability

logger = logging.getLogger(__name__)


class VulnerabilityDeduplicator:
    """
    Deduplicate vulnerabilities reported by multiple scanners.

    Strategy:
    1. Group by CVE ID + Asset identifier
    2. Merge duplicate entries, preserving source provenance
    3. Prefer higher severity if conflict
    4. Prefer higher CVSS score if conflict
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def deduplicate(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> List[NormalizedVulnerability]:
        """
        Deduplicate a list of normalized vulnerabilities.

        Args:
            vulnerabilities: List of normalized vulnerabilities

        Returns:
            Deduplicated list of vulnerabilities
        """
        if not vulnerabilities:
            return []

        # Group by dedup key
        grouped = self._group_vulnerabilities(vulnerabilities)

        # Merge duplicates
        deduplicated = []
        for key, vulns in grouped.items():
            if len(vulns) == 1:
                # No duplicates
                deduplicated.append(vulns[0])
            else:
                # Merge duplicates
                merged = self._merge_vulnerabilities(vulns)
                deduplicated.append(merged)
                self.logger.info(
                    f"Merged {len(vulns)} duplicate entries for {key}"
                )

        self.logger.info(
            f"Deduplicated {len(vulnerabilities)} vulnerabilities to {len(deduplicated)}"
        )

        return deduplicated

    def _group_vulnerabilities(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> Dict[Tuple[str, str], List[NormalizedVulnerability]]:
        """
        Group vulnerabilities by deduplication key.

        Key: (CVE ID, Asset identifier)
        """
        grouped = defaultdict(list)

        for vuln in vulnerabilities:
            key = self._get_dedup_key(vuln)
            grouped[key].append(vuln)

        return grouped

    def _get_dedup_key(self, vuln: NormalizedVulnerability) -> Tuple[str, str]:
        """
        Generate deduplication key for vulnerability.

        Returns:
            Tuple of (normalized CVE ID, normalized asset identifier)
        """
        # Normalize CVE ID (remove whitespace, uppercase)
        cve_id = vuln.cve_id.strip().upper()

        # Normalize asset identifier (lowercase, remove whitespace)
        asset_id = (vuln.asset_identifier or "unknown").strip().lower()

        return (cve_id, asset_id)

    def _merge_vulnerabilities(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> NormalizedVulnerability:
        """
        Merge multiple vulnerability entries into one.

        Resolution strategy:
        - CVE ID: Use first non-empty
        - Title: Use longest/most descriptive
        - Description: Concatenate unique descriptions
        - Severity: Use highest severity
        - CVSS Score: Use highest score
        - Asset: Use first
        - Source scanners: Combine all sources
        - Raw data: Merge all raw data with scanner prefixes
        """
        if len(vulnerabilities) == 1:
            return vulnerabilities[0]

        # Sort by severity (highest first), then CVSS score
        sorted_vulns = sorted(
            vulnerabilities,
            key=lambda v: (
                self._severity_to_int(v.severity),
                v.cvss_score or 0.0,
            ),
            reverse=True,
        )

        # Use highest severity vulnerability as base
        base = sorted_vulns[0]

        # Collect all source scanners
        source_scanners = list(set(v.source_scanner for v in vulnerabilities))

        # Merge raw data
        merged_raw_data = {}
        for vuln in vulnerabilities:
            scanner = vuln.source_scanner
            merged_raw_data[f"{scanner}_data"] = vuln.raw_data

        # Use earliest discovery time
        earliest_discovery = min(v.discovered_at for v in vulnerabilities)

        # Create merged vulnerability
        merged = NormalizedVulnerability(
            cve_id=base.cve_id,
            title=self._select_best_title(vulnerabilities),
            description=self._merge_descriptions(vulnerabilities),
            severity=base.severity,  # Highest
            cvss_score=base.cvss_score,  # Highest
            cvss_vector=base.cvss_vector or self._find_first_non_empty(
                vulnerabilities, "cvss_vector"
            ),
            affected_package=base.affected_package or self._find_first_non_empty(
                vulnerabilities, "affected_package"
            ),
            affected_version=base.affected_version or self._find_first_non_empty(
                vulnerabilities, "affected_version"
            ),
            fixed_version=base.fixed_version or self._find_first_non_empty(
                vulnerabilities, "fixed_version"
            ),
            asset_identifier=base.asset_identifier,
            discovered_at=earliest_discovery,
            status=base.status,
            source_scanner=",".join(sorted(source_scanners)),  # Combined sources
            raw_data=merged_raw_data,
        )

        return merged

    def _severity_to_int(self, severity: str) -> int:
        """Convert severity to integer for comparison"""
        severity_map = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "info": 1,
        }
        return severity_map.get(severity.lower(), 0)

    def _select_best_title(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> str:
        """Select the most descriptive title"""
        titles = [v.title for v in vulnerabilities if v.title]

        if not titles:
            return vulnerabilities[0].cve_id

        # Prefer longest title (usually more descriptive)
        return max(titles, key=len)

    def _merge_descriptions(
        self, vulnerabilities: List[NormalizedVulnerability]
    ) -> str:
        """Merge descriptions from multiple sources"""
        descriptions = [v.description for v in vulnerabilities if v.description]

        if not descriptions:
            return None

        # Remove duplicates while preserving order
        unique_descriptions = []
        seen = set()

        for desc in descriptions:
            # Normalize for comparison
            normalized = desc.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_descriptions.append(desc)

        # If all descriptions are the same, return one
        if len(unique_descriptions) == 1:
            return unique_descriptions[0]

        # Otherwise, combine with separator
        return " | ".join(unique_descriptions)

    def _find_first_non_empty(
        self, vulnerabilities: List[NormalizedVulnerability], field: str
    ) -> any:
        """Find first non-empty value for a field"""
        for vuln in vulnerabilities:
            value = getattr(vuln, field, None)
            if value:
                return value
        return None


def deduplicate_vulnerabilities(
    vulnerabilities: List[NormalizedVulnerability],
) -> List[NormalizedVulnerability]:
    """
    Convenience function for deduplication.

    Args:
        vulnerabilities: List of normalized vulnerabilities

    Returns:
        Deduplicated list
    """
    deduplicator = VulnerabilityDeduplicator()
    return deduplicator.deduplicate(vulnerabilities)
