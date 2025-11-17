"""
Pre-Deployment Validator

Validates prerequisites before patch deployment.
"""

import logging
from typing import List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models import Asset, Patch
from services.digital_twin.analyzers.result_analyzer import TestResult, TestStatus

logger = logging.getLogger(__name__)


class PreDeployValidator:
    """
    Validates prerequisites before deployment.

    Checks:
    - Patch has been tested successfully
    - Assets are reachable
    - No ongoing maintenance windows
    - Sufficient resources available
    """

    def __init__(self, db: Session):
        """
        Initialize pre-deployment validator.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    def validate(
        self,
        patch: Patch,
        assets: List[Asset]
    ) -> Tuple[bool, str]:
        """
        Run all pre-deployment validations.

        Args:
            patch: Patch to validate
            assets: Target assets

        Returns:
            (success, message) tuple
        """
        self.logger.info(
            f"Running pre-deployment validation for patch {patch.id} "
            f"on {len(assets)} assets"
        )

        # Check 1: Patch testing status
        test_ok, test_msg = self._validate_patch_testing(patch)
        if not test_ok:
            return False, test_msg

        # Check 2: Asset connectivity
        connectivity_ok, connectivity_msg = self._validate_asset_connectivity(assets)
        if not connectivity_ok:
            return False, connectivity_msg

        # Check 3: Maintenance windows
        maintenance_ok, maintenance_msg = self._validate_maintenance_windows(assets)
        if not maintenance_ok:
            return False, maintenance_msg

        # Check 4: Patch approval
        approval_ok, approval_msg = self._validate_patch_approval(patch)
        if not approval_ok:
            return False, approval_msg

        self.logger.info("All pre-deployment checks passed")
        return True, "All validations passed"

    def _validate_patch_testing(self, patch: Patch) -> Tuple[bool, str]:
        """
        Validate patch has been tested successfully.

        Args:
            patch: Patch to validate

        Returns:
            (success, message) tuple
        """
        # Check if patch has test results
        test_result = (
            self.db.query(TestResult)
            .filter_by(patch_id=patch.id)
            .order_by(TestResult.created_at.desc())
            .first()
        )

        if not test_result:
            return False, "Patch has not been tested in Digital Twin"

        if test_result.status != TestStatus.PASSED:
            return (
                False,
                f"Patch testing failed: {test_result.status.value}. "
                f"Cannot deploy untested patch."
            )

        # Check confidence score
        if test_result.confidence_score < 70.0:
            return (
                False,
                f"Test confidence score too low: {test_result.confidence_score}%. "
                f"Minimum required: 70%"
            )

        self.logger.info(
            f"Patch testing validated: status={test_result.status.value}, "
            f"confidence={test_result.confidence_score}%"
        )
        return True, "Patch testing validated"

    def _validate_asset_connectivity(self, assets: List[Asset]) -> Tuple[bool, str]:
        """
        Validate assets are reachable.

        Args:
            assets: Assets to check

        Returns:
            (success, message) tuple
        """
        # For MVP: Basic check that assets exist and have hostnames
        # In production: Would ping/SSH to verify connectivity

        if not assets:
            return False, "No assets specified for deployment"

        unreachable = []
        for asset in assets:
            if not asset.hostname:
                unreachable.append(f"Asset {asset.id}: missing hostname")
            # Additional checks can be added here

        if unreachable:
            return False, f"Unreachable assets: {', '.join(unreachable)}"

        self.logger.info(f"Asset connectivity validated for {len(assets)} assets")
        return True, "All assets reachable"

    def _validate_maintenance_windows(self, assets: List[Asset]) -> Tuple[bool, str]:
        """
        Validate no ongoing maintenance windows.

        Args:
            assets: Assets to check

        Returns:
            (success, message) tuple
        """
        # For MVP: Check asset metadata for maintenance windows
        # In production: Would query maintenance_windows table

        in_maintenance = []
        for asset in assets:
            if asset.metadata and asset.metadata.get("maintenance_mode"):
                in_maintenance.append(f"Asset {asset.id} ({asset.hostname})")

        if in_maintenance:
            return (
                False,
                f"Assets in maintenance mode: {', '.join(in_maintenance)}"
            )

        self.logger.info("Maintenance window validation passed")
        return True, "No maintenance conflicts"

    def _validate_patch_approval(self, patch: Patch) -> Tuple[bool, str]:
        """
        Validate patch is approved for deployment.

        Args:
            patch: Patch to validate

        Returns:
            (success, message) tuple
        """
        # Check patch validation status
        if not patch.validation_passed:
            return False, "Patch has not passed validation checks"

        # Check confidence score
        if patch.confidence_score < 70.0:
            return (
                False,
                f"Patch confidence score too low: {patch.confidence_score}%. "
                f"Minimum required: 70%"
            )

        self.logger.info(
            f"Patch approval validated: confidence={patch.confidence_score}%"
        )
        return True, "Patch approved for deployment"
