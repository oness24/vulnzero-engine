"""
Deployment strategies for patch rollout
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio
import structlog

logger = structlog.get_logger()


class DeploymentStrategy:
    """Base class for deployment strategies"""

    def __init__(self, name: str):
        self.name = name

    async def deploy(
        self,
        assets: List[Dict[str, Any]],
        deploy_func: Callable,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute deployment strategy

        Args:
            assets: List of assets to deploy to
            deploy_func: Function to deploy to single asset
            **kwargs: Additional arguments

        Returns:
            Deployment results
        """
        raise NotImplementedError


class RollingDeployment(DeploymentStrategy):
    """
    Rolling deployment strategy
    Deploy to assets in batches with configurable batch size
    """

    def __init__(self, batch_size: int = 1, wait_between_batches: int = 30):
        super().__init__("rolling")
        self.batch_size = batch_size
        self.wait_between_batches = wait_between_batches

    async def deploy(
        self,
        assets: List[Dict[str, Any]],
        deploy_func: Callable,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute rolling deployment

        Args:
            assets: List of assets
            deploy_func: Deployment function
            **kwargs: Additional arguments

        Returns:
            Deployment results
        """
        logger.info(
            "starting_rolling_deployment",
            total_assets=len(assets),
            batch_size=self.batch_size,
        )

        results = {
            "strategy": "rolling",
            "started_at": datetime.utcnow().isoformat(),
            "total_assets": len(assets),
            "successful": 0,
            "failed": 0,
            "batches": [],
        }

        # Split assets into batches
        batches = [
            assets[i:i + self.batch_size]
            for i in range(0, len(assets), self.batch_size)
        ]

        logger.info("rolling_deployment_batches", batch_count=len(batches))

        for batch_num, batch in enumerate(batches, 1):
            logger.info(
                "deploying_batch",
                batch_num=batch_num,
                total_batches=len(batches),
                batch_size=len(batch),
            )

            batch_results = {
                "batch_number": batch_num,
                "started_at": datetime.utcnow().isoformat(),
                "assets": [],
            }

            # Deploy to all assets in this batch concurrently
            tasks = []
            for asset in batch:
                task = deploy_func(asset, **kwargs)
                tasks.append(task)

            # Wait for all deployments in this batch
            batch_outcomes = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for asset, outcome in zip(batch, batch_outcomes):
                if isinstance(outcome, Exception):
                    logger.error(
                        "deployment_failed",
                        asset=asset.get("name"),
                        error=str(outcome),
                    )
                    batch_results["assets"].append({
                        "asset": asset.get("name"),
                        "success": False,
                        "error": str(outcome),
                    })
                    results["failed"] += 1
                else:
                    success = outcome.get("success", False)
                    batch_results["assets"].append({
                        "asset": asset.get("name"),
                        "success": success,
                        "result": outcome,
                    })
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1

            batch_results["completed_at"] = datetime.utcnow().isoformat()
            results["batches"].append(batch_results)

            # Wait between batches (except for last batch)
            if batch_num < len(batches) and self.wait_between_batches > 0:
                logger.info(
                    "waiting_between_batches",
                    seconds=self.wait_between_batches,
                )
                await asyncio.sleep(self.wait_between_batches)

        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = results["failed"] == 0

        logger.info(
            "rolling_deployment_complete",
            successful=results["successful"],
            failed=results["failed"],
        )

        return results


class BlueGreenDeployment(DeploymentStrategy):
    """
    Blue-Green deployment strategy
    Deploy to "green" environment first, then switch traffic
    """

    def __init__(self):
        super().__init__("blue_green")

    async def deploy(
        self,
        assets: List[Dict[str, Any]],
        deploy_func: Callable,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute blue-green deployment

        Args:
            assets: List of assets (should have blue/green markers)
            deploy_func: Deployment function
            **kwargs: Additional arguments

        Returns:
            Deployment results
        """
        logger.info("starting_blue_green_deployment", total_assets=len(assets))

        results = {
            "strategy": "blue_green",
            "started_at": datetime.utcnow().isoformat(),
            "total_assets": len(assets),
            "successful": 0,
            "failed": 0,
            "phases": {},
        }

        # Separate blue and green assets
        green_assets = [a for a in assets if a.get("environment") == "green"]
        blue_assets = [a for a in assets if a.get("environment") == "blue"]

        if not green_assets:
            # If no explicit green environment, use half as green
            mid = len(assets) // 2
            green_assets = assets[:mid]
            blue_assets = assets[mid:]

        # Phase 1: Deploy to green environment
        logger.info("deploying_to_green", asset_count=len(green_assets))

        green_tasks = [deploy_func(asset, **kwargs) for asset in green_assets]
        green_outcomes = await asyncio.gather(*green_tasks, return_exceptions=True)

        green_results = []
        green_success_count = 0

        for asset, outcome in zip(green_assets, green_outcomes):
            if isinstance(outcome, Exception):
                green_results.append({
                    "asset": asset.get("name"),
                    "success": False,
                    "error": str(outcome),
                })
            else:
                success = outcome.get("success", False)
                green_results.append({
                    "asset": asset.get("name"),
                    "success": success,
                    "result": outcome,
                })
                if success:
                    green_success_count += 1

        results["phases"]["green"] = {
            "assets": green_results,
            "successful": green_success_count,
            "failed": len(green_assets) - green_success_count,
        }

        # Check if green deployment was successful
        if green_success_count != len(green_assets):
            logger.error(
                "green_deployment_failed",
                successful=green_success_count,
                total=len(green_assets),
            )
            results["completed_at"] = datetime.utcnow().isoformat()
            results["success"] = False
            results["failed"] = len(green_assets) - green_success_count
            return results

        # Phase 2: Deploy to blue environment (production)
        logger.info("deploying_to_blue", asset_count=len(blue_assets))

        blue_tasks = [deploy_func(asset, **kwargs) for asset in blue_assets]
        blue_outcomes = await asyncio.gather(*blue_tasks, return_exceptions=True)

        blue_results = []
        blue_success_count = 0

        for asset, outcome in zip(blue_assets, blue_outcomes):
            if isinstance(outcome, Exception):
                blue_results.append({
                    "asset": asset.get("name"),
                    "success": False,
                    "error": str(outcome),
                })
            else:
                success = outcome.get("success", False)
                blue_results.append({
                    "asset": asset.get("name"),
                    "success": success,
                    "result": outcome,
                })
                if success:
                    blue_success_count += 1

        results["phases"]["blue"] = {
            "assets": blue_results,
            "successful": blue_success_count,
            "failed": len(blue_assets) - blue_success_count,
        }

        results["successful"] = green_success_count + blue_success_count
        results["failed"] = (len(green_assets) - green_success_count) + (len(blue_assets) - blue_success_count)
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = results["failed"] == 0

        logger.info(
            "blue_green_deployment_complete",
            successful=results["successful"],
            failed=results["failed"],
        )

        return results


class CanaryDeployment(DeploymentStrategy):
    """
    Canary deployment strategy
    Deploy to a small subset first, then gradually increase
    """

    def __init__(
        self,
        canary_percentage: float = 10.0,
        monitor_duration: int = 300,
    ):
        super().__init__("canary")
        self.canary_percentage = canary_percentage
        self.monitor_duration = monitor_duration

    async def deploy(
        self,
        assets: List[Dict[str, Any]],
        deploy_func: Callable,
        health_check_func: Optional[Callable] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute canary deployment

        Args:
            assets: List of assets
            deploy_func: Deployment function
            health_check_func: Optional health check function
            **kwargs: Additional arguments

        Returns:
            Deployment results
        """
        logger.info(
            "starting_canary_deployment",
            total_assets=len(assets),
            canary_percentage=self.canary_percentage,
        )

        results = {
            "strategy": "canary",
            "started_at": datetime.utcnow().isoformat(),
            "total_assets": len(assets),
            "successful": 0,
            "failed": 0,
            "phases": {},
        }

        # Calculate canary size
        canary_size = max(1, int(len(assets) * self.canary_percentage / 100))
        canary_assets = assets[:canary_size]
        remaining_assets = assets[canary_size:]

        # Phase 1: Deploy to canary
        logger.info("deploying_to_canary", canary_size=canary_size)

        canary_tasks = [deploy_func(asset, **kwargs) for asset in canary_assets]
        canary_outcomes = await asyncio.gather(*canary_tasks, return_exceptions=True)

        canary_results = []
        canary_success_count = 0

        for asset, outcome in zip(canary_assets, canary_outcomes):
            if isinstance(outcome, Exception):
                canary_results.append({
                    "asset": asset.get("name"),
                    "success": False,
                    "error": str(outcome),
                })
            else:
                success = outcome.get("success", False)
                canary_results.append({
                    "asset": asset.get("name"),
                    "success": success,
                    "result": outcome,
                })
                if success:
                    canary_success_count += 1

        results["phases"]["canary"] = {
            "assets": canary_results,
            "successful": canary_success_count,
            "failed": len(canary_assets) - canary_success_count,
        }

        # Check canary health
        if canary_success_count != len(canary_assets):
            logger.error(
                "canary_deployment_failed",
                successful=canary_success_count,
                total=len(canary_assets),
            )
            results["completed_at"] = datetime.utcnow().isoformat()
            results["success"] = False
            results["failed"] = len(canary_assets) - canary_success_count
            return results

        # Monitor canary
        if health_check_func and self.monitor_duration > 0:
            logger.info(
                "monitoring_canary",
                duration_seconds=self.monitor_duration,
            )
            await asyncio.sleep(self.monitor_duration)

            # Run health checks on canary
            health_checks_passed = True
            if health_check_func:
                for asset in canary_assets:
                    try:
                        health_result = await health_check_func(asset)
                        if not health_result.get("healthy", False):
                            health_checks_passed = False
                            logger.warning(
                                "canary_health_check_failed",
                                asset=asset.get("name"),
                            )
                            break
                    except Exception as e:
                        logger.error(
                            "canary_health_check_error",
                            asset=asset.get("name"),
                            error=str(e),
                        )
                        health_checks_passed = False
                        break

            if not health_checks_passed:
                logger.error("canary_monitoring_failed")
                results["completed_at"] = datetime.utcnow().isoformat()
                results["success"] = False
                results["error"] = "Canary health checks failed"
                return results

        # Phase 2: Deploy to remaining assets
        logger.info("deploying_to_remaining", asset_count=len(remaining_assets))

        remaining_tasks = [deploy_func(asset, **kwargs) for asset in remaining_assets]
        remaining_outcomes = await asyncio.gather(*remaining_tasks, return_exceptions=True)

        remaining_results = []
        remaining_success_count = 0

        for asset, outcome in zip(remaining_assets, remaining_outcomes):
            if isinstance(outcome, Exception):
                remaining_results.append({
                    "asset": asset.get("name"),
                    "success": False,
                    "error": str(outcome),
                })
            else:
                success = outcome.get("success", False)
                remaining_results.append({
                    "asset": asset.get("name"),
                    "success": success,
                    "result": outcome,
                })
                if success:
                    remaining_success_count += 1

        results["phases"]["full_rollout"] = {
            "assets": remaining_results,
            "successful": remaining_success_count,
            "failed": len(remaining_assets) - remaining_success_count,
        }

        results["successful"] = canary_success_count + remaining_success_count
        results["failed"] = (len(canary_assets) - canary_success_count) + (len(remaining_assets) - remaining_success_count)
        results["completed_at"] = datetime.utcnow().isoformat()
        results["success"] = results["failed"] == 0

        logger.info(
            "canary_deployment_complete",
            successful=results["successful"],
            failed=results["failed"],
        )

        return results


def get_deployment_strategy(
    strategy_type: str,
    **kwargs,
) -> DeploymentStrategy:
    """
    Get deployment strategy instance

    Args:
        strategy_type: Type of strategy (rolling, blue_green, canary)
        **kwargs: Strategy-specific arguments

    Returns:
        DeploymentStrategy instance
    """
    strategies = {
        "rolling": RollingDeployment,
        "blue_green": BlueGreenDeployment,
        "canary": CanaryDeployment,
    }

    strategy_class = strategies.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"Unknown deployment strategy: {strategy_type}")

    return strategy_class(**kwargs)
