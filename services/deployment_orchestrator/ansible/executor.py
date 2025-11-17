"""
Ansible Executor

Executes Ansible playbooks for patch deployment on remote hosts.
"""

import logging
from typing import Dict, Any
from datetime import datetime
import tempfile
import os

from shared.models import Asset, Patch

logger = logging.getLogger(__name__)


class AnsibleExecutionResult:
    """Result of Ansible execution"""
    def __init__(
        self,
        success: bool,
        message: str,
        stdout: str = "",
        stderr: str = "",
        return_code: int = 0
    ):
        self.success = success
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.timestamp = datetime.utcnow()


class AnsibleExecutor:
    """
    Executes Ansible playbooks for patch deployment.
    
    Uses ansible-runner library for Python-native execution.
    """

    def __init__(self):
        """Initialize Ansible executor"""
        self.logger = logging.getLogger(__name__)

    def execute_patch(self, asset: Asset, patch: Patch) -> AnsibleExecutionResult:
        """
        Execute patch deployment on asset using Ansible.

        Args:
            asset: Asset to deploy to
            patch: Patch to deploy

        Returns:
            AnsibleExecutionResult with execution outcome
        """
        try:
            self.logger.info(f"Executing patch {patch.id} on asset {asset.id} via Ansible")

            # Generate playbook
            from services.deployment_orchestrator.ansible.playbook_generator import PlaybookGenerator
            generator = PlaybookGenerator()
            playbook_content = generator.generate_patch_playbook(asset, patch)

            # Create temporary directory for Ansible execution
            with tempfile.TemporaryDirectory() as tmpdir:
                # Write playbook
                playbook_path = os.path.join(tmpdir, "deploy.yml")
                with open(playbook_path, 'w') as f:
                    f.write(playbook_content)

                # Write patch script
                script_path = os.path.join(tmpdir, "patch.sh")
                with open(script_path, 'w') as f:
                    f.write(patch.patch_content)
                os.chmod(script_path, 0o755)

                # For MVP: Use subprocess to call ansible-playbook
                # In production: Use ansible-runner Python library
                import subprocess

                cmd = [
                    "ansible-playbook",
                    playbook_path,
                    "-i", f"{asset.hostname},",
                    "-e", f"patch_script={script_path}",
                    "-e", f"patch_id={patch.id}",
                    "-e", f"asset_id={asset.id}",
                ]

                # Execute
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                success = result.returncode == 0
                message = "Deployment successful" if success else "Deployment failed"

                self.logger.info(
                    f"Ansible execution completed: return_code={result.returncode}"
                )

                return AnsibleExecutionResult(
                    success=success,
                    message=message,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode
                )

        except subprocess.TimeoutExpired:
            self.logger.error("Ansible execution timed out")
            return AnsibleExecutionResult(
                success=False,
                message="Execution timed out",
                stderr="Ansible playbook execution exceeded 5 minute timeout",
                return_code=-1
            )

        except Exception as e:
            self.logger.error(f"Ansible execution failed: {e}")
            return AnsibleExecutionResult(
                success=False,
                message=f"Execution error: {str(e)}",
                stderr=str(e),
                return_code=-1
            )

    def execute_rollback(self, asset: Asset, patch: Patch) -> AnsibleExecutionResult:
        """
        Execute rollback script on asset.

        Args:
            asset: Asset to rollback
            patch: Patch with rollback script

        Returns:
            AnsibleExecutionResult
        """
        try:
            if not patch.rollback_script:
                return AnsibleExecutionResult(
                    success=False,
                    message="No rollback script available"
                )

            self.logger.info(f"Executing rollback for patch {patch.id} on asset {asset.id}")

            # Similar to execute_patch but with rollback script
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, "rollback.sh")
                with open(script_path, 'w') as f:
                    f.write(patch.rollback_script)
                os.chmod(script_path, 0o755)

                import subprocess

                # Direct SSH execution for rollback (simpler than full playbook)
                cmd = [
                    "ssh",
                    f"root@{asset.hostname}",
                    "bash", "-s"
                ]

                result = subprocess.run(
                    cmd,
                    input=patch.rollback_script,
                    capture_output=True,
                    text=True,
                    timeout=180  # 3 minute timeout
                )

                success = result.returncode == 0
                message = "Rollback successful" if success else "Rollback failed"

                return AnsibleExecutionResult(
                    success=success,
                    message=message,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode
                )

        except Exception as e:
            self.logger.error(f"Rollback execution failed: {e}")
            return AnsibleExecutionResult(
                success=False,
                message=f"Rollback error: {str(e)}",
                stderr=str(e),
                return_code=-1
            )
