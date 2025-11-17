"""
Patch Executor

Executes patch scripts in Docker containers and captures results.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import docker

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of patch execution"""
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_seconds: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_seconds = duration_seconds
        self.success = success
        self.error_message = error_message
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


class PatchExecutor:
    """
    Executes patches in Docker containers.
    """

    def __init__(self, container: docker.models.containers.Container):
        """
        Initialize patch executor.

        Args:
            container: Docker container to execute in
        """
        self.container = container
        self.logger = logging.getLogger(__name__)

    def execute_patch(
        self,
        patch_content: str,
        timeout_seconds: int = 600
    ) -> ExecutionResult:
        """
        Execute a patch script in the container.

        Args:
            patch_content: Bash script content
            timeout_seconds: Execution timeout

        Returns:
            ExecutionResult with execution details
        """
        start_time = datetime.utcnow()

        try:
            # Write patch to container
            patch_path = "/tmp/vulnzero_patch.sh"
            self.logger.info(f"Writing patch to {patch_path}")

            # Create patch file in container
            self.container.exec_run(
                f"bash -c 'cat > {patch_path} << HEREDOC_EOF\n{patch_content}\nHEREDOC_EOF'"
            )

            # Make executable
            self.container.exec_run(f"chmod +x {patch_path}")

            # Execute patch
            self.logger.info("Executing patch...")
            exec_result = self.container.exec_run(
                f"bash {patch_path}",
                demux=True,
                stream=False,
            )

            exit_code = exec_result.exit_code
            stdout, stderr = exec_result.output

            stdout_str = stdout.decode("utf-8") if stdout else ""
            stderr_str = stderr.decode("utf-8") if stderr else ""

            duration = (datetime.utcnow() - start_time).total_seconds()
            success = exit_code == 0

            self.logger.info(
                f"Patch execution completed: exit_code={exit_code}, "
                f"duration={duration:.2f}s, success={success}"
            )

            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_seconds=duration,
                success=success,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"Patch execution failed: {e}")

            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )

    def execute_rollback(
        self,
        rollback_content: str,
        timeout_seconds: int = 300
    ) -> ExecutionResult:
        """
        Execute a rollback script.

        Args:
            rollback_content: Rollback script content
            timeout_seconds: Execution timeout

        Returns:
            ExecutionResult
        """
        self.logger.info("Executing rollback script...")
        return self.execute_patch(rollback_content, timeout_seconds)

    def get_system_state(self) -> Dict[str, Any]:
        """
        Capture current system state.

        Returns:
            Dictionary with system state information
        """
        state = {}

        # Get running services
        result = self.container.exec_run("systemctl list-units --type=service --state=running", demux=True)
        if result.exit_code == 0:
            stdout, _ = result.output
            state["running_services"] = stdout.decode("utf-8") if stdout else ""

        # Get installed packages (Ubuntu/Debian)
        result = self.container.exec_run("dpkg -l", demux=True)
        if result.exit_code == 0:
            stdout, _ = result.output
            state["installed_packages"] = stdout.decode("utf-8") if stdout else ""

        # Get listening ports
        result = self.container.exec_run("ss -tulpn", demux=True)
        if result.exit_code == 0:
            stdout, _ = result.output
            state["listening_ports"] = stdout.decode("utf-8") if stdout else ""

        return state
