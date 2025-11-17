"""
Rolling Deployment Strategy

Gradual deployment in batches with monitoring between batches.
Zero downtime, automatic rollback on failure.
"""

import logging
import time
from typing import List
from datetime import datetime
from math import ceil

from services.deployment_orchestrator.strategies.base import (
    DeploymentStrategy, DeploymentResult, DeploymentStatus
)
from shared.models import Asset

logger = logging.getLogger(__name__)


class RollingDeployment(DeploymentStrategy):
    """
    Rolling deployment in configurable batches.
    
    Deploys gradually with monitoring between batches.
    Stops automatically on failure. Ideal for production.
    """

    def __init__(
        self,
        patch,
        batch_size: float = 0.2,
        wait_seconds: int = 60,
        max_failures: int = 2,
        continue_on_error: bool = False
    ):
        """
        Initialize rolling deployment strategy.
        
        Args:
            patch: Patch to deploy
            batch_size: Fraction of assets per batch (0.2 = 20%)
            wait_seconds: Wait time between batches
            max_failures: Stop after N failures
            continue_on_error: Continue despite failures
        """
        super().__init__(patch)
        self.batch_size = batch_size
        self.wait_seconds = wait_seconds
        self.max_failures = max_failures
        self.continue_on_error = continue_on_error
        
        self.logger.info(
            f"Initialized rolling deployment: "
            f"batch_size={batch_size}, wait={wait_seconds}s, "
            f"max_failures={max_failures}"
        )

    def validate_prerequisites(self, assets: List[Asset]) -> tuple[bool, str]:
        """Validate prerequisites"""
        if not assets:
            return False, "No assets provided"
        
        if self.patch.test_status != "passed":
            return False, f"Patch test status is {self.patch.test_status}"
        
        if self.batch_size <= 0 or self.batch_size > 1:
            return False, f"Invalid batch_size: {self.batch_size} (must be 0-1)"
        
        return True, ""

    def execute(self, assets: List[Asset]) -> DeploymentResult:
        """
        Execute rolling deployment.
        
        Deploys in batches with wait time between batches.
        Stops on max_failures unless continue_on_error is True.
        """
        start_time = datetime.utcnow()
        total_assets = len(assets)
        batch_count = ceil(1 / self.batch_size)
        assets_per_batch = max(1, int(total_assets * self.batch_size))
        
        self.logger.info(
            f"Starting rolling deployment: "
            f"{total_assets} assets, {batch_count} batches, "
            f"{assets_per_batch} per batch"
        )
        
        deployed = []
        failed = []
        logs = []
        failure_count = 0
        
        # Split assets into batches
        for batch_num in range(batch_count):
            start_idx = batch_num * assets_per_batch
            end_idx = min(start_idx + assets_per_batch, total_assets)
            batch = assets[start_idx:end_idx]
            
            if not batch:
                break
            
            self.logger.info(
                f"Deploying batch {batch_num + 1}/{batch_count}: "
                f"{len(batch)} assets"
            )
            
            # Deploy batch
            for asset in batch:
                try:
                    success, message = self._deploy_to_asset(asset)
                    
                    log_entry = {
                        "batch": batch_num + 1,
                        "asset_id": asset.id,
                        "asset_name": asset.hostname,
                        "success": success,
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    logs.append(log_entry)
                    
                    if success:
                        deployed.append(asset.id)
                        self.logger.info(f"✓ Asset {asset.id} deployed")
                    else:
                        failed.append(asset.id)
                        failure_count += 1
                        self.logger.error(f"✗ Asset {asset.id} failed: {message}")
                        
                        # Check if we should stop
                        if failure_count >= self.max_failures and not self.continue_on_error:
                            error_msg = f"Stopped after {failure_count} failures"
                            self.logger.error(error_msg)
                            
                            duration = (datetime.utcnow() - start_time).total_seconds()
                            return DeploymentResult(
                                success=False,
                                status=DeploymentStatus.FAILED,
                                assets_deployed=deployed,
                                assets_failed=failed,
                                execution_logs=logs,
                                duration_seconds=duration,
                                error_message=error_msg
                            )
                            
                except Exception as e:
                    failed.append(asset.id)
                    failure_count += 1
                    self.logger.error(f"✗ Asset {asset.id} exception: {e}")
                    
                    logs.append({
                        "batch": batch_num + 1,
                        "asset_id": asset.id,
                        "success": False,
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Wait between batches (except last batch)
            if batch_num < batch_count - 1 and batch_num < (end_idx // assets_per_batch):
                self.logger.info(f"Waiting {self.wait_seconds}s before next batch...")
                time.sleep(self.wait_seconds)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine status
        if not failed:
            status = DeploymentStatus.COMPLETED
            success = True
            error_msg = None
        elif not deployed:
            status = DeploymentStatus.FAILED
            success = False
            error_msg = "All deployments failed"
        else:
            status = DeploymentStatus.COMPLETED
            success = True
            error_msg = f"{len(failed)} failures out of {total_assets}"
        
        self.logger.info(
            f"Rolling deployment completed: "
            f"{len(deployed)}/{total_assets} successful in {duration:.2f}s"
        )
        
        return DeploymentResult(
            success=success,
            status=status,
            assets_deployed=deployed,
            assets_failed=failed,
            execution_logs=logs,
            duration_seconds=duration,
            error_message=error_msg
        )
