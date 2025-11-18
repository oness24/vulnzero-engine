"""
Base scanner adapter interface for vulnerability scanners
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class RawVulnerability:
    """Raw vulnerability data from scanner"""
    scanner_id: str
    scanner_name: str
    cve_id: Optional[str]
    title: str
    description: Optional[str]
    severity: str
    cvss_score: Optional[float]
    cvss_vector: Optional[str]
    affected_package: Optional[str]
    vulnerable_version: Optional[str]
    fixed_version: Optional[str]
    affected_assets: List[str]
    discovered_at: datetime
    raw_data: Dict[str, Any]


class ScannerAdapter(ABC):
    """Abstract base class for vulnerability scanner adapters"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scanner adapter with configuration

        Args:
            config: Scanner-specific configuration (API URL, credentials, etc.)
        """
        self.config = config
        self.scanner_name = self.__class__.__name__.replace("Adapter", "")

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the scanner API

        Returns:
            True if authentication successful

        Raises:
            ScannerAuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def fetch_vulnerabilities(
        self,
        since: Optional[datetime] = None,
        severity_filter: Optional[List[str]] = None,
    ) -> List[RawVulnerability]:
        """
        Fetch vulnerabilities from the scanner

        Args:
            since: Only fetch vulnerabilities discovered since this time
            severity_filter: Filter by severity levels (e.g., ['critical', 'high'])

        Returns:
            List of raw vulnerabilities

        Raises:
            ScannerFetchError: If fetching fails
        """
        pass

    @abstractmethod
    async def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific asset

        Args:
            asset_id: Asset identifier

        Returns:
            Asset details dictionary

        Raises:
            ScannerAssetNotFoundError: If asset not found
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if the scanner API is accessible

        Returns:
            True if scanner is healthy
        """
        try:
            return await self.authenticate()
        except Exception:
            return False

    def normalize_severity(self, scanner_severity: str) -> str:
        """
        Normalize scanner-specific severity to standard levels

        Args:
            scanner_severity: Severity from scanner

        Returns:
            Normalized severity (critical, high, medium, low, info)
        """
        severity_map = {
            # Common mappings
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "info",
            "informational": "info",
            # CVSS-based mappings
            "9.0-10.0": "critical",
            "7.0-8.9": "high",
            "4.0-6.9": "medium",
            "0.1-3.9": "low",
        }

        severity_lower = scanner_severity.lower().strip()
        return severity_map.get(severity_lower, "medium")


class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass


class ScannerAuthenticationError(ScannerError):
    """Scanner authentication failed"""
    pass


class ScannerFetchError(ScannerError):
    """Failed to fetch data from scanner"""
    pass


class ScannerAssetNotFoundError(ScannerError):
    """Asset not found in scanner"""
    pass
