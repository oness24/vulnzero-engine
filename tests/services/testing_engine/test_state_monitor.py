"""
Tests for system state monitor
"""

import pytest
from unittest.mock import MagicMock, Mock
from services.testing_engine.state_monitor import SystemStateMonitor
from services.testing_engine.container_manager import ContainerManager


@pytest.fixture
def mock_container_manager():
    """Mock container manager"""
    return MagicMock(spec=ContainerManager)


@pytest.fixture
def state_monitor(mock_container_manager):
    """Create state monitor with mocked container manager"""
    return SystemStateMonitor(mock_container_manager)


@pytest.fixture
def mock_container():
    """Mock Docker container"""
    container = MagicMock()
    container.id = "test123"
    return container


def test_capture_state(state_monitor, mock_container_manager, mock_container):
    """Test capturing system state"""
    # Mock command outputs
    mock_container_manager.execute_command.side_effect = [
        # Package manager detection
        {"success": True, "stdout": "apt"},
        # Package list
        {"success": True, "stdout": "nginx=1.18.0\nopenssl=1.1.1"},
        # Service list
        {"success": True, "stdout": "nginx.service loaded active running"},
        # Files
        {"success": True, "stdout": "1024 1234567890"},
        {"success": True, "stdout": "2048 1234567891"},
        {"success": True, "stdout": "512 1234567892"},
        {"success": True, "stdout": "256 1234567893"},
        # Network
        {"success": True, "stdout": "1: eth0 inet 192.168.1.100/24"},
        {"success": True, "stdout": "tcp LISTEN 0.0.0.0:80"},
        # Processes
        {"success": True, "stdout": "root 1 nginx\nroot 2 bash"},
        # OS release
        {"success": True, "stdout": 'ID=ubuntu\nVERSION_ID="22.04"'},
        # Kernel
        {"success": True, "stdout": "5.15.0-generic"},
        # Memory
        {"success": True, "stdout": "Mem: 2048 1024 512"},
    ]

    state = state_monitor.capture_state(mock_container)

    assert "timestamp" in state
    assert "packages" in state
    assert "services" in state
    assert "system_info" in state


def test_detect_package_manager_apt(state_monitor, mock_container_manager, mock_container):
    """Test detecting APT package manager"""
    mock_container_manager.execute_command.return_value = {
        "success": True,
        "stdout": "apt",
    }

    pm = state_monitor._detect_package_manager(mock_container)

    assert pm == "apt"


def test_detect_package_manager_yum(state_monitor, mock_container_manager, mock_container):
    """Test detecting YUM package manager"""
    mock_container_manager.execute_command.side_effect = [
        {"success": True, "stdout": ""},  # apt not found
        {"success": True, "stdout": ""},  # dnf not found
        {"success": True, "stdout": "yum"},  # yum found
    ]

    pm = state_monitor._detect_package_manager(mock_container)

    assert pm == "yum"


def test_capture_package_state_apt(state_monitor, mock_container_manager, mock_container):
    """Test capturing package state with APT"""
    mock_container_manager.execute_command.side_effect = [
        # Detect apt
        {"success": True, "stdout": "apt"},
        # Get packages
        {"success": True, "stdout": "nginx=1.18.0-1\nopenssl=1.1.1k-1"},
    ]

    packages = state_monitor._capture_package_state(mock_container)

    assert "nginx" in packages
    assert packages["nginx"] == "1.18.0-1"


def test_capture_service_state(state_monitor, mock_container_manager, mock_container):
    """Test capturing service state"""
    mock_container_manager.execute_command.return_value = {
        "success": True,
        "stdout": "nginx.service loaded active running\napache2.service loaded active running",
    }

    services = state_monitor._capture_service_state(mock_container)

    assert "nginx" in services
    assert services["nginx"] == "running"


