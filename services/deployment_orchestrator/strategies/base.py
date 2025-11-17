"""
Base Deployment Strategy

Abstract base class for all deployment strategies.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum
import logging

from shared.models import Asset, Patch

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Deployment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentResult:
    """Result of a deployment operation"""
    def __init__(
        self,
        success: bool,
        status: DeploymentStatus,
        assets_deployed: List[int],
        assets_failed: List[int],
        execution_logs: List[Dict[str, Any]],
        duration_seconds: float,
        error_message: str = None
    ):
        self.success = success
        self.status = status
        self.assets_deployed = assets_deployed
        self.assets_failed = assets_failed
        self.execution_logs = execution_logs
        self.duration_seconds = duration_seconds
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "assets_deployed": self.assets_deployed,
            "assets_failed": self.assets_failed,
            "total_assets": len(self.assets_deployed) + len(self.assets_failed),
            "success_rate": len(self.assets_deployed) / (len(self.assets_deployed) + len(self.assets_failed)) * 100 if (len(self.assets_deployed) + len(self.assets_failed)) > 0 else 0,
            "execution_logs": self.execution_logs,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }


class DeploymentStrategy(ABC):
    """
    Abstract base class for deployment strategies.
    """

    def __init__(self, patch: Patch):
        """
        Initialize deployment strategy.

        Args:
            patch: Patch to deploy
        """
        self.patch = patch
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def execute(self, assets: List[Asset]) -> DeploymentResult:
        """
        Execute deployment strategy.

        Args:
            assets: List of assets to deploy to

        Returns:
            DeploymentResult with deployment outcome
        """
        pass

    @abstractmethod
    def validate_prerequisites(self, assets: List[Asset]) -> tuple[bool, str]:
        """
        Validate prerequisites for deployment.

        Args:
            assets: Assets to validate

        Returns:
            Tuple of (valid, error_message)
        """
        pass

    def _deploy_to_asset(self, asset: Asset) -> tuple[bool, str]:
        """
        Deploy patch to a single asset.

        Args:
            asset: Asset to deploy to

        Returns:
            Tuple of (success, message)
        """
        from services.deployment_orchestrator.ansible.executor import AnsibleExecutor

        executor = AnsibleExecutor()
        result = executor.execute_patch(asset, self.patch)

        return result.success, result.message
