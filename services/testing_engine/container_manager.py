"""
Docker container manager for creating isolated test environments
"""

from typing import Dict, Any, Optional, List
import asyncio
import docker
from docker.models.containers import Container
from docker.errors import DockerException, NotFound, APIError
import structlog

logger = structlog.get_logger()


class ContainerManager:
    """
    Manages Docker containers for testing patches in isolated environments
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize container manager

        Args:
            base_url: Docker daemon URL (None for default)
        """
        try:
            self.client = docker.DockerClient(base_url=base_url) if base_url else docker.from_env()
            self.client.ping()
            logger.info("docker_client_initialized")
        except DockerException as e:
            logger.error("docker_initialization_failed", error=str(e))
            raise

    def create_test_environment(
        self,
        os_type: str,
        os_version: str,
        container_name: Optional[str] = None,
        network_mode: str = "bridge",
        environment: Optional[Dict[str, str]] = None,
    ) -> Container:
        """
        Create a test environment container

        Args:
            os_type: Operating system type (ubuntu, debian, centos, etc.)
            os_version: OS version
            container_name: Optional container name
            network_mode: Docker network mode
            environment: Environment variables

        Returns:
            Docker container instance
        """
        # Map OS types to Docker images
        image_map = {
            "ubuntu": f"ubuntu:{os_version}",
            "debian": f"debian:{os_version}",
            "centos": f"centos:{os_version}" if os_version != "8" else "centos:centos8",
            "rhel": f"redhat/ubi8:{os_version}" if os_version.startswith("8") else f"redhat/ubi9:{os_version}",
            "fedora": f"fedora:{os_version}",
            "opensuse": f"opensuse/leap:{os_version}",
            "alpine": f"alpine:{os_version}",
        }

        image_name = image_map.get(os_type.lower(), f"{os_type}:{os_version}")

        logger.info(
            "creating_test_environment",
            os_type=os_type,
            os_version=os_version,
            image=image_name,
        )

        try:
            # Pull image if not available
            try:
                self.client.images.get(image_name)
            except NotFound:
                logger.info("pulling_image", image=image_name)
                self.client.images.pull(image_name)

            # Create container
            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                detach=True,
                network_mode=network_mode,
                environment=environment or {},
                # Run in privileged mode to allow package installations
                privileged=True,
                # Keep container running
                command="/bin/bash -c 'while true; do sleep 3600; done'",
                # Auto-remove on stop
                auto_remove=False,
            )

            # Start container
            container.start()

            logger.info(
                "test_environment_created",
                container_id=container.id,
                name=container_name,
            )

            return container

        except APIError as e:
            logger.error(
                "container_creation_failed",
                error=str(e),
                os_type=os_type,
            )
            raise

    def execute_command(
        self,
        container: Container,
        command: str,
        workdir: str = "/",
        environment: Optional[Dict[str, str]] = None,
        user: str = "root",
    ) -> Dict[str, Any]:
        """
        Execute a command in a container

        Args:
            container: Docker container
            command: Command to execute
            workdir: Working directory
            environment: Environment variables
            user: User to run command as

        Returns:
            Dictionary with exit_code, stdout, stderr
        """
        logger.debug(
            "executing_command",
            container_id=container.id,
            command=command[:100],  # Truncate long commands
        )

        try:
            exec_result = container.exec_run(
                cmd=command,
                workdir=workdir,
                environment=environment,
                user=user,
                privileged=True,
                demux=True,  # Separate stdout and stderr
            )

            stdout = exec_result.output[0].decode('utf-8') if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode('utf-8') if exec_result.output[1] else ""

            result = {
                "exit_code": exec_result.exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "success": exec_result.exit_code == 0,
            }

            logger.debug(
                "command_executed",
                container_id=container.id,
                exit_code=exec_result.exit_code,
            )

            return result

        except APIError as e:
            logger.error(
                "command_execution_failed",
                error=str(e),
                container_id=container.id,
            )
            raise

    def copy_file_to_container(
        self,
        container: Container,
        local_path: str,
        container_path: str,
    ) -> bool:
        """
        Copy a file to container

        Args:
            container: Docker container
            local_path: Local file path
            container_path: Destination path in container

        Returns:
            True if successful
        """
        import tarfile
        import io
        import os

        logger.debug(
            "copying_file_to_container",
            container_id=container.id,
            local_path=local_path,
            container_path=container_path,
        )

        try:
            # Create tar archive in memory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar.add(local_path, arcname=os.path.basename(local_path))

            tar_stream.seek(0)

            # Put archive in container
            container.put_archive(
                path=os.path.dirname(container_path),
                data=tar_stream,
            )

            logger.info("file_copied_to_container", container_id=container.id)
            return True

        except Exception as e:
            logger.error(
                "file_copy_failed",
                error=str(e),
                container_id=container.id,
            )
            return False

    def copy_content_to_container(
        self,
        container: Container,
        content: str,
        container_path: str,
    ) -> bool:
        """
        Copy content (as a file) to container

        Args:
            container: Docker container
            content: File content
            container_path: Destination path in container

        Returns:
            True if successful
        """
        import tarfile
        import io
        import os

        logger.debug(
            "copying_content_to_container",
            container_id=container.id,
            container_path=container_path,
        )

        try:
            # Create tar archive with content
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                file_data = content.encode('utf-8')
                tarinfo = tarfile.TarInfo(name=os.path.basename(container_path))
                tarinfo.size = len(file_data)
                tarinfo.mode = 0o755  # Executable
                tar.addfile(tarinfo, io.BytesIO(file_data))

            tar_stream.seek(0)

            # Put archive in container
            container.put_archive(
                path=os.path.dirname(container_path),
                data=tar_stream,
            )

            logger.info("content_copied_to_container", container_id=container.id)
            return True

        except Exception as e:
            logger.error(
                "content_copy_failed",
                error=str(e),
                container_id=container.id,
            )
            return False

    def get_container_logs(
        self,
        container: Container,
        tail: int = 100,
    ) -> str:
        """
        Get container logs

        Args:
            container: Docker container
            tail: Number of lines to retrieve

        Returns:
            Log output
        """
        try:
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode('utf-8')
        except Exception as e:
            logger.error("failed_to_get_logs", error=str(e))
            return ""

    def stop_container(self, container: Container, timeout: int = 10) -> bool:
        """
        Stop a container

        Args:
            container: Docker container
            timeout: Timeout in seconds

        Returns:
            True if successful
        """
        logger.info("stopping_container", container_id=container.id)

        try:
            container.stop(timeout=timeout)
            logger.info("container_stopped", container_id=container.id)
            return True
        except APIError as e:
            logger.error("container_stop_failed", error=str(e))
            return False

    def remove_container(
        self,
        container: Container,
        force: bool = False,
    ) -> bool:
        """
        Remove a container

        Args:
            container: Docker container
            force: Force removal even if running

        Returns:
            True if successful
        """
        logger.info("removing_container", container_id=container.id)

        try:
            container.remove(force=force, v=True)  # Also remove volumes
            logger.info("container_removed", container_id=container.id)
            return True
        except APIError as e:
            logger.error("container_removal_failed", error=str(e))
            return False

    def cleanup_container(self, container: Container) -> bool:
        """
        Stop and remove a container

        Args:
            container: Docker container

        Returns:
            True if successful
        """
        logger.info("cleaning_up_container", container_id=container.id)

        try:
            # Stop first
            try:
                container.stop(timeout=5)
            except:
                pass  # May already be stopped

            # Remove
            container.remove(force=True, v=True)
            logger.info("container_cleaned_up", container_id=container.id)
            return True

        except Exception as e:
            logger.error("container_cleanup_failed", error=str(e))
            return False

    def get_container_info(self, container: Container) -> Dict[str, Any]:
        """
        Get container information

        Args:
            container: Docker container

        Returns:
            Container info dictionary
        """
        try:
            container.reload()  # Refresh container state
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs.get("Created"),
                "state": container.attrs.get("State", {}),
            }
        except Exception as e:
            logger.error("failed_to_get_container_info", error=str(e))
            return {}

    def list_containers(
        self,
        all: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Container]:
        """
        List containers

        Args:
            all: Include stopped containers
            filters: Filter criteria

        Returns:
            List of containers
        """
        try:
            return self.client.containers.list(all=all, filters=filters)
        except APIError as e:
            logger.error("failed_to_list_containers", error=str(e))
            return []

    async def wait_for_container_ready(
        self,
        container: Container,
        timeout: int = 30,
    ) -> bool:
        """
        Wait for container to be ready

        Args:
            container: Docker container
            timeout: Timeout in seconds

        Returns:
            True if ready
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                container.reload()
                if container.status == "running":
                    # Additional check - try to execute a simple command
                    result = self.execute_command(container, "echo ready")
                    if result["success"]:
                        logger.info("container_ready", container_id=container.id)
                        return True

            except Exception as e:
                logger.debug("container_not_ready_yet", error=str(e))

            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.error("container_ready_timeout", container_id=container.id)
                return False

            await asyncio.sleep(1)

    def create_snapshot(self, container: Container) -> str:
        """
        Create a snapshot (image) of container state

        Args:
            container: Docker container

        Returns:
            Image ID
        """
        logger.info("creating_snapshot", container_id=container.id)

        try:
            image_tag = f"vulnzero-snapshot-{container.id[:12]}"
            container.commit(repository="vulnzero-snapshots", tag=image_tag)

            logger.info("snapshot_created", image_tag=image_tag)
            return image_tag

        except APIError as e:
            logger.error("snapshot_creation_failed", error=str(e))
            raise

    def restore_from_snapshot(
        self,
        snapshot_tag: str,
        container_name: Optional[str] = None,
    ) -> Container:
        """
        Restore container from snapshot

        Args:
            snapshot_tag: Snapshot image tag
            container_name: Name for new container

        Returns:
            New container instance
        """
        logger.info("restoring_from_snapshot", snapshot_tag=snapshot_tag)

        try:
            image_name = f"vulnzero-snapshots:{snapshot_tag}"

            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                detach=True,
                privileged=True,
                command="/bin/bash -c 'while true; do sleep 3600; done'",
            )

            container.start()

            logger.info("restored_from_snapshot", container_id=container.id)
            return container

        except APIError as e:
            logger.error("snapshot_restore_failed", error=str(e))
            raise

    def __del__(self):
        """Cleanup on deletion"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
        except:
            pass
