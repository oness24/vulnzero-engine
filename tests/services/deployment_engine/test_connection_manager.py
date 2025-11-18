"""
Tests for connection manager
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from services.deployment_engine.connection_manager import (
    SSHConnectionManager,
    AgentConnectionManager,
    get_connection_manager,
)


@pytest.fixture
def sample_asset():
    """Sample asset for testing"""
    return {
        "name": "web-server-01",
        "ip_address": "192.168.1.100",
        "ssh_user": "ubuntu",
        "ssh_port": 22,
    }


@pytest.fixture
def ssh_manager():
    """Create SSH connection manager"""
    return SSHConnectionManager()


def test_ssh_connection_manager_init(ssh_manager):
    """Test SSH connection manager initialization"""
    assert ssh_manager.connection_type == "ssh"
    assert ssh_manager.client is None
    assert ssh_manager.sftp is None


def test_ssh_connect_with_password(ssh_manager, sample_asset):
    """Test SSH connection with password"""
    asset = sample_asset.copy()
    asset["ssh_password"] = "test_password"

    with patch('paramiko.SSHClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = ssh_manager.connect(asset)

        assert result is True
        mock_client.connect.assert_called_once()
        call_kwargs = mock_client.connect.call_args[1]
        assert call_kwargs["hostname"] == "192.168.1.100"
        assert call_kwargs["username"] == "ubuntu"
        assert call_kwargs["password"] == "test_password"


def test_ssh_connect_with_key(ssh_manager, sample_asset):
    """Test SSH connection with key file"""
    asset = sample_asset.copy()
    asset["ssh_key_path"] = "/path/to/key.pem"

    with patch('paramiko.SSHClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = ssh_manager.connect(asset)

        assert result is True
        call_kwargs = mock_client.connect.call_args[1]
        assert call_kwargs["key_filename"] == "/path/to/key.pem"


def test_ssh_connect_failure(ssh_manager, sample_asset):
    """Test SSH connection failure"""
    with patch('paramiko.SSHClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.connect.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_client

        result = ssh_manager.connect(sample_asset)

        assert result is False


def test_ssh_disconnect(ssh_manager):
    """Test SSH disconnect"""
    ssh_manager.client = MagicMock()
    ssh_manager.sftp = MagicMock()

    ssh_manager.disconnect()

    ssh_manager.client.close.assert_called_once()
    ssh_manager.sftp.close.assert_called_once()
    assert ssh_manager.client is None
    assert ssh_manager.sftp is None


def test_execute_command_success(ssh_manager):
    """Test executing command successfully"""
    mock_client = MagicMock()
    ssh_manager.client = mock_client

    # Mock command execution
    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b"command output"

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""

    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    result = ssh_manager.execute_command("ls -la")

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert result["stdout"] == "command output"


def test_execute_command_failure(ssh_manager):
    """Test executing command with failure"""
    mock_client = MagicMock()
    ssh_manager.client = mock_client

    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 1
    mock_stdout.read.return_value = b""

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b"error message"

    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    result = ssh_manager.execute_command("invalid_command")

    assert result["success"] is False
    assert result["exit_code"] == 1
    assert "error message" in result["stderr"]


def test_execute_command_with_sudo(ssh_manager):
    """Test executing command with sudo"""
    mock_client = MagicMock()
    ssh_manager.client = mock_client

    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b""

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""

    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    ssh_manager.execute_command("apt-get update", sudo=True)

    # Check that sudo was prepended
    call_args = mock_client.exec_command.call_args[0]
    assert call_args[0].startswith("sudo ")


def test_copy_content(ssh_manager):
    """Test copying content to remote file"""
    mock_sftp = MagicMock()
    ssh_manager.sftp = mock_sftp

    mock_file = MagicMock()
    mock_sftp.file.return_value.__enter__.return_value = mock_file

    result = ssh_manager.copy_content("test content", "/tmp/test.txt")

    assert result is True
    mock_file.write.assert_called_with("test content")
    mock_sftp.chmod.assert_called_once()


def test_copy_content_no_sftp(ssh_manager):
    """Test copying content when SFTP not available"""
    ssh_manager.sftp = None

    result = ssh_manager.copy_content("test", "/tmp/test.txt")

    assert result is False


def test_test_connection_success(ssh_manager):
    """Test connection test"""
    ssh_manager.client = MagicMock()
    ssh_manager.execute_command = Mock(return_value={
        "success": True,
        "stdout": "test",
    })

    result = ssh_manager.test_connection()

    assert result["connected"] is True


def test_context_manager(sample_asset):
    """Test using connection manager as context manager"""
    with patch('paramiko.SSHClient'):
        manager = SSHConnectionManager()

        with manager as mgr:
            assert mgr is manager

        # Should be disconnected after context exit
        assert manager.client is None


def test_agent_connection_manager():
    """Test agent connection manager"""
    manager = AgentConnectionManager()

    assert manager.connection_type == "agent"


def test_agent_connect(sample_asset):
    """Test agent connection"""
    manager = AgentConnectionManager()
    asset = sample_asset.copy()
    asset["agent_url"] = "http://agent:8080"

    result = manager.connect(asset)

    # For now, should succeed with URL
    assert result is True


def test_agent_connect_no_url(sample_asset):
    """Test agent connection without URL"""
    manager = AgentConnectionManager()

    result = manager.connect(sample_asset)

    assert result is False


def test_get_connection_manager_ssh():
    """Test getting SSH connection manager"""
    manager = get_connection_manager("ssh")

    assert isinstance(manager, SSHConnectionManager)


def test_get_connection_manager_agent():
    """Test getting agent connection manager"""
    manager = get_connection_manager("agent")

    assert isinstance(manager, AgentConnectionManager)


def test_get_connection_manager_unknown():
    """Test getting unknown connection manager"""
    with pytest.raises(ValueError):
        get_connection_manager("unknown")
