"""
Tests for test runner
"""

import pytest
from unittest.mock import MagicMock, Mock
from services.testing_engine.test_runner import TestRunner
from services.testing_engine.container_manager import ContainerManager


@pytest.fixture
def mock_container_manager():
    """Mock container manager"""
    return MagicMock(spec=ContainerManager)


@pytest.fixture
def test_runner(mock_container_manager):
    """Create test runner with mocked container manager"""
    return TestRunner(mock_container_manager)


@pytest.fixture
def mock_container():
    """Mock Docker container"""
    container = MagicMock()
    container.id = "test123"
    return container


@pytest.fixture
def sample_patch_script():
    """Sample patch script"""
    return "#!/bin/bash\napt-get install -y nginx"


@pytest.fixture
def sample_rollback_script():
    """Sample rollback script"""
    return "#!/bin/bash\napt-get install -y --allow-downgrades nginx=1.18.0-0"


def test_run_comprehensive_tests_success(test_runner, mock_container, sample_patch_script, sample_rollback_script):
    """Test comprehensive tests with all passing"""
    # Mock executor methods
    test_runner.executor.execute_patch = Mock(return_value={
        "success": True,
        "patch_output": {"exit_code": 0},
        "state_changes": {"has_changes": True},
    })

    test_runner.executor.verify_patch_idempotency = Mock(return_value={
        "success": True,
        "is_idempotent": True,
    })

    test_runner.executor.test_rollback = Mock(return_value={
        "success": True,
    })

    result = test_runner.run_comprehensive_tests(
        mock_container,
        sample_patch_script,
        sample_rollback_script,
    )

    assert result["overall_success"] is True
    assert result["tests_passed"] == 3  # basic, idempotency, rollback
    assert result["tests_failed"] == 0


def test_run_comprehensive_tests_basic_failure(test_runner, mock_container, sample_patch_script, sample_rollback_script):
    """Test comprehensive tests with basic test failure"""
    # Basic test fails
    test_runner.executor.execute_patch = Mock(return_value={
        "success": False,
        "patch_output": {"exit_code": 1},
        "errors": ["Patch failed"],
    })

    result = test_runner.run_comprehensive_tests(
        mock_container,
        sample_patch_script,
        sample_rollback_script,
    )

    assert result["overall_success"] is False
    assert result["tests_failed"] >= 1
    # Should skip remaining tests after basic failure


def test_run_comprehensive_tests_with_custom_tests(test_runner, mock_container, sample_patch_script, sample_rollback_script):
    """Test comprehensive tests with custom tests"""
    test_runner.executor.execute_patch = Mock(return_value={"success": True, "patch_output": {"exit_code": 0}})
    test_runner.executor.verify_patch_idempotency = Mock(return_value={"success": True, "is_idempotent": True})
    test_runner.executor.test_rollback = Mock(return_value={"success": True})

    # Custom tests
    test_runner.executor.execute_custom_test = Mock(return_value={"success": True})

    custom_tests = [
        {"name": "connectivity_test", "script": "#!/bin/bash\nping -c 1 8.8.8.8"},
        {"name": "service_test", "script": "#!/bin/bash\nsystemctl is-active nginx"},
    ]

    result = test_runner.run_comprehensive_tests(
        mock_container,
        sample_patch_script,
        sample_rollback_script,
        custom_tests=custom_tests,
    )

    assert result["tests_passed"] >= 5  # basic + idempotency + rollback + 2 custom
    assert "custom_tests" in result["tests"]


def test_run_smoke_tests(test_runner, mock_container_manager, mock_container):
    """Test smoke tests"""
    # Mock successful smoke tests
    mock_container_manager.execute_command.side_effect = [
        # Connectivity
        {"success": True, "stdout": "64 bytes from 8.8.8.8"},
        # Package manager
        {"success": True, "stdout": "apt 2.0"},
        # Disk space
        {"success": True, "stdout": "50"},  # 50% usage
    ]

    result = test_runner.run_smoke_tests(mock_container)

    assert result["success"] is True
    assert "connectivity" in result["tests"]
    assert "package_manager" in result["tests"]
    assert "disk_space" in result["tests"]


