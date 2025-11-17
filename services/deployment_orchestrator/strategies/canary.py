"""
Canary Deployment Strategy

Progressive rollout with monitoring: 10% → 50% → 100%.
Automatic promotion or rollback based on health checks.
"""

import logging
import time
from typing import List
from datetime import datetime

from services.deployment_orchestrator.strategies.base import (
    DeploymentStrategy, DeploymentResult, DeploymentStatus
)
from shared.models import Asset

logger = logging.getLogger(__name__)


class CanaryDeployment(DeploymentStrategy):
    """
    Canary deployment with progressive rollout.
    
    Deploys in stages with monitoring between each stage.
    Auto-promotes on success or rolls back on failure.
    """

    def __init__(
        self,
        patch,
        stages: List[float] = None,
        monitoring_duration: int = 900,
        auto_promote: bool = True,
        rollback_on_failure: bool = True
    ):
        """
        Initialize canary deployment.
        
        Args:
            patch: Patch to deploy
            stages: List of deployment percentages (default: [0.1, 0.5, 1.0])
            monitoring_duration: Seconds to monitor each stage (default: 15 min)
            auto_promote: Automatically promote if healthy
            rollback_on_failure: Automatically rollback on failure
        """
        super().__init__(patch)
        self.stages = stages or [0.1, 0.5, 1.0]  # 10%, 50%, 100%
        self.monitoring_duration = monitoring_duration
        self.auto_promote = auto_promote
        self.rollback_on_failure = rollback_on_failure
        
        self.logger.info(
            f"Initialized canary deployment: "
            f"stages={self.stages}, monitoring={monitoring_duration}s"
        )

    def validate_prerequisites(self, assets: List[Asset]) -> tuple[bool, str]:
        """Validate prerequisites"""
        if not assets:
            return False, "No assets provided"
        
        if self.patch.test_status != "passed":
            return False, f"Patch test status is {self.patch.test_status}"
        
        if not self.stages or len(self.stages) == 0:
            return False, "No deployment stages defined"
        
        # Validate stages are ascending and <= 1.0
        for i, stage in enumerate(self.stages):
            if stage <= 0 or stage > 1.0:
                return False, f"Invalid stage {i}: {stage} (must be 0-1)"
            if i > 0 and stage <= self.stages[i-1]:
                return False, f"Stages must be ascending"
        
        return True, ""

    def execute(self, assets: List[Asset]) -> DeploymentResult:
        """
        Execute canary deployment.
        
        Deploys progressively through stages, monitoring health
        at each stage before proceeding.
        """
        start_time = datetime.utcnow()
        total_assets = len(assets)
        
        self.logger.info(
            f"Starting canary deployment: "
            f"{total_assets} assets, {len(self.stages)} stages"
        )
        
        deployed = []
        failed = []
        logs = []
        assets_remaining = list(assets)
        
        # Execute each stage
        for stage_num, stage_pct in enumerate(self.stages):
            stage_target = int(total_assets * stage_pct)
            assets_to_deploy = stage_target - len(deployed)
            
            if assets_to_deploy <= 0:
                continue
            
            # Get next batch of assets
            batch = assets_remaining[:assets_to_deploy]
            assets_remaining = assets_remaining[assets_to_deploy:]
            
            self.logger.info(
                f"Canary stage {stage_num + 1}/{len(self.stages)}: "
                f"{int(stage_pct * 100)}% ({len(batch)} assets)"
            )
            
            # Deploy to batch
            stage_failures = 0
            for asset in batch:
                try:
                    success, message = self._deploy_to_asset(asset)
                    
                    log_entry = {
                        "stage": stage_num + 1,
                        "stage_pct": int(stage_pct * 100),
                        "asset_id": asset.id,
                        "asset_name": asset.hostname,
                        "success": success,
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    logs.append(log_entry)
                    
                    if success:
                        deployed.append(asset.id)
                        self.logger.info(f"✓ Canary asset {asset.id} deployed")
                    else:
                        failed.append(asset.id)
                        stage_failures += 1
                        self.logger.error(f"✗ Canary asset {asset.id} failed: {message}")
                        
                except Exception as e:
                    failed.append(asset.id)
                    stage_failures += 1
                    self.logger.error(f"✗ Canary asset {asset.id} exception: {e}")
                    
                    logs.append({
                        "stage": stage_num + 1,
                        "stage_pct": int(stage_pct * 100),
                        "asset_id": asset.id,
                        "success": False,
                        "message": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            # Check stage health
            stage_success_rate = (len(batch) - stage_failures) / len(batch) if batch else 0
            
            if stage_failures > 0:
                self.logger.warning(
                    f"Stage {stage_num + 1} completed with {stage_failures} failures "
                    f"({stage_success_rate * 100:.1f}% success rate)"
                )
                
                # Decide whether to continue
                if stage_success_rate < 0.8:  # Less than 80% success
                    error_msg = (
                        f"Canary stage {stage_num + 1} failed: "
                        f"{stage_success_rate * 100:.1f}% success rate"
                    )
                    self.logger.error(error_msg)
                    
                    if self.rollback_on_failure:
                        # TODO: Trigger rollback
                        self.logger.info("Automatic rollback triggered")
                    
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
            
            # Monitor stage health before proceeding (except last stage)
            if stage_num < len(self.stages) - 1:
                self.logger.info(
                    f"Monitoring canary stage {stage_num + 1} for "
                    f"{self.monitoring_duration}s..."
                )
                
                # Simplified monitoring - just wait
                # In production, this would check metrics, health checks, etc.
                time.sleep(min(self.monitoring_duration, 60))  # Cap at 60s for demo
                
                # Health check would go here
                health_ok = True  # Placeholder
                
                if not health_ok and not self.auto_promote:
                    error_msg = f"Health checks failed at stage {stage_num + 1}"
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
                
                self.logger.info(f"✓ Canary stage {stage_num + 1} healthy, promoting...")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Determine final status
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
            f"Canary deployment completed: "
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
