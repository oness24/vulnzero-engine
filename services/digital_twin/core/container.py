"""
Docker Container Manager

Manages Docker containers for digital twin testing environments.
"""

import docker
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ContainerManager:
    """
    Manages Docker container lifecycle for digital twin testing.
    """

    # Supported base images
    IMAGES = {
        "ubuntu-20.04": "ubuntu:20.04",
        "ubuntu-22.04": "ubuntu:22.04",
        "ubuntu-24.04": "ubuntu:24.04",
        "rhel-8": "rockylinux:8",
        "rhel-9": "rockylinux:9",
        "amazonlinux-2": "amazonlinux:2",
        "debian-11": "debian:11",
        "debian-12": "debian:12",
    }

    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            self.logger = logging.getLogger(__name__)
            self.logger.info("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def create_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        network_mode: str = "bridge",
        cpu_limit: str = "2.0",
        mem_limit: str = "4g",
        detach: bool = True,
    ) -> docker.models.containers.Container:
        """
        Create a Docker container.

        Args:
            image: Docker image name or key from IMAGES dict
            name: Container name (auto-generated if None)
            command: Command to run in container
            environment: Environment variables
            volumes: Volume mounts
            network_mode: Docker network mode
            cpu_limit: CPU limit (e.g., "2.0" for 2 cores)
            mem_limit: Memory limit (e.g., "4g" for 4GB)
            detach: Run in detached mode

        Returns:
            Docker container object
        """
        # Resolve image name
        image_name = self.IMAGES.get(image, image)

        # Generate name if not provided
        if not name:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            name = f"vulnzero-twin-{timestamp}"

        self.logger.info(f"Creating container '{name}' from image '{image_name}'")

        try:
            # Pull image if not available
            try:
                self.client.images.get(image_name)
            except docker.errors.ImageNotFound:
                self.logger.info(f"Pulling image '{image_name}'...")
                self.client.images.pull(image_name)

            # Create container
            container = self.client.containers.create(
                image=image_name,
                name=name,
                command=command or "/bin/bash",
                environment=environment or {},
                volumes=volumes or {},
                network_mode=network_mode,
                detach=detach,
                tty=True,
                stdin_open=True,
                cpu_quota=int(float(cpu_limit) * 100000),  # Convert to CPU quota
                mem_limit=mem_limit,
                labels={
                    "vulnzero.type": "digital-twin",
                    "vulnzero.created": datetime.utcnow().isoformat(),
                },
            )

            self.logger.info(f"Container '{name}' created successfully")
            return container

        except docker.errors.APIError as e:
            self.logger.error(f"Failed to create container: {e}")
            raise

    def start_container(self, container: docker.models.containers.Container) -> bool:
        """
        Start a container.

        Args:
            container: Docker container object

        Returns:
            True if started successfully
        """
        try:
            container.start()
            self.logger.info(f"Container '{container.name}' started")
            return True
        except docker.errors.APIError as e:
            self.logger.error(f"Failed to start container: {e}")
            return False

    def stop_container(
        self,
        container: docker.models.containers.Container,
        timeout: int = 10
    ) -> bool:
        """
        Stop a container.

        Args:
            container: Docker container object
            timeout: Seconds to wait before killing

        Returns:
            True if stopped successfully
        """
        try:
            container.stop(timeout=timeout)
            self.logger.info(f"Container '{container.name}' stopped")
            return True
        except docker.errors.APIError as e:
            self.logger.error(f"Failed to stop container: {e}")
            return False

    def remove_container(
        self,
        container: docker.models.containers.Container,
        force: bool = True
    ) -> bool:
        """
        Remove a container.

        Args:
            container: Docker container object
            force: Force removal even if running

        Returns:
            True if removed successfully
        """
        try:
            container.remove(force=force)
            self.logger.info(f"Container '{container.name}' removed")
            return True
        except docker.errors.APIError as e:
            self.logger.error(f"Failed to remove container: {e}")
            return False

    def execute_command(
        self,
        container: docker.models.containers.Container,
        command: str,
        workdir: Optional[str] = None,
        user: str = "root",
        environment: Optional[Dict[str, str]] = None,
    ) -> tuple[int, str, str]:
        """
        Execute a command in a container.

        Args:
            container: Docker container object
            command: Command to execute
            workdir: Working directory
            user: User to run as
            environment: Environment variables

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            exec_result = container.exec_run(
                command,
                workdir=workdir,
                user=user,
                environment=environment or {},
                demux=True,  # Separate stdout and stderr
            )

            exit_code = exec_result.exit_code
            stdout, stderr = exec_result.output

            stdout_str = stdout.decode("utf-8") if stdout else ""
            stderr_str = stderr.decode("utf-8") if stderr else ""

            return exit_code, stdout_str, stderr_str

        except docker.errors.APIError as e:
            self.logger.error(f"Failed to execute command: {e}")
            return -1, "", str(e)

    def get_container_logs(
        self,
        container: docker.models.containers.Container,
        tail: Optional[int] = None
    ) -> str:
        """
        Get container logs.

        Args:
            container: Docker container object
            tail: Number of lines from end (None for all)

        Returns:
            Container logs as string
        """
        try:
            logs = container.logs(tail=tail)
            return logs.decode("utf-8")
        except docker.errors.APIError as e:
            self.logger.error(f"Failed to get logs: {e}")
            return ""

    def cleanup_old_containers(self, max_age_hours: int = 24) -> int:
        """
        Clean up old digital twin containers.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of containers removed
        """
        removed_count = 0

        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "vulnzero.type=digital-twin"}
            )

            for container in containers:
                created_str = container.labels.get("vulnzero.created")
                if not created_str:
                    continue

                created = datetime.fromisoformat(created_str)
                age_hours = (datetime.utcnow() - created).total_seconds() / 3600

                if age_hours > max_age_hours:
                    self.logger.info(f"Removing old container '{container.name}' (age: {age_hours:.1f}h)")
                    if self.remove_container(container, force=True):
                        removed_count += 1

            return removed_count

        except docker.errors.APIError as e:
            self.logger.error(f"Failed to cleanup containers: {e}")
            return removed_count

    def list_digital_twin_containers(self) -> List[Dict[str, Any]]:
        """
        List all digital twin containers.

        Returns:
            List of container info dicts
        """
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": "vulnzero.type=digital-twin"}
            )

            return [
                {
                    "id": c.short_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "created": c.labels.get("vulnzero.created"),
                }
                for c in containers
            ]

        except docker.errors.APIError as e:
            self.logger.error(f"Failed to list containers: {e}")
            return []
