"""
CSV/JSON Scanner

Generic scanner for importing vulnerabilities from CSV or JSON files.
"""

import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from services.aggregator.scanners.base import (
    BaseScanner,
    ScanResult,
    RawVulnerability,
    ScannerError,
)

logger = logging.getLogger(__name__)


class CSVScanner(BaseScanner):
    """
    Generic CSV/JSON file import scanner.

    Configuration required:
    - file_path: Path to CSV or JSON file
    - file_type: 'csv' or 'json'
    - mapping: Field mapping configuration (optional)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.file_path = config.get("file_path")
        self.file_type = config.get("file_type", "csv").lower()
        self.mapping = config.get("mapping", {})

    async def authenticate(self) -> bool:
        """
        Validate file exists and is readable.

        Returns:
            bool: True if file is accessible
        """
        try:
            file = Path(self.file_path)
            if not file.exists():
                raise ScannerError(f"File not found: {self.file_path}")

            if not file.is_file():
                raise ScannerError(f"Not a file: {self.file_path}")

            self.logger.info(f"CSV/JSON file validated: {self.file_path}")
            return True

        except Exception as e:
            raise ScannerError(f"File validation error: {e}")

    async def scan(self, target: Optional[str] = None) -> ScanResult:
        """
        Import vulnerabilities from CSV or JSON file.

        Args:
            target: Not used for file imports

        Returns:
            ScanResult with imported vulnerabilities
        """
        scan_id = f"csv-import-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.utcnow()
        vulnerabilities: List[RawVulnerability] = []
        errors: List[str] = []

        try:
            if self.file_type == "csv":
                vulnerabilities = await self._import_csv()
            elif self.file_type == "json":
                vulnerabilities = await self._import_json()
            else:
                errors.append(f"Unsupported file type: {self.file_type}")

            self.logger.info(f"CSV/JSON import found {len(vulnerabilities)} vulnerabilities")

        except Exception as e:
            errors.append(str(e))
            self.logger.error(f"CSV/JSON import error: {e}")

        return self._create_scan_result(scan_id, started_at, vulnerabilities, errors)

    async def _import_csv(self) -> List[RawVulnerability]:
        """Import vulnerabilities from CSV file"""
        vulnerabilities: List[RawVulnerability] = []

        with open(self.file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                # Apply field mapping if configured
                mapped_row = self._apply_mapping(row)

                # Generate unique ID
                vuln_id = mapped_row.get("cve_id") or mapped_row.get("id") or f"CSV-{len(vulnerabilities)}"

                raw_vuln = RawVulnerability(
                    scanner_id="csv",
                    scanner_vuln_id=vuln_id,
                    raw_data=mapped_row,
                    discovered_at=datetime.utcnow(),
                    scanner_type="csv",
                )
                vulnerabilities.append(raw_vuln)

        return vulnerabilities

    async def _import_json(self) -> List[RawVulnerability]:
        """Import vulnerabilities from JSON file"""
        vulnerabilities: List[RawVulnerability] = []

        with open(self.file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

            # Support both array and object with vulnerabilities array
            items = data if isinstance(data, list) else data.get("vulnerabilities", [])

            for item in items:
                # Apply field mapping if configured
                mapped_item = self._apply_mapping(item)

                # Generate unique ID
                vuln_id = mapped_item.get("cve_id") or mapped_item.get("id") or f"JSON-{len(vulnerabilities)}"

                raw_vuln = RawVulnerability(
                    scanner_id="json",
                    scanner_vuln_id=vuln_id,
                    raw_data=mapped_item,
                    discovered_at=datetime.utcnow(),
                    scanner_type="json",
                )
                vulnerabilities.append(raw_vuln)

        return vulnerabilities

    def _apply_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply field mapping to normalize data.

        Example mapping:
        {
            "cve": "cve_id",
            "score": "cvss_score",
            "host": "hostname"
        }
        """
        if not self.mapping:
            return data

        mapped = {}
        for source_field, target_field in self.mapping.items():
            if source_field in data:
                mapped[target_field] = data[source_field]

        # Include unmapped fields
        for key, value in data.items():
            if key not in mapped:
                mapped[key] = value

        return mapped

    async def get_vulnerability_details(self, vuln_id: str) -> Dict[str, Any]:
        """
        Get detailed information (not supported for file imports).

        Args:
            vuln_id: Vulnerability ID

        Returns:
            Empty dict (file imports don't support detail fetching)
        """
        return {}

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass
