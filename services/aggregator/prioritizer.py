"""
ML-based vulnerability prioritization
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import structlog

from shared.models.models import Vulnerability

logger = structlog.get_logger()


class VulnerabilityPrioritizer:
    """
    ML-based vulnerability prioritization

    For MVP: Uses a weighted scoring system
    Future: Train XGBoost model on historical remediation data
    """

    def __init__(self):
        self.scaler = MinMaxScaler()
        self.weights = {
            "cvss_score": 0.30,  # CVSS base score
            "epss_score": 0.25,  # Exploit prediction
            "severity": 0.20,    # Severity level
            "asset_criticality": 0.15,  # Asset importance
            "exploit_available": 0.10,  # Known exploits
        }

    def calculate_priority_score(
        self,
        vulnerability: Vulnerability,
        asset_criticality: float = 5.0,
    ) -> float:
        """
        Calculate priority score for a vulnerability

        Args:
            vulnerability: Vulnerability model instance
            asset_criticality: Criticality of affected assets (1-10 scale)

        Returns:
            Priority score (0-100)
        """
        features = self._extract_features(vulnerability, asset_criticality)
        score = self._calculate_weighted_score(features)

        logger.debug(
            "priority_calculated",
            cve_id=vulnerability.cve_id,
            score=score,
            features=features,
        )

        return round(score, 2)

    def _extract_features(
        self,
        vulnerability: Vulnerability,
        asset_criticality: float,
    ) -> Dict[str, float]:
        """
        Extract features for prioritization

        Args:
            vulnerability: Vulnerability instance
            asset_criticality: Asset criticality score

        Returns:
            Dictionary of normalized features
        """
        features = {}

        # CVSS Score (0-10 scale)
        cvss = vulnerability.cvss_score or 0.0
        features["cvss_score"] = min(cvss / 10.0, 1.0)

        # EPSS Score (0-1 scale, already normalized)
        features["epss_score"] = vulnerability.epss_score or 0.0

        # Severity (categorical to numeric)
        severity_map = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
            "info": 0.0,
        }
        features["severity"] = severity_map.get(
            vulnerability.severity.value.lower(),
            0.5,
        )

        # Asset criticality (1-10 scale, normalize to 0-1)
        features["asset_criticality"] = min(asset_criticality / 10.0, 1.0)

        # Exploit available (binary)
        features["exploit_available"] = 1.0 if vulnerability.exploit_available else 0.0

        return features

    def _calculate_weighted_score(self, features: Dict[str, float]) -> float:
        """
        Calculate weighted score from features

        Args:
            features: Dictionary of feature values

        Returns:
            Priority score (0-100)
        """
        score = 0.0

        for feature_name, weight in self.weights.items():
            feature_value = features.get(feature_name, 0.0)
            score += feature_value * weight

        # Convert to 0-100 scale
        return score * 100

    def prioritize_batch(
        self,
        vulnerabilities: List[Vulnerability],
        asset_criticalities: Dict[int, float] | None = None,
    ) -> List[tuple[Vulnerability, float]]:
        """
        Prioritize a batch of vulnerabilities

        Args:
            vulnerabilities: List of vulnerabilities
            asset_criticalities: Optional dict mapping asset IDs to criticality

        Returns:
            List of (vulnerability, priority_score) tuples, sorted by priority
        """
        if asset_criticalities is None:
            asset_criticalities = {}

        results = []

        for vuln in vulnerabilities:
            # Get asset criticality (default to medium if not provided)
            criticality = asset_criticalities.get(vuln.id, 5.0)

            priority = self.calculate_priority_score(vuln, criticality)
            results.append((vuln, priority))

        # Sort by priority (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            "batch_prioritized",
            total=len(vulnerabilities),
            highest_priority=results[0][1] if results else 0,
            lowest_priority=results[-1][1] if results else 0,
        )

        return results

    def get_risk_category(self, priority_score: float) -> str:
        """
        Categorize risk based on priority score

        Args:
            priority_score: Priority score (0-100)

        Returns:
            Risk category string
        """
        if priority_score >= 80:
            return "critical"
        elif priority_score >= 60:
            return "high"
        elif priority_score >= 40:
            return "medium"
        elif priority_score >= 20:
            return "low"
        else:
            return "informational"

    def explain_priority(
        self,
        vulnerability: Vulnerability,
        asset_criticality: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Explain why a vulnerability received its priority score

        Args:
            vulnerability: Vulnerability instance
            asset_criticality: Asset criticality

        Returns:
            Dictionary with explanation
        """
        features = self._extract_features(vulnerability, asset_criticality)
        total_score = self._calculate_weighted_score(features)

        contributions = {}
        for feature_name, weight in self.weights.items():
            feature_value = features.get(feature_name, 0.0)
            contribution = feature_value * weight * 100
            contributions[feature_name] = {
                "value": feature_value,
                "weight": weight,
                "contribution": round(contribution, 2),
            }

        return {
            "total_score": round(total_score, 2),
            "risk_category": self.get_risk_category(total_score),
            "feature_contributions": contributions,
            "top_factors": self._get_top_factors(contributions),
        }

    def _get_top_factors(
        self,
        contributions: Dict[str, Dict[str, Any]],
    ) -> List[str]:
        """Get top contributing factors"""
        sorted_factors = sorted(
            contributions.items(),
            key=lambda x: x[1]["contribution"],
            reverse=True,
        )

        return [factor[0] for factor in sorted_factors[:3]]
