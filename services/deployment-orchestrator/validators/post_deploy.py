"""
Post-Deployment Validator

Validates deployment success through health checks and metrics.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from shared.models import Asset, Patch
from services.deployment_orchestrator.ansible.executor import AnsibleExecutor
from services.deployment_orchestrator.ansible.playbook_generator import PlaybookGenerator

logger = logging.getLogger(__name__)


class PostDeployValidator:
    """
    Validates deployment success after patch execution.

    Performs:
    - System health checks
    - Service availability validation
    - Performance metrics comparison
    - Error log analysis
    """

    def __init__(self, db: Session):
        """
        Initialize post-deployment validator.

        Args:
            db: Database session
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.executor = AnsibleExecutor()

    def validate(
        self,
        patch: Patch,
        assets: List[Asset]
    ) -> Dict[str, Any]:
        """
        Run post-deployment validation.

        Args:
            patch: Deployed patch
            assets: Target assets

        Returns:
            Validation results dict with:
            - success: Overall validation status
            - asset_results: Per-asset validation results
            - issues: List of issues found
        """
        self.logger.info(
            f"Running post-deployment validation for patch {patch.id} "
            f"on {len(assets)} assets"
        )

        results = {
            "success": True,
            "asset_results": {},
            "issues": []
        }

        for asset in assets:
            asset_result = self._validate_asset(asset, patch)
            results["asset_results"][asset.id] = asset_result

            if not asset_result["healthy"]:
                results["success"] = False
                results["issues"].extend(
                    [f"Asset {asset.id}: {issue}" for issue in asset_result["issues"]]
                )

        # Calculate overall health
        total = len(assets)
        healthy = sum(
            1 for r in results["asset_results"].values()
            if r["healthy"]
        )
        results["health_percentage"] = (healthy / total * 100) if total > 0 else 0

        self.logger.info(
            f"Post-deployment validation complete: "
            f"{healthy}/{total} assets healthy ({results['health_percentage']:.1f}%)"
        )

        return results

    def _validate_asset(
        self,
        asset: Asset,
        patch: Patch
    ) -> Dict[str, Any]:
        """
        Validate single asset after deployment.

        Args:
            asset: Asset to validate
            patch: Deployed patch

        Returns:
            Asset validation result dict
        """
        result = {
            "healthy": True,
            "issues": [],
            "health_checks": {}
        }

        try:
            # Run health check playbook
            generator = PlaybookGenerator()
            playbook_content = generator.generate_health_check_playbook(asset)

            # For MVP: Execute health check via Ansible
            # In production: Would use ansible-runner with proper result parsing
            import tempfile
            import os
            import subprocess

            with tempfile.TemporaryDirectory() as tmpdir:
                playbook_path = os.path.join(tmpdir, "health_check.yml")
                with open(playbook_path, 'w') as f:
                    f.write(playbook_content)

                cmd = [
                    "ansible-playbook",
                    playbook_path,
                    "-i", f"{asset.hostname},",
                ]

                health_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if health_result.returncode != 0:
                    result["healthy"] = False
                    result["issues"].append(
                        f"Health check playbook failed: {health_result.stderr}"
                    )
                else:
                    # Parse output for specific check results
                    result["health_checks"] = self._parse_health_output(
                        health_result.stdout
                    )

                    # Check for critical failures
                    if "FAILED" in health_result.stdout:
                        result["healthy"] = False
                        result["issues"].append("One or more health checks failed")

        except subprocess.TimeoutExpired:
            result["healthy"] = False
            result["issues"].append("Health check timed out")
            self.logger.error(f"Health check timeout for asset {asset.id}")

        except Exception as e:
            result["healthy"] = False
            result["issues"].append(f"Health check error: {str(e)}")
            self.logger.error(
                f"Health check error for asset {asset.id}: {e}",
                exc_info=True
            )

        return result

    def _parse_health_output(self, output: str) -> Dict[str, Any]:
        """
        Parse Ansible health check output.

        Args:
            output: Ansible playbook stdout

        Returns:
            Parsed health check results
        """
        checks = {
            "uptime": "unknown",
            "services": "unknown",
            "disk_space": "unknown",
            "memory_usage": "unknown",
            "network": "unknown"
        }

        # Basic parsing for MVP
        # In production: Would use structured output (JSON callback plugin)

        if "ok=" in output:
            # Extract task counts
            import re
            ok_match = re.search(r"ok=(\d+)", output)
            failed_match = re.search(r"failed=(\d+)", output)

            if ok_match:
                checks["tasks_passed"] = int(ok_match.group(1))
            if failed_match:
                checks["tasks_failed"] = int(failed_match.group(1))

        return checks
