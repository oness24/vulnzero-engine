"""
VulnZero Deployment Orchestrator

Manages production deployment of patches with multiple strategies,
pre/post validation, and automatic rollback capabilities.
"""

__version__ = "0.1.0"

from services.deployment_orchestrator.core.engine import DeploymentEngine
from services.deployment_orchestrator.strategies.base import DeploymentStrategy
from services.deployment_orchestrator.strategies.blue_green import BlueGreenDeployment
from services.deployment_orchestrator.strategies.rolling import RollingDeployment
from services.deployment_orchestrator.strategies.canary import CanaryDeployment

__all__ = [
    "DeploymentEngine",
    "DeploymentStrategy",
    "BlueGreenDeployment",
    "RollingDeployment",
    "CanaryDeployment",
]
