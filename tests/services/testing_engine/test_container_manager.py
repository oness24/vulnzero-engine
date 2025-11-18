"""
Tests for container manager
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from docker.errors import NotFound, APIError
from services.testing_engine.container_manager import ContainerManager


@pytest.fixture
def mock_docker_client():
    """Mock Docker client"""
    with patch("services.testing_engine.container_manager.docker") as mock_docker:
        mock_client = MagicMock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        yield mock_client


@pytest.fixture
def container_manager(mock_docker_client):
    """Create container manager with mocked Docker client"""
    return ContainerManager()


def test_container_manager_initialization(mock_docker_client):
    """Test container manager initialization"""
    manager = ContainerManager()

    assert manager.client is not None
    mock_docker_client.ping.assert_called_once()


def test_create_test_environment_ubuntu(container_manager, mock_docker_client):
    """Test creating Ubuntu test environment"""
    mock_container = MagicMock()
    mock_container.id = "test123"

    mock_docker_client.images.get.side_effect = NotFound("image not found")
    mock_docker_client.images.pull.return_value = None
    mock_docker_client.containers.create.return_value = mock_container

    container = container_manager.create_test_environment(
        os_type="ubuntu",
        os_version="22.04",
        container_name="test-container",
    )

    assert container == mock_container
    mock_docker_client.images.pull.assert_called_with("ubuntu:22.04")
    mock_container.start.assert_called_once()


def test_create_test_environment_centos(container_manager, mock_docker_client):
    """Test creating CentOS test environment"""
    mock_container = MagicMock()

    # Image already exists
    mock_docker_client.images.get.return_value = MagicMock()
    mock_docker_client.containers.create.return_value = mock_container

    container = container_manager.create_test_environment(
        os_type="centos",
        os_version="8",
    )

    assert container == mock_container
    # Should use centos:centos8 for version 8
    mock_docker_client.containers.create.assert_called_once()


def test_execute_command(container_manager):
    """Test executing command in container"""
    mock_container = MagicMock()
    mock_exec_result = MagicMock()
    mock_exec_result.exit_code = 0
    mock_exec_result.output = (b"stdout output", b"stderr output")

    mock_container.exec_run.return_value = mock_exec_result

    result = container_manager.execute_command(
        mock_container,
        "echo test",
    )

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert result["stdout"] == "stdout output"
    assert result["stderr"] == "stderr output"


def test_execute_command_failure(container_manager):
    """Test executing command that fails"""
    mock_container = MagicMock()
    mock_exec_result = MagicMock()
    mock_exec_result.exit_code = 1
    mock_exec_result.output = (b"", b"error message")

    mock_container.exec_run.return_value = mock_exec_result

    result = container_manager.execute_command(
        mock_container,
        "false",
    )

    assert result["success"] is False
    assert result["exit_code"] == 1
    assert "error message" in result["stderr"]


def test_copy_content_to_container(container_manager):
    """Test copying content to container"""
    mock_container = MagicMock()

    result = container_manager.copy_content_to_container(
        mock_container,
        "#!/bin/bash\necho hello",
        "/tmp/test.sh",
    )

    assert result is True
    mock_container.put_archive.assert_called_once()


def test_stop_container(container_manager):
    """Test stopping container"""
    mock_container = MagicMock()

    result = container_manager.stop_container(mock_container)

    assert result is True
    mock_container.stop.assert_called_with(timeout=10)


def test_remove_container(container_manager):
    """Test removing container"""
    mock_container = MagicMock()

    result = container_manager.remove_container(mock_container, force=True)

    assert result is True
    mock_container.remove.assert_called_with(force=True, v=True)


def test_cleanup_container(container_manager):
    """Test cleanup container"""
    mock_container = MagicMock()

    result = container_manager.cleanup_container(mock_container)

    assert result is True
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()


def test_get_container_info(container_manager):
    """Test getting container info"""
    mock_container = MagicMock()
    mock_container.id = "abc123"
    mock_container.name = "test-container"
    mock_container.status = "running"
    mock_container.image.tags = ["ubuntu:22.04"]
    mock_container.attrs = {
        "Created": "2024-01-01T00:00:00Z",
        "State": {"Running": True},
    }

    info = container_manager.get_container_info(mock_container)

    assert info["id"] == "abc123"
    assert info["name"] == "test-container"
    assert info["status"] == "running"


def test_create_snapshot(container_manager):
    """Test creating container snapshot"""
    mock_container = MagicMock()
    mock_container.id = "abc123def456"

    container_manager.create_snapshot(mock_container)

    mock_container.commit.assert_called_once()
    call_args = mock_container.commit.call_args
    assert call_args[1]["repository"] == "vulnzero-snapshots"


@pytest.mark.asyncio
async def test_wait_for_container_ready(container_manager):
    """Test waiting for container to be ready"""
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.reload.return_value = None

    # Mock execute_command to return success
    container_manager.execute_command = Mock(return_value={"success": True})

    ready = await container_manager.wait_for_container_ready(mock_container, timeout=5)

    assert ready is True


@pytest.mark.asyncio
async def test_wait_for_container_timeout(container_manager):
    """Test container ready timeout"""
    mock_container = MagicMock()
    mock_container.status = "created"  # Never becomes running

    ready = await container_manager.wait_for_container_ready(mock_container, timeout=1)

    assert ready is False


def test_list_containers(container_manager, mock_docker_client):
    """Test listing containers"""
    mock_containers = [MagicMock(), MagicMock()]
    mock_docker_client.containers.list.return_value = mock_containers

    containers = container_manager.list_containers(all=True)

    assert len(containers) == 2
    mock_docker_client.containers.list.assert_called_with(all=True, filters=None)