def test_compare_states(state_monitor):
    """Test comparing two system states"""
    before_state = {
        "packages": {
            "nginx": "1.18.0-0",
            "openssl": "1.1.1k-1",
        },
        "services": {
            "nginx": "running",
        },
        "files": {
            "/etc/passwd": {"size": "1024", "mtime": "1234567890"},
        },
        "network": {
            "interfaces": {"eth0": ["192.168.1.100"]},
        },
    }

    after_state = {
        "packages": {
            "nginx": "1.18.0-1",  # Updated
            "openssl": "1.1.1k-1",
            "curl": "7.68.0-1",  # Added
        },
        "services": {
            "nginx": "running",
            "apache2": "running",  # Started
        },
        "files": {
            "/etc/passwd": {"size": "1024", "mtime": "1234567890"},
        },
        "network": {
            "interfaces": {"eth0": ["192.168.1.100"]},
        },
    }

    differences = state_monitor.compare_states(before_state, after_state)

    assert differences["has_changes"] is True

    # Check package changes
    pkg_changes = differences["packages_changed"]
    assert len(pkg_changes["updated"]) == 1
    assert pkg_changes["updated"][0]["package"] == "nginx"
    assert len(pkg_changes["added"]) == 1
    assert pkg_changes["added"][0]["package"] == "curl"

    # Check service changes
    svc_changes = differences["services_changed"]
    assert len(svc_changes["started"]) == 1
    assert "apache2" in svc_changes["started"]


def test_compare_packages(state_monitor):
    """Test comparing package states"""
    before = {
        "nginx": "1.18.0-0",
        "openssl": "1.1.1k-1",
        "removed-pkg": "1.0.0",
    }

    after = {
        "nginx": "1.18.0-1",
        "openssl": "1.1.1k-1",
        "new-pkg": "2.0.0",
    }

    result = state_monitor._compare_packages(before, after)

    # Updated
    assert len(result["updated"]) == 1
    assert result["updated"][0]["package"] == "nginx"

    # Added
    assert len(result["added"]) == 1
    assert result["added"][0]["package"] == "new-pkg"

    # Removed
    assert len(result["removed"]) == 1
    assert result["removed"][0]["package"] == "removed-pkg"


def test_compare_services(state_monitor):
    """Test comparing service states"""
    before = {
        "nginx": "running",
        "stopped-service": "running",
    }

    after = {
        "nginx": "running",
        "new-service": "running",
    }

    result = state_monitor._compare_services(before, after)

    assert "new-service" in result["started"]
    assert "stopped-service" in result["stopped"]


def test_generate_state_report(state_monitor):
    """Test generating state report"""
    state = {
        "timestamp": "2024-01-01T00:00:00Z",
        "packages": {"nginx": "1.18.0", "openssl": "1.1.1k"},
        "services": {"nginx": "running", "apache2": "running"},
        "system_info": {"ID": "ubuntu", "VERSION_ID": "22.04"},
    }

    differences = {
        "packages_changed": {
            "updated": [{"package": "nginx", "before_version": "1.18.0-0", "after_version": "1.18.0-1"}],
            "added": [],
            "removed": [],
        },
        "services_changed": {
            "started": ["apache2"],
            "stopped": [],
        },
    }

    report = state_monitor.generate_state_report(state, differences)

    assert "SYSTEM STATE REPORT" in report
    assert "ubuntu" in report
    assert "nginx" in report
    assert "Updated Packages" in report


def test_capture_state_with_specific_packages(state_monitor, mock_container_manager, mock_container):
    """Test capturing state for specific packages"""
    mock_container_manager.execute_command.side_effect = [
        # Detect apt
        {"success": True, "stdout": "apt"},
        # nginx version
        {"success": True, "stdout": "1.18.0-1"},
        # openssl version
        {"success": True, "stdout": "1.1.1k-1"},
        # Other capture commands...
        {"success": True, "stdout": ""},
        {"success": True, "stdout": "1024 123"},
        {"success": True, "stdout": "2048 124"},
        {"success": True, "stdout": "512 125"},
        {"success": True, "stdout": "256 126"},
        {"success": True, "stdout": ""},
        {"success": True, "stdout": ""},
        {"success": True, "stdout": ""},
        {"success": True, "stdout": "ID=ubuntu"},
        {"success": True, "stdout": "5.15.0"},
        {"success": True, "stdout": "Mem: 2048"},
    ]

    state = state_monitor.capture_state(
        mock_container,
        packages=["nginx", "openssl"],
    )

    assert "nginx" in state["packages"]
    assert "openssl" in state["packages"]


def test_compare_states_no_changes(state_monitor):
    """Test comparing states with no changes"""
    state = {
        "packages": {"nginx": "1.18.0"},
        "services": {"nginx": "running"},
        "files": {"/etc/passwd": {"size": "1024", "mtime": "123"}},
        "network": {"interfaces": {"eth0": ["192.168.1.100"]}},
    }

    differences = state_monitor.compare_states(state, state)

    assert differences["has_changes"] is False
    assert len(differences["packages_changed"]["updated"]) == 0
