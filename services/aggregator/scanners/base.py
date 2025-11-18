"""
Base Scanner Interface

Abstract base class for vulnerability scanner integrations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class RawVulnerability(BaseModel):
    """Raw vulnerability data from scanner (before normalization)"""

    scanner_id: str
    scanner_vuln_id: str
    raw_data: Dict[str, Any]
    discovered_at: datetime
    scanner_type: str  # wazuh, qualys, tenable, csv


class ScanResult(BaseModel):
    """Result of a scanner scan operation"""

    scanner_type: str
    scan_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    vulnerabilities_found: int = 0
    vulnerabilities: List[RawVulnerability] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseScanner(ABC):
    """
    Abstract base class for vulnerability scanners.

    All scanner integrations must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scanner with configuration.

        Args:
            config: Scanner-specific configuration (API keys, endpoints, etc.)
        """
        self.config = config
        self.scanner_type = self.__class__.__name__.lower().replace('scanner', '')
        self.logger = logging.getLogger(f"scanner.{self.scanner_type}")

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the scanner API.

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def scan(self, target: Optional[str] = None) -> ScanResult:
        """
        Perform vulnerability scan or fetch latest results.

        Args:
            target: Optional specific target to scan (asset ID, IP range, etc.)

        Returns:
            ScanResult: Scan results with vulnerabilities

        Raises:
            ScannerError: If scan fails
        """
        pass

    @abstractmethod
    async def get_vulnerability_details(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific vulnerability.

        Args:
            vuln_id: Scanner-specific vulnerability ID

        Returns:
            Dict containing detailed vulnerability information
        """
        pass

    async def test_connection(self) -> bool:
        """
        Test connectivity to the scanner.

        Returns:
            bool: True if connection successful
        """
        try:
            return await self.authenticate()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def _create_scan_result(
        self,
        scan_id: str,
        started_at: datetime,
        vulnerabilities: List[RawVulnerability] = None,
        errors: List[str] = None,
    ) -> ScanResult:
        """Helper to create ScanResult object"""
        return ScanResult(
            scanner_type=self.scanner_type,
            scan_id=scan_id,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            vulnerabilities_found=len(vulnerabilities) if vulnerabilities else 0,
            vulnerabilities=vulnerabilities or [],
            errors=errors or [],
            success=len(errors) == 0 if errors is not None else True,
        )


class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass


class AuthenticationError(ScannerError):
    """Authentication failed"""
    pass


class ScanTimeoutError(ScannerError):
    """Scan operation timed out"""
    pass


class RateLimitError(ScannerError):
    """API rate limit exceeded"""
    pass
