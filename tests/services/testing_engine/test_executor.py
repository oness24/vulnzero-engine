"""
Tests for patch executor
"""

import pytest
from unittest.mock import MagicMock, Mock
from services.testing_engine.executor import PatchExecutor
from services.testing_engine.container_manager import ContainerManager


@pytest.fixture
def mock_container_manager():
    """Mock container manager"""
    return MagicMock(spec=ContainerManager)


@pytest.fixture
def executor(mock_container_manager):
    """Create executor with mocked container manager"""
    return PatchExecutor(mock_container_manager)


@pytest.fixture
def mock_container():
    """Mock Docker container"""
    container = MagicMock()
    container.id = "test123"
    return container


@pytest.fixture
def sample_patch_script():
    """Sample patch script"""
    return """#!/bin/bash
set -euo pipefail
apt-get update
apt-get install -y nginx
"""


@pytest.fixture
def sample_rollback_script():
    """Sample rollback script"""
    return """#!/bin/bash
set -euo pipefail
apt-get install -y --allow-downgrades nginx=1.18.0-0
"""


def test_execute_patch_success(executor, mock_container_manager, mock_container, sample_patch_script):
    """Test successful patch execution"""
    # Mock state capture
    executor.state_monitor.capture_state = Mock(return_value={"packages": {"nginx": "1.18.0"}})

    # Mock copy operation
    mock_container_manager.copy_content_to_container.return_value = True

    # Mock patch execution
    mock_container_manager.execute_command.return_value = {
        "exit_code": 0,
        "stdout": "Patch completed successfully",
        "stderr": "",
        "success": True,
    }

    result = executor.execute_patch(
        mock_container,
        sample_patch_script,
        capture_state=True,
    )

    assert result["success"] is True
    assert result["patch_output"]["exit_code"] == 0
    assert "state_before" in result
    assert "state_after" in result


def test_execute_patch_failure(executor, mock_container_manager, mock_container, sample_patch_script):
    """Test failed patch execution"""
    executor.state_monitor.capture_state = Mock(return_value={})
    mock_container_manager.copy_content_to_container.return_value = True

    # Mock failed execution
    mock_container_manager.execute_command.return_value = {
        "exit_code": 1,
        "stdout": "",
        "stderr": "Error occurred",
        "success": False,
    }

    result = executor.execute_patch(
        mock_container,
        sample_patch_script,
    )

    assert result["success"] is False
    assert len(result["errors"]) > 0


def test_execute_patch_with_validation(executor, mock_container_manager, mock_container, sample_patch_script):
    """Test patch execution with validation script"""
    executor.state_monitor.capture_state = Mock(return_value={})
    mock_container_manager.copy_content_to_container.return_value = True

    # Mock patch execution success and validation success
    mock_container_manager.execute_command.side_effect = [
        # Patch execution
        {"exit_code": 0, "stdout": "Success", "stderr": "", "success": True},
        # Validation execution
        {"exit_code": 0, "stdout": "Validation passed", "stderr": "", "success": True},
    ]

    validation_script = "#!/bin/bash\necho 'Validation passed'"

    result = executor.execute_patch(
        mock_container,
        sample_patch_script,
        validation_script=validation_script,
        capture_state=False,
    )

    assert result["success"] is True
    assert result["validation_output"]["success"] is True


def test_execute_rollback(executor, mock_container_manager, mock_container, sample_rollback_script):
    """Test rollback execution"""
    mock_container_manager.copy_content_to_container.return_value = True

    mock_container_manager.execute_command.return_value = {
        "exit_code": 0,
        "stdout": "Rollback successful",
        "stderr": "",
        "success": True,
    }

    result = executor.execute_rollback(mock_container, sample_rollback_script)

    assert result["success"] is True
    assert result["output"]["exit_code"] == 0


