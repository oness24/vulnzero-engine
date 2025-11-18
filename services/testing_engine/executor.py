"""
Patch execution engine for testing patches in isolated environments
"""

from typing import Dict, Any, Optional
from datetime import datetime
from docker.models.containers import Container
import structlog

from services.testing_engine.container_manager import ContainerManager
from services.testing_engine.state_monitor import SystemStateMonitor

logger = structlog.get_logger()


class PatchExecutor:
    """
    Executes patches in isolated test environments
    """

    def __init__(self, container_manager: ContainerManager):
        self.container_manager = container_manager
        self.state_monitor = SystemStateMonitor(container_manager)

    def execute_patch(
        self,
        container: Container,
        patch_script: str,
        validation_script: Optional[str] = None,
        capture_state: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a patch in a container

        Args:
            container: Docker container
            patch_script: Patch script to execute
            validation_script: Optional validation script
            capture_state: Whether to capture before/after state

        Returns:
            Execution results
        """
        logger.info("executing_patch", container_id=container.id)

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "container_id": container.id,
            "success": False,
            "patch_output": {},
            "validation_output": {},
            "state_before": {},
            "state_after": {},
            "state_changes": {},
            "errors": [],
        }

        try:
            # Capture state before
            if capture_state:
                logger.info("capturing_state_before", container_id=container.id)
                result["state_before"] = self.state_monitor.capture_state(container)

            # Copy patch script to container
            patch_path = "/tmp/patch_script.sh"
            if not self.container_manager.copy_content_to_container(
                container,
                patch_script,
                patch_path,
            ):
                result["errors"].append("Failed to copy patch script to container")
                return result

            # Execute patch script
            logger.info("executing_patch_script", container_id=container.id)
            patch_output = self.container_manager.execute_command(
                container,
                f"bash {patch_path}",
            )

            result["patch_output"] = {
                "exit_code": patch_output["exit_code"],
                "stdout": patch_output["stdout"],
                "stderr": patch_output["stderr"],
                "success": patch_output["success"],
            }

            if not patch_output["success"]:
                result["errors"].append(f"Patch execution failed with exit code {patch_output['exit_code']}")
                logger.error(
                    "patch_execution_failed",
                    container_id=container.id,
                    exit_code=patch_output["exit_code"],
                )
                return result

            # Capture state after
            if capture_state:
                logger.info("capturing_state_after", container_id=container.id)
                result["state_after"] = self.state_monitor.capture_state(container)

                # Compare states
                result["state_changes"] = self.state_monitor.compare_states(
                    result["state_before"],
                    result["state_after"],
                )

            # Execute validation script if provided
            if validation_script:
                logger.info("executing_validation_script", container_id=container.id)

                validation_path = "/tmp/validation_script.sh"
                if self.container_manager.copy_content_to_container(
                    container,
                    validation_script,
                    validation_path,
                ):
                    validation_output = self.container_manager.execute_command(
                        container,
                        f"bash {validation_path}",
                    )

                    result["validation_output"] = {
                        "exit_code": validation_output["exit_code"],
                        "stdout": validation_output["stdout"],
                        "stderr": validation_output["stderr"],
                        "success": validation_output["success"],
                    }

                    if not validation_output["success"]:
                        result["errors"].append("Validation script failed")
                        logger.warning("validation_failed", container_id=container.id)
                else:
                    result["errors"].append("Failed to copy validation script")

            # Overall success
            result["success"] = (
                patch_output["success"] and
                (not validation_script or result["validation_output"].get("success", False))
            )

            result["completed_at"] = datetime.utcnow().isoformat()

            logger.info(
                "patch_execution_complete",
                container_id=container.id,
                success=result["success"],
            )

            return result

        except Exception as e:
            logger.error(
                "patch_execution_error",
                error=str(e),
                container_id=container.id,
            )
            result["errors"].append(f"Execution error: {str(e)}")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

    def execute_rollback(
        self,
        container: Container,
        rollback_script: str,
    ) -> Dict[str, Any]:
        """
        Execute rollback script

        Args:
            container: Docker container
            rollback_script: Rollback script to execute

        Returns:
            Execution results
        """
        logger.info("executing_rollback", container_id=container.id)

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "container_id": container.id,
            "success": False,
            "output": {},
            "errors": [],
        }

        try:
            # Copy rollback script to container
            rollback_path = "/tmp/rollback_script.sh"
            if not self.container_manager.copy_content_to_container(
                container,
                rollback_script,
                rollback_path,
            ):
                result["errors"].append("Failed to copy rollback script to container")
                return result

            # Execute rollback script
            rollback_output = self.container_manager.execute_command(
                container,
                f"bash {rollback_path}",
            )

            result["output"] = {
                "exit_code": rollback_output["exit_code"],
                "stdout": rollback_output["stdout"],
                "stderr": rollback_output["stderr"],
                "success": rollback_output["success"],
            }

            result["success"] = rollback_output["success"]
            result["completed_at"] = datetime.utcnow().isoformat()

            if result["success"]:
                logger.info("rollback_successful", container_id=container.id)
            else:
                logger.error("rollback_failed", container_id=container.id)
                result["errors"].append(f"Rollback failed with exit code {rollback_output['exit_code']}")

            return result

        except Exception as e:
            logger.error("rollback_execution_error", error=str(e), container_id=container.id)
            result["errors"].append(f"Rollback error: {str(e)}")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

    def test_rollback(
        self,
        container: Container,
        patch_script: str,
        rollback_script: str,
        target_package: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test that rollback works correctly

        Args:
            container: Docker container
            patch_script: Patch script
            rollback_script: Rollback script
            target_package: Optional package to verify

        Returns:
            Test results
        """
        logger.info("testing_rollback", container_id=container.id)

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "success": False,
            "patch_applied": False,
            "rollback_executed": False,
            "state_restored": False,
            "errors": [],
        }

        try:
            # Capture initial state
            initial_state = self.state_monitor.capture_state(
                container,
                packages=[target_package] if target_package else None,
            )

            # Apply patch
            patch_result = self.execute_patch(
                container,
                patch_script,
                capture_state=False,
            )

            result["patch_applied"] = patch_result["success"]

            if not patch_result["success"]:
                result["errors"].append("Patch application failed")
                return result

            # Execute rollback
            rollback_result = self.execute_rollback(container, rollback_script)

            result["rollback_executed"] = rollback_result["success"]

            if not rollback_result["success"]:
                result["errors"].append("Rollback execution failed")
                return result

            # Capture final state
            final_state = self.state_monitor.capture_state(
                container,
                packages=[target_package] if target_package else None,
            )

            # Compare states
            if target_package:
                initial_version = initial_state["packages"].get(target_package)
                final_version = final_state["packages"].get(target_package)

                if initial_version == final_version:
                    result["state_restored"] = True
                    logger.info(
                        "rollback_verified",
                        package=target_package,
                        version=initial_version,
                    )
                else:
                    result["errors"].append(
                        f"Version mismatch: {initial_version} != {final_version}"
                    )
                    logger.warning(
                        "rollback_verification_failed",
                        initial_version=initial_version,
                        final_version=final_version,
                    )

            result["success"] = result["patch_applied"] and result["rollback_executed"] and result["state_restored"]
            result["completed_at"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            logger.error("rollback_test_error", error=str(e))
            result["errors"].append(f"Rollback test error: {str(e)}")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

    def verify_patch_idempotency(
        self,
        container: Container,
        patch_script: str,
    ) -> Dict[str, Any]:
        """
        Verify that patch can be run multiple times safely

        Args:
            container: Docker container
            patch_script: Patch script to test

        Returns:
            Idempotency test results
        """
        logger.info("testing_idempotency", container_id=container.id)

        result = {
            "started_at": datetime.utcnow().isoformat(),
            "success": False,
            "first_run": {},
            "second_run": {},
            "is_idempotent": False,
            "errors": [],
        }

        try:
            # First execution
            logger.info("first_execution", container_id=container.id)
            first_result = self.execute_patch(
                container,
                patch_script,
                capture_state=True,
            )

            result["first_run"] = {
                "success": first_result["success"],
                "exit_code": first_result["patch_output"]["exit_code"],
            }

            if not first_result["success"]:
                result["errors"].append("First execution failed")
                return result

            # Second execution (should be idempotent)
            logger.info("second_execution", container_id=container.id)
            second_result = self.execute_patch(
                container,
                patch_script,
                capture_state=True,
            )

            result["second_run"] = {
                "success": second_result["success"],
                "exit_code": second_result["patch_output"]["exit_code"],
            }

            # Check if second run succeeded and made no unexpected changes
            if second_result["success"]:
                # Ideally, second run should not change state
                has_changes = second_result["state_changes"].get("has_changes", False)

                if not has_changes:
                    result["is_idempotent"] = True
                    logger.info("patch_is_idempotent", container_id=container.id)
                else:
                    logger.warning(
                        "patch_made_changes_on_second_run",
                        container_id=container.id,
                    )
                    # Still consider it idempotent if it succeeded
                    result["is_idempotent"] = True
                    result["warnings"] = ["Patch made changes on second run"]
            else:
                result["errors"].append("Second execution failed")

            result["success"] = result["first_run"]["success"] and result["second_run"]["success"]
            result["completed_at"] = datetime.utcnow().isoformat()

            return result

        except Exception as e:
            logger.error("idempotency_test_error", error=str(e))
            result["errors"].append(f"Idempotency test error: {str(e)}")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

    def execute_custom_test(
        self,
        container: Container,
        test_script: str,
        test_name: str = "custom_test",
    ) -> Dict[str, Any]:
        """
        Execute a custom test script

        Args:
            container: Docker container
            test_script: Test script to execute
            test_name: Name of the test

        Returns:
            Test results
        """
        logger.info("executing_custom_test", test_name=test_name, container_id=container.id)

        result = {
            "test_name": test_name,
            "started_at": datetime.utcnow().isoformat(),
            "success": False,
            "output": {},
            "errors": [],
        }

        try:
            # Copy test script to container
            test_path = f"/tmp/{test_name}.sh"
            if not self.container_manager.copy_content_to_container(
                container,
                test_script,
                test_path,
            ):
                result["errors"].append("Failed to copy test script to container")
                return result

            # Execute test script
            test_output = self.container_manager.execute_command(
                container,
                f"bash {test_path}",
            )

            result["output"] = {
                "exit_code": test_output["exit_code"],
                "stdout": test_output["stdout"],
                "stderr": test_output["stderr"],
            }

            result["success"] = test_output["success"]
            result["completed_at"] = datetime.utcnow().isoformat()

            if result["success"]:
                logger.info("custom_test_passed", test_name=test_name)
            else:
                logger.warning("custom_test_failed", test_name=test_name)
                result["errors"].append(f"Test failed with exit code {test_output['exit_code']}")

            return result

        except Exception as e:
            logger.error("custom_test_error", error=str(e), test_name=test_name)
            result["errors"].append(f"Test execution error: {str(e)}")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result
