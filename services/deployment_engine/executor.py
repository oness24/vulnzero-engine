"""
Deployment execution engine
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import structlog

from services.deployment_engine.connection_manager import get_connection_manager
from services.deployment_engine.ansible_runner import AnsibleRunner
from services.deployment_engine.strategies import get_deployment_strategy

logger = structlog.get_logger()


class DeploymentExecutor:
    """
    Main executor for patch deployments
    """

    def __init__(self, use_ansible: bool = True):
        """
        Initialize deployment executor

        Args:
            use_ansible: Use Ansible for deployments (vs direct SSH)
        """
        self.use_ansible = use_ansible

    async def deploy_patch(
        self,
        patch: Dict[str, Any],
        assets: List[Dict[str, Any]],
        strategy: str = "rolling",
        strategy_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Deploy patch to assets

        Args:
            patch: Patch information (scripts, etc.)
            assets: List of target assets
            strategy: Deployment strategy
            strategy_options: Strategy-specific options

        Returns:
            Deployment results
        """
        logger.info(
            "starting_deployment",
            patch_id=patch.get("id"),
            asset_count=len(assets),
            strategy=strategy,
        )

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "patch_id": patch.get("id"),
            "strategy": strategy,
            "total_assets": len(assets),
            "successful_assets": 0,
            "failed_assets": 0,
            "deployment_results": [],
        }

        # Get deployment strategy
        strategy_options = strategy_options or {}
        deployment_strategy = get_deployment_strategy(strategy, **strategy_options)

        # Define deployment function
        async def deploy_to_asset(asset: Dict[str, Any]) -> Dict[str, Any]:
            if self.use_ansible:
                return await self._deploy_with_ansible(asset, patch)
            else:
                return await self._deploy_with_ssh(asset, patch)

        # Execute deployment with strategy
        deployment_results = await deployment_strategy.deploy(
            assets,
            deploy_to_asset,
        )

        result.update(deployment_results)
        result["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "deployment_completed",
            patch_id=patch.get("id"),
            successful=result.get("successful", 0),
            failed=result.get("failed", 0),
        )

        return result

    async def _deploy_with_ansible(
        self,
        asset: Dict[str, Any],
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deploy using Ansible

        Args:
            asset: Target asset
            patch: Patch information

        Returns:
            Deployment result
        """
        logger.info("deploying_with_ansible", asset=asset.get("name"))

        try:
            runner = AnsibleRunner()

            # Run deployment
            result = runner.deploy_to_asset(
                asset,
                patch["patch_script"],
                patch["rollback_script"],
                patch.get("validation_script"),
            )

            # Cleanup
            runner.cleanup()

            return result

        except Exception as e:
            logger.error(
                "ansible_deployment_failed",
                asset=asset.get("name"),
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def _deploy_with_ssh(
        self,
        asset: Dict[str, Any],
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deploy using direct SSH

        Args:
            asset: Target asset
            patch: Patch information

        Returns:
            Deployment result
        """
        logger.info("deploying_with_ssh", asset=asset.get("name"))

        conn_manager = get_connection_manager("ssh")

        try:
            # Connect
            if not conn_manager.connect(asset):
                return {
                    "success": False,
                    "error": "Failed to connect to asset",
                }

            # Copy patch script
            patch_path = "/tmp/vulnzero_patch.sh"
            if not conn_manager.copy_content(patch["patch_script"], patch_path, 0o755):
                return {
                    "success": False,
                    "error": "Failed to copy patch script",
                }

            # Copy rollback script
            rollback_path = "/tmp/vulnzero_rollback.sh"
            conn_manager.copy_content(patch["rollback_script"], rollback_path, 0o755)

            # Execute patch
            patch_result = conn_manager.execute_command(
                f"bash {patch_path}",
                sudo=True,
            )

            # Execute validation if provided and patch succeeded
            validation_result = None
            if patch_result["success"] and patch.get("validation_script"):
                validation_path = "/tmp/vulnzero_validate.sh"
                conn_manager.copy_content(
                    patch["validation_script"],
                    validation_path,
                    0o755,
                )
                validation_result = conn_manager.execute_command(
                    f"bash {validation_path}",
                    sudo=True,
                )

            # Cleanup
            conn_manager.execute_command(
                f"rm -f {patch_path} {rollback_path} /tmp/vulnzero_validate.sh",
                sudo=True,
            )

            conn_manager.disconnect()

            # Overall success
            success = patch_result["success"] and (
                not validation_result or validation_result["success"]
            )

            return {
                "success": success,
                "patch_result": patch_result,
                "validation_result": validation_result,
            }

        except Exception as e:
            logger.error(
                "ssh_deployment_failed",
                asset=asset.get("name"),
                error=str(e),
            )
            conn_manager.disconnect()
            return {
                "success": False,
                "error": str(e),
            }

    async def rollback_deployment(
        self,
        deployment_id: int,
        assets: List[Dict[str, Any]],
        rollback_script: str,
    ) -> Dict[str, Any]:
        """
        Rollback a deployment

        Args:
            deployment_id: Deployment ID
            assets: Assets to rollback
            rollback_script: Rollback script

        Returns:
            Rollback results
        """
        logger.info(
            "starting_rollback",
            deployment_id=deployment_id,
            asset_count=len(assets),
        )

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "deployment_id": deployment_id,
            "total_assets": len(assets),
            "successful_rollbacks": 0,
            "failed_rollbacks": 0,
            "rollback_results": [],
        }

        # Rollback each asset
        for asset in assets:
            rollback_result = await self._execute_rollback(asset, rollback_script)

            result["rollback_results"].append({
                "asset": asset.get("name"),
                "success": rollback_result["success"],
                "result": rollback_result,
            })

            if rollback_result["success"]:
                result["successful_rollbacks"] += 1
            else:
                result["failed_rollbacks"] += 1

        result["completed_at"] = datetime.utcnow().isoformat()
        result["success"] = result["failed_rollbacks"] == 0

        logger.info(
            "rollback_completed",
            deployment_id=deployment_id,
            successful=result["successful_rollbacks"],
            failed=result["failed_rollbacks"],
        )

        return result

    async def _execute_rollback(
        self,
        asset: Dict[str, Any],
        rollback_script: str,
    ) -> Dict[str, Any]:
        """
        Execute rollback on single asset

        Args:
            asset: Target asset
            rollback_script: Rollback script

        Returns:
            Rollback result
        """
        logger.info("executing_rollback", asset=asset.get("name"))

        conn_manager = get_connection_manager("ssh")

        try:
            # Connect
            if not conn_manager.connect(asset):
                return {
                    "success": False,
                    "error": "Failed to connect",
                }

            # Copy and execute rollback script
            rollback_path = "/tmp/vulnzero_rollback.sh"
            conn_manager.copy_content(rollback_script, rollback_path, 0o755)

            rollback_result = conn_manager.execute_command(
                f"bash {rollback_path}",
                sudo=True,
            )

            # Cleanup
            conn_manager.execute_command(f"rm -f {rollback_path}", sudo=True)
            conn_manager.disconnect()

            return {
                "success": rollback_result["success"],
                "output": rollback_result,
            }

        except Exception as e:
            logger.error("rollback_execution_failed", error=str(e))
            conn_manager.disconnect()
            return {
                "success": False,
                "error": str(e),
            }

    async def verify_deployment(
        self,
        assets: List[Dict[str, Any]],
        verification_script: str,
    ) -> Dict[str, Any]:
        """
        Verify deployment on assets

        Args:
            assets: Assets to verify
            verification_script: Verification script

        Returns:
            Verification results
        """
        logger.info("verifying_deployment", asset_count=len(assets))

        results = {
            "total_assets": len(assets),
            "verified": 0,
            "failed": 0,
            "asset_results": [],
        }

        # Verify each asset
        tasks = []
        for asset in assets:
            task = self._verify_single_asset(asset, verification_script)
            tasks.append(task)

        # Run verifications concurrently
        verification_results = await asyncio.gather(*tasks, return_exceptions=True)

        for asset, verification in zip(assets, verification_results):
            if isinstance(verification, Exception):
                results["asset_results"].append({
                    "asset": asset.get("name"),
                    "verified": False,
                    "error": str(verification),
                })
                results["failed"] += 1
            else:
                results["asset_results"].append({
                    "asset": asset.get("name"),
                    "verified": verification["success"],
                    "result": verification,
                })
                if verification["success"]:
                    results["verified"] += 1
                else:
                    results["failed"] += 1

        results["all_verified"] = results["failed"] == 0

        logger.info(
            "deployment_verification_complete",
            verified=results["verified"],
            failed=results["failed"],
        )

        return results

    async def _verify_single_asset(
        self,
        asset: Dict[str, Any],
        verification_script: str,
    ) -> Dict[str, Any]:
        """Verify deployment on single asset"""
        conn_manager = get_connection_manager("ssh")

        try:
            if not conn_manager.connect(asset):
                return {"success": False, "error": "Connection failed"}

            verify_path = "/tmp/vulnzero_verify.sh"
            conn_manager.copy_content(verification_script, verify_path, 0o755)

            result = conn_manager.execute_command(f"bash {verify_path}", sudo=True)

            conn_manager.execute_command(f"rm -f {verify_path}", sudo=True)
            conn_manager.disconnect()

            return {
                "success": result["success"],
                "output": result,
            }

        except Exception as e:
            conn_manager.disconnect()
            return {"success": False, "error": str(e)}