def test_test_rollback(executor, mock_container_manager, mock_container, sample_patch_script, sample_rollback_script):
    """Test rollback functionality"""
    # Mock state captures
    initial_state = {"packages": {"nginx": "1.18.0-0"}}
    final_state = {"packages": {"nginx": "1.18.0-0"}}

    executor.state_monitor.capture_state = Mock(side_effect=[initial_state, final_state])

    # Mock successful patch and rollback
    executor.execute_patch = Mock(return_value={"success": True})
    executor.execute_rollback = Mock(return_value={"success": True})

    result = executor.test_rollback(
        mock_container,
        sample_patch_script,
        sample_rollback_script,
        target_package="nginx",
    )

    assert result["patch_applied"] is True
    assert result["rollback_executed"] is True
    assert result["state_restored"] is True
    assert result["success"] is True


def test_test_rollback_version_mismatch(executor, mock_container_manager, mock_container, sample_patch_script, sample_rollback_script):
    """Test rollback with version mismatch"""
    # Mock state captures with different versions
    initial_state = {"packages": {"nginx": "1.18.0-0"}}
    final_state = {"packages": {"nginx": "1.18.0-1"}}  # Different version

    executor.state_monitor.capture_state = Mock(side_effect=[initial_state, final_state])
    executor.execute_patch = Mock(return_value={"success": True})
    executor.execute_rollback = Mock(return_value={"success": True})

    result = executor.test_rollback(
        mock_container,
        sample_patch_script,
        sample_rollback_script,
        target_package="nginx",
    )

    assert result["state_restored"] is False
    assert result["success"] is False
    assert len(result["errors"]) > 0


def test_verify_patch_idempotency(executor, mock_container, sample_patch_script):
    """Test patch idempotency verification"""
    # Mock first and second executions
    first_result = {
        "success": True,
        "patch_output": {"exit_code": 0},
        "state_changes": {"has_changes": True},
    }

    second_result = {
        "success": True,
        "patch_output": {"exit_code": 0},
        "state_changes": {"has_changes": False},  # No changes on second run
    }

    executor.execute_patch = Mock(side_effect=[first_result, second_result])

    result = executor.verify_patch_idempotency(mock_container, sample_patch_script)

    assert result["success"] is True
    assert result["is_idempotent"] is True
    assert result["first_run"]["success"] is True
    assert result["second_run"]["success"] is True


def test_verify_patch_not_idempotent(executor, mock_container, sample_patch_script):
    """Test non-idempotent patch"""
    # First run succeeds, second run fails
    first_result = {
        "success": True,
        "patch_output": {"exit_code": 0},
    }

    second_result = {
        "success": False,
        "patch_output": {"exit_code": 1},
    }

    executor.execute_patch = Mock(side_effect=[first_result, second_result])

    result = executor.verify_patch_idempotency(mock_container, sample_patch_script)

    assert result["first_run"]["success"] is True
    assert result["second_run"]["success"] is False


def test_execute_custom_test(executor, mock_container_manager, mock_container):
    """Test custom test execution"""
    test_script = "#!/bin/bash\necho 'Test passed'"

    mock_container_manager.copy_content_to_container.return_value = True
    mock_container_manager.execute_command.return_value = {
        "exit_code": 0,
        "stdout": "Test passed",
        "stderr": "",
        "success": True,
    }

    result = executor.execute_custom_test(
        mock_container,
        test_script,
        test_name="connectivity_test",
    )

    assert result["success"] is True
    assert result["test_name"] == "connectivity_test"
    assert result["output"]["exit_code"] == 0


def test_execute_patch_copy_failure(executor, mock_container_manager, mock_container, sample_patch_script):
    """Test patch execution when copy fails"""
    mock_container_manager.copy_content_to_container.return_value = False

    result = executor.execute_patch(mock_container, sample_patch_script)

    assert result["success"] is False
    assert any("Failed to copy" in error for error in result["errors"])


def test_execute_rollback_copy_failure(executor, mock_container_manager, mock_container, sample_rollback_script):
    """Test rollback when copy fails"""
    mock_container_manager.copy_content_to_container.return_value = False

    result = executor.execute_rollback(mock_container, sample_rollback_script)

    assert result["success"] is False
    assert any("Failed to copy" in error for error in result["errors"])
