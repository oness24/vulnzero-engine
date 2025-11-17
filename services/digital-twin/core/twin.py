"""
Digital Twin Orchestrator

Main class for managing digital twin testing lifecycle.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from services.digital_twin.core.container import ContainerManager
from services.digital_twin.executors.patch_executor import PatchExecutor, ExecutionResult
from shared.models import Asset, Patch

logger = logging.getLogger(__name__)


class DigitalTwin:
    """
    Digital Twin for safe patch testing.
    
    Creates isolated Docker environment matching production asset
    for testing patches before deployment.
    """

    def __init__(self, asset: Asset, patch: Patch):
        """
        Initialize digital twin for asset and patch.

        Args:
            asset: Production asset to clone
            patch: Patch to test
        """
        self.asset = asset
        self.patch = patch
        self.container_manager = ContainerManager()
        self.container = None
        self.executor = None
        self.logger = logging.getLogger(__name__)
        
        self.test_id = f"twin-{asset.id}-{patch.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def provision(self) -> bool:
        """
        Provision digital twin container.

        Returns:
            True if provisioning successful
        """
        try:
            self.logger.info(f"Provisioning digital twin for asset {self.asset.id}")

            # Determine image based on asset OS
            image = self._determine_image()
            
            # Create container
            self.container = self.container_manager.create_container(
                image=image,
                name=self.test_id,
                environment=self._build_environment(),
            )

            # Start container
            if not self.container_manager.start_container(self.container):
                return False

            # Initialize executor
            self.executor = PatchExecutor(self.container)

            # Run setup commands
            self._setup_container()

            self.logger.info(f"Digital twin provisioned successfully: {self.test_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to provision digital twin: {e}")
            return False

    def execute_patch(self) -> ExecutionResult:
        """
        Execute patch in digital twin.

        Returns:
            ExecutionResult with execution details
        """
        if not self.executor:
            raise RuntimeError("Digital twin not provisioned. Call provision() first.")

        self.logger.info(f"Executing patch {self.patch.id} in digital twin")
        
        return self.executor.execute_patch(
            patch_content=self.patch.patch_content,
            timeout_seconds=600
        )

    def run_health_checks(self) -> Dict[str, Any]:
        """
        Run health checks after patch execution.

        Returns:
            Dictionary of health check results
        """
        if not self.executor:
            raise RuntimeError("Digital twin not provisioned.")

        self.logger.info("Running health checks...")
        
        from services.digital_twin.validators.health_checks import run_all_health_checks
        
        return run_all_health_checks(self.container, self.asset)

    def cleanup(self) -> bool:
        """
        Cleanup digital twin resources.

        Returns:
            True if cleanup successful
        """
        if not self.container:
            return True

        try:
            self.logger.info(f"Cleaning up digital twin: {self.test_id}")
            
            # Stop and remove container
            self.container_manager.stop_container(self.container)
            return self.container_manager.remove_container(self.container)

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return False

    def _determine_image(self) -> str:
        """Determine Docker image based on asset OS"""
        os_type = (self.asset.os_type or "").lower()
        os_version = (self.asset.os_version or "").lower()

        if "ubuntu" in os_type:
            if "24.04" in os_version:
                return "ubuntu-24.04"
            elif "22.04" in os_version:
                return "ubuntu-22.04"
            else:
                return "ubuntu-20.04"
        
        elif "rhel" in os_type or "rocky" in os_type:
            if "9" in os_version:
                return "rhel-9"
            else:
                return "rhel-8"
        
        elif "amazon" in os_type:
            return "amazonlinux-2"
        
        elif "debian" in os_type:
            if "12" in os_version:
                return "debian-12"
            else:
                return "debian-11"
        
        # Default to Ubuntu 22.04
        return "ubuntu-22.04"

    def _build_environment(self) -> Dict[str, str]:
        """Build environment variables for container"""
        return {
            "VULNZERO_ASSET_ID": str(self.asset.id),
            "VULNZERO_PATCH_ID": str(self.patch.id),
            "VULNZERO_TEST_MODE": "true",
        }

    def _setup_container(self):
        """Run initial setup commands in container"""
        # Update package manager
        os_type = (self.asset.os_type or "").lower()
        
        if "ubuntu" in os_type or "debian" in os_type:
            self.container.exec_run("apt-get update -qq")
        elif "rhel" in os_type or "rocky" in os_type:
            self.container.exec_run("yum update -y -q")

    def __enter__(self):
        """Context manager entry"""
        self.provision()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
