"""
ML-Based Priority Scoring System

Calculates priority scores (0-100) for vulnerability remediation based on multiple factors.

For MVP: Uses weighted scoring algorithm.
For Production: Replace with trained XGBoost/RandomForest model.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from services.aggregator.processors.normalizer import NormalizedVulnerability

logger = logging.getLogger(__name__)


class PriorityScorer:
    """
    Calculate priority scores for vulnerabilities.

    Factors considered:
    1. CVSS Score (0-10) - 25% weight
    2. EPSS Score (0-1) - 25% weight
    3. Exploit Availability - 20% weight
    4. Asset Criticality - 15% weight
    5. Vulnerability Age - 10% weight
    6. CISA KEV Status - 5% bonus

    Output: Priority score 0-100 (higher = more urgent)
    """

    def __init__(self):
        """Initialize priority scorer"""
        self.logger = logging.getLogger(__name__)

        # Weights for each factor
        self.weights = {
            "cvss": 0.25,
            "epss": 0.25,
            "exploit": 0.20,
            "criticality": 0.15,
            "age": 0.10,
            "patch_available": 0.05,
        }

    def calculate_priority(
        self,
        vulnerability: NormalizedVulnerability,
        enrichment_data: Dict[str, Any] = None,
        asset_criticality: int = 3,  # 1-5 scale, default medium
    ) -> float:
        """
        Calculate priority score for a vulnerability.

        Args:
            vulnerability: Normalized vulnerability
            enrichment_data: Enrichment data (NVD, EPSS, Exploit-DB)
            asset_criticality: Asset criticality level (1-5)

        Returns:
            Priority score (0-100)
        """
        enrichment_data = enrichment_data or {}

        # Calculate component scores
        cvss_score = self._score_cvss(vulnerability, enrichment_data)
        epss_score = self._score_epss(enrichment_data)
        exploit_score = self._score_exploit_availability(enrichment_data)
        criticality_score = self._score_asset_criticality(asset_criticality)
        age_score = self._score_vulnerability_age(vulnerability)
        patch_score = self._score_patch_availability(vulnerability)

        # Calculate weighted total
        priority = (
            (cvss_score * self.weights["cvss"]) +
            (epss_score * self.weights["epss"]) +
            (exploit_score * self.weights["exploit"]) +
            (criticality_score * self.weights["criticality"]) +
            (age_score * self.weights["age"]) +
            (patch_score * self.weights["patch_available"])
        ) * 100

        # Bonus for CISA KEV
        if enrichment_data.get("in_cisa_kev"):
            priority = min(100, priority * 1.2)  # 20% bonus, cap at 100

        # Ensure score is in range
        priority = max(0, min(100, priority))

        self.logger.debug(
            f"Priority for {vulnerability.cve_id}: {priority:.1f} "
            f"(CVSS:{cvss_score:.2f}, EPSS:{epss_score:.2f}, "
            f"Exploit:{exploit_score:.2f}, Age:{age_score:.2f})"
        )

        return round(priority, 1)

    def _score_cvss(
        self,
        vulnerability: NormalizedVulnerability,
        enrichment_data: Dict[str, Any]
    ) -> float:
        """
        Score based on CVSS (0-1 scale).

        CVSS is 0-10, normalize to 0-1
        """
        # Prefer enriched CVSS, fall back to scanner CVSS
        cvss = enrichment_data.get("cvss_score") or vulnerability.cvss_score

        if cvss is None:
            # No CVSS, use severity mapping
            severity_map = {
                "critical": 9.5,
                "high": 7.5,
                "medium": 5.0,
                "low": 3.0,
                "info": 1.0,
            }
            cvss = severity_map.get(vulnerability.severity.lower(), 5.0)

        # Normalize to 0-1
        return min(1.0, cvss / 10.0)

    def _score_epss(self, enrichment_data: Dict[str, Any]) -> float:
        """
        Score based on EPSS probability (0-1 scale).

        EPSS is already 0-1 (probability of exploitation)
        """
        epss = enrichment_data.get("epss_score")

        if epss is None:
            # No EPSS data, use medium score
            return 0.3

        return min(1.0, epss)

    def _score_exploit_availability(self, enrichment_data: Dict[str, Any]) -> float:
        """
        Score based on exploit availability (0-1 scale).

        Scoring:
        - No exploit: 0.0
        - Proof of concept: 0.5
        - Functional exploit: 0.8
        - High/weaponized: 1.0
        """
        if not enrichment_data.get("exploit_available"):
            return 0.0

        maturity = enrichment_data.get("exploit_maturity", "none")

        maturity_scores = {
            "none": 0.0,
            "proof_of_concept": 0.5,
            "functional": 0.8,
            "high": 1.0,
        }

        return maturity_scores.get(maturity, 0.5)

    def _score_asset_criticality(self, criticality: int) -> float:
        """
        Score based on asset criticality (0-1 scale).

        Criticality is 1-5, normalize to 0-1
        """
        # Validate range
        criticality = max(1, min(5, criticality))

        # Normalize to 0-1
        return (criticality - 1) / 4.0

    def _score_vulnerability_age(self, vulnerability: NormalizedVulnerability) -> float:
        """
        Score based on vulnerability age (0-1 scale).

        Older vulnerabilities that remain unpatched are higher priority.

        Scoring:
        - < 7 days: 0.3
        - 7-30 days: 0.5
        - 30-90 days: 0.7
        - 90-180 days: 0.9
        - > 180 days: 1.0
        """
        age = datetime.utcnow() - vulnerability.discovered_at
        days = age.days

        if days < 7:
            return 0.3
        elif days < 30:
            return 0.5
        elif days < 90:
            return 0.7
        elif days < 180:
            return 0.9
        else:
            return 1.0

    def _score_patch_availability(self, vulnerability: NormalizedVulnerability) -> float:
        """
        Score based on patch availability (0-1 scale).

        If a patch is available, remediation is more urgent.
        """
        if vulnerability.fixed_version:
            return 1.0  # Patch available
        else:
            return 0.3  # No patch yet

    def get_priority_explanation(
        self,
        vulnerability: NormalizedVulnerability,
        enrichment_data: Dict[str, Any] = None,
        asset_criticality: int = 3,
    ) -> Dict[str, Any]:
        """
        Get detailed explanation of priority score.

        Args:
            vulnerability: Normalized vulnerability
            enrichment_data: Enrichment data
            asset_criticality: Asset criticality level

        Returns:
            Dict with score breakdown
        """
        enrichment_data = enrichment_data or {}

        cvss_score = self._score_cvss(vulnerability, enrichment_data)
        epss_score = self._score_epss(enrichment_data)
        exploit_score = self._score_exploit_availability(enrichment_data)
        criticality_score = self._score_asset_criticality(asset_criticality)
        age_score = self._score_vulnerability_age(vulnerability)
        patch_score = self._score_patch_availability(vulnerability)

        total_score = self.calculate_priority(
            vulnerability, enrichment_data, asset_criticality
        )

        return {
            "total_score": total_score,
            "components": {
                "cvss": {
                    "score": cvss_score,
                    "weight": self.weights["cvss"],
                    "contribution": cvss_score * self.weights["cvss"] * 100,
                },
                "epss": {
                    "score": epss_score,
                    "weight": self.weights["epss"],
                    "contribution": epss_score * self.weights["epss"] * 100,
                },
                "exploit": {
                    "score": exploit_score,
                    "weight": self.weights["exploit"],
                    "contribution": exploit_score * self.weights["exploit"] * 100,
                },
                "criticality": {
                    "score": criticality_score,
                    "weight": self.weights["criticality"],
                    "contribution": criticality_score * self.weights["criticality"] * 100,
                },
                "age": {
                    "score": age_score,
                    "weight": self.weights["age"],
                    "contribution": age_score * self.weights["age"] * 100,
                },
                "patch_available": {
                    "score": patch_score,
                    "weight": self.weights["patch_available"],
                    "contribution": patch_score * self.weights["patch_available"] * 100,
                },
            },
            "bonuses": {
                "cisa_kev": enrichment_data.get("in_cisa_kev", False),
            },
        }


# Convenience function
def calculate_priority_score(
    vulnerability: NormalizedVulnerability,
    enrichment_data: Dict[str, Any] = None,
    asset_criticality: int = 3,
) -> float:
    """
    Convenience function to calculate priority score.

    Args:
        vulnerability: Normalized vulnerability
        enrichment_data: Enrichment data
        asset_criticality: Asset criticality level (1-5)

    Returns:
        Priority score (0-100)
    """
    scorer = PriorityScorer()
    return scorer.calculate_priority(vulnerability, enrichment_data, asset_criticality)