def test_run_smoke_tests_with_services(test_runner, mock_container_manager, mock_container):
    """Test smoke tests with service checks"""
    mock_container_manager.execute_command.side_effect = [
        # Connectivity
        {"success": True, "stdout": "ping success"},
        # Package manager
        {"success": True, "stdout": "apt 2.0"},
        # Disk space
        {"success": True, "stdout": "60"},
        # nginx service
        {"success": True, "stdout": "active"},
        # apache2 service
        {"success": False, "stdout": "inactive"},
    ]

    result = test_runner.run_smoke_tests(
        mock_container,
        services_to_check=["nginx", "apache2"],
    )

    assert "services" in result["tests"]
    assert result["tests"]["services"]["nginx"]["success"] is True
    assert result["tests"]["services"]["apache2"]["success"] is False


def test_run_security_tests(test_runner, mock_container_manager, mock_container):
    """Test security tests"""
    mock_container_manager.execute_command.side_effect = [
        # No extra root users
        {"success": True, "stdout": "ok"},
        # No world-writable files
        {"success": True, "stdout": "ok"},
        # SSH config (disabled root login)
        {"success": True, "stdout": "secure"},
        # Firewall
        {"success": True, "stdout": "Chain INPUT"},
    ]

    result = test_runner.run_security_tests(mock_container)

    assert result["success"] is True
    assert "no_extra_root_users" in result["tests"]
    assert "no_world_writable_files" in result["tests"]


def test_run_security_tests_failure(test_runner, mock_container_manager, mock_container):
    """Test security tests with failures"""
    mock_container_manager.execute_command.side_effect = [
        # Extra root user found
        {"success": True, "stdout": "hackeruser"},
        # World-writable files found
        {"success": True, "stdout": "/etc/passwd"},
        # SSH permits root login
        {"success": True, "stdout": "insecure"},
        # No firewall
        {"success": True, "stdout": "no_iptables"},
    ]

    result = test_runner.run_security_tests(mock_container)

    assert result["success"] is False
    assert result["tests"]["no_extra_root_users"]["success"] is False


def test_run_performance_tests(test_runner, mock_container_manager, mock_container, sample_patch_script):
    """Test performance tests"""
    test_runner.executor.execute_patch = Mock(return_value={"success": True})

    mock_container_manager.execute_command.return_value = {
        "success": True,
        "stdout": "512 2048",  # 512MB used, 2048MB total
    }

    result = test_runner.run_performance_tests(mock_container, sample_patch_script)

    assert "execution_time_seconds" in result
    assert result["execution_time_seconds"] >= 0
    assert "memory_impact" in result


def test_generate_test_summary(test_runner):
    """Test generating test summary"""
    test_results = {
        "container_id": "abc123",
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:05:00Z",
        "overall_success": True,
        "tests_passed": 3,
        "tests_failed": 0,
        "tests": {
            "basic_execution": {
                "success": True,
                "state_changes": {"has_changes": True, "packages_changed": {"updated": [{"package": "nginx"}]}},
            },
            "idempotency": {
                "is_idempotent": True,
            },
            "rollback": {
                "success": True,
            },
        },
    }

    summary = test_runner.generate_test_summary(test_results)

    assert "PATCH TEST SUMMARY" in summary
    assert "PASSED" in summary
    assert "Tests Passed: 3" in summary
    assert "[PASS] Basic Patch Execution" in summary


def test_generate_test_summary_with_failures(test_runner):
    """Test generating summary with failures"""
    test_results = {
        "container_id": "abc123",
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:05:00Z",
        "overall_success": False,
        "tests_passed": 1,
        "tests_failed": 2,
        "tests": {
            "basic_execution": {
                "success": False,
            },
            "idempotency": {
                "is_idempotent": False,
            },
        },
    }

    summary = test_runner.generate_test_summary(test_results)

    assert "FAILED" in summary
    assert "Tests Failed: 2" in summary
