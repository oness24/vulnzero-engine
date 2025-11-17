"""
All-At-Once Deployment Strategy

Deploys to all assets simultaneously. Fastest but highest risk.
Best for dev/test environments.
"""

import logging
from typing import List
from datetime import datetime

from services.deployment_orchestrator.strategies.base import (
    DeploymentStrategy, DeploymentResult, DeploymentStatus
)
from shared.models import Asset

logger = logging.getLogger(__name__)


class AllAtOnceDeployment(DeploymentStrategy):
    """
    Deploy to all assets simultaneously.
    
    Fastest deployment method but highest risk. Recommended only for
    dev/test environments or when downtime is acceptable.
    """

    def __init__(self, patch):
        """Initialize all-at-once strategy"""
        super().__init__(patch)
        self.logger.info("Initialized all-at-once deployment strategy")

    def validate_prerequisites(self, assets: List[Asset]) -> tuple[bool, str]:
        """
        Validate prerequisites for all-at-once deployment.
        
        Args:
            assets: Assets to deploy to
            
        Returns:
            Tuple of (valid, error_message)
        """
        if not assets:
            return False, "No assets provided for deployment"
        
        # Check patch test status
        if self.patch.test_status != "passed":
            return False, f"Patch test status is {self.patch.test_status}, must be 'passed'"
        
        # Validate patch content exists
        if not self.patch.patch_content:
            return False, "Patch content is empty"
        
        self.logger.info(f"Prerequisites validated for {len(assets)} assets")
        return True, ""

    def execute(self, assets: List[Asset]) -> DeploymentResult:
        """
        Execute all-at-once deployment.
        
        Deploys to all assets simultaneously without waiting.
        
        Args:
            assets: List of assets to deploy to
            
        Returns:
            DeploymentResult with deployment outcome
        """
        start_time = datetime.utcnow()
        self.logger.info(f"Starting all-at-once deployment to {len(assets)} assets")
        
        deployed = []
        failed = []
        logs = []
        
        # Deploy to all assets simultaneously
        for asset in assets:
            try:
                success, message = self._deploy_to_asset(asset)
                
                log_entry = {
                    "asset_id": asset.id,
                    "asset_name": asset.hostname,
                    "success": success,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
                logs.append(log_entry)
                
                if success:
                    deployed.append(asset.id)
                    self.logger.info(f"✓ Asset {asset.id} deployed successfully")
                else:
                    failed.append(asset.id)
                    self.logger.error(f"✗ Asset {asset.id} failed: {message}")
                    
            except Exception as e:
                failed.append(asset.id)
                error_msg = f"Exception during deployment: {str(e)}"
                self.logger.error(f"✗ Asset {asset.id} exception: {e}")
                logs.append({
                    "asset_id": asset.id,
                    "asset_name": asset.hostname,
                    "success": False,
                    "message": error_msg,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine overall status
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
            success = True  # Partial success
            error_msg = f"{len(failed)} deployments failed"
        
        self.logger.info(
            f"All-at-once deployment completed: "
            f"{len(deployed)}/{len(assets)} successful in {duration:.2f}s"
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
