"""
Asset connection manager for SSH and agent-based connections
"""

from typing import Dict, Any, Optional
import paramiko
import structlog
from datetime import datetime

logger = structlog.get_logger()


class ConnectionManager:
    """Base class for connection managers"""

    def __init__(self):
        self.connection_type = "base"

    def connect(self, asset: Dict[str, Any]) -> bool:
        """Establish connection to asset"""
        raise NotImplementedError

    def disconnect(self):
        """Close connection"""
        raise NotImplementedError

    def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute command on asset"""
        raise NotImplementedError

    def copy_file(self, local_path: str, remote_path: str) -> bool:
        """Copy file to asset"""
        raise NotImplementedError


class SSHConnectionManager(ConnectionManager):
    """
    SSH-based connection manager using paramiko
    """

    def __init__(self):
        super().__init__()
        self.connection_type = "ssh"
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None

    def connect(
        self,
        asset: Dict[str, Any],
        timeout: int = 30,
    ) -> bool:
        """
        Establish SSH connection to asset

        Args:
            asset: Asset information with connection details
            timeout: Connection timeout in seconds

        Returns:
            True if successful
        """
        logger.info("connecting_via_ssh", asset=asset.get("name"))

        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Extract connection details
            hostname = asset.get("ip_address") or asset.get("hostname")
            username = asset.get("ssh_user", "root")
            port = asset.get("ssh_port", 22)

            # Authentication
            if asset.get("ssh_key_path"):
                # Key-based authentication
                self.client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    key_filename=asset["ssh_key_path"],
                    timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            elif asset.get("ssh_password"):
                # Password-based authentication
                self.client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=asset["ssh_password"],
                    timeout=timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            else:
                # Try default SSH keys
                self.client.connect(
                    hostname=hostname,
                    port=port,
                    username=username,
                    timeout=timeout,
                )

            # Open SFTP session
            self.sftp = self.client.open_sftp()

            logger.info("ssh_connection_established", asset=asset.get("name"))
            return True

        except Exception as e:
            logger.error(
                "ssh_connection_failed",
                asset=asset.get("name"),
                error=str(e),
            )
            return False

    def disconnect(self):
        """Close SSH connection"""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
            self.sftp = None

        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None

        logger.info("ssh_connection_closed")

    def execute_command(
        self,
        command: str,
        sudo: bool = False,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Execute command via SSH

        Args:
            command: Command to execute
            sudo: Use sudo
            timeout: Command timeout in seconds

        Returns:
            Dictionary with exit_code, stdout, stderr
        """
        if not self.client:
            return {
                "success": False,
                "error": "Not connected",
            }

        logger.debug("executing_ssh_command", command=command[:100])

        try:
            if sudo:
                command = f"sudo {command}"

            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=timeout,
            )

            # Wait for command to complete
            exit_code = stdout.channel.recv_exit_status()

            # Read output
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')

            result = {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout_data,
                "stderr": stderr_data,
            }

            logger.debug(
                "ssh_command_completed",
                exit_code=exit_code,
            )

            return result

        except Exception as e:
            logger.error("ssh_command_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    def copy_file(
        self,
        local_path: str,
        remote_path: str,
        permissions: int = 0o644,
    ) -> bool:
        """
        Copy file to remote asset via SFTP

        Args:
            local_path: Local file path
            remote_path: Remote file path
            permissions: File permissions (octal)

        Returns:
            True if successful
        """
        if not self.sftp:
            logger.error("sftp_not_available")
            return False

        logger.debug(
            "copying_file_via_sftp",
            local=local_path,
            remote=remote_path,
        )

        try:
            self.sftp.put(local_path, remote_path)
            self.sftp.chmod(remote_path, permissions)

            logger.info("file_copied_successfully")
            return True

        except Exception as e:
            logger.error("sftp_copy_failed", error=str(e))
            return False

    def copy_content(
        self,
        content: str,
        remote_path: str,
        permissions: int = 0o644,
    ) -> bool:
        """
        Copy content to remote file

        Args:
            content: File content
            remote_path: Remote file path
            permissions: File permissions

        Returns:
            True if successful
        """
        if not self.sftp:
            logger.error("sftp_not_available")
            return False

        logger.debug("writing_content_via_sftp", remote=remote_path)

        try:
            # Write content to remote file
            with self.sftp.file(remote_path, 'w') as remote_file:
                remote_file.write(content)

            # Set permissions
            self.sftp.chmod(remote_path, permissions)

            logger.info("content_written_successfully")
            return True

        except Exception as e:
            logger.error("sftp_write_failed", error=str(e))
            return False

    def get_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """
        Download file from remote asset

        Args:
            remote_path: Remote file path
            local_path: Local destination path

        Returns:
            True if successful
        """
        if not self.sftp:
            logger.error("sftp_not_available")
            return False

        logger.debug(
            "downloading_file_via_sftp",
            remote=remote_path,
            local=local_path,
        )

        try:
            self.sftp.get(remote_path, local_path)
            logger.info("file_downloaded_successfully")
            return True

        except Exception as e:
            logger.error("sftp_download_failed", error=str(e))
            return False

    def test_connection(self) -> Dict[str, Any]:
        """
        Test SSH connection

        Returns:
            Connection test results
        """
        if not self.client:
            return {
                "connected": False,
                "error": "Not connected",
            }

        try:
            # Execute simple command
            result = self.execute_command("echo test", timeout=10)

            return {
                "connected": result["success"],
                "test_output": result.get("stdout", ""),
                "latency_ms": 0,  # Could measure actual latency
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
            }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class AgentConnectionManager(ConnectionManager):
    """
    Agent-based connection manager
    For future implementation with agent deployment
    """

    def __init__(self):
        super().__init__()
        self.connection_type = "agent"
        self.agent_url: Optional[str] = None

    def connect(self, asset: Dict[str, Any]) -> bool:
        """
        Connect to asset agent

        Args:
            asset: Asset information

        Returns:
            True if successful
        """
        logger.info("connecting_to_agent", asset=asset.get("name"))

        # For now, this is a placeholder
        # Future implementation would connect to agent API
        self.agent_url = asset.get("agent_url")

        if not self.agent_url:
            logger.error("agent_url_not_configured")
            return False

        return True

    def disconnect(self):
        """Close agent connection"""
        self.agent_url = None
        logger.info("agent_connection_closed")

    def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute command via agent

        Args:
            command: Command to execute

        Returns:
            Execution results
        """
        # Placeholder for agent-based execution
        logger.info("executing_command_via_agent", command=command[:50])

        # Future implementation would call agent API
        return {
            "success": False,
            "error": "Agent-based execution not yet implemented",
        }

    def copy_file(self, local_path: str, remote_path: str) -> bool:
        """Copy file via agent"""
        logger.info("copying_file_via_agent")

        # Future implementation
        return False


def get_connection_manager(
    connection_type: str = "ssh",
) -> ConnectionManager:
    """
    Get connection manager instance

    Args:
        connection_type: Type of connection (ssh, agent)

    Returns:
        ConnectionManager instance
    """
    managers = {
        "ssh": SSHConnectionManager,
        "agent": AgentConnectionManager,
    }

    manager_class = managers.get(connection_type)
    if not manager_class:
        raise ValueError(f"Unknown connection type: {connection_type}")

    return manager_class()
