"""
Tests for deployment executor
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from services.deployment_engine.executor import DeploymentExecutor


@pytest.fixture
def executor():
    """Create deployment executor"""
    return DeploymentExecutor(use_ansible=False)


@pytest.fixture
def sample_patch():
    """Sample patch data"""
    return {
        "id": 1,
        "patch_script": "#!/bin/bash\napt-get install -y nginx",
        "rollback_script": "#!/bin/bash\napt-get remove -y nginx",
        "validation_script": "#!/bin/bash\necho test",
    }


@pytest.fixture
def sample_assets():
    """Sample assets"""
    return [
        {"name": "web-01", "ip_address": "192.168.1.100", "ssh_user": "ubuntu"},
        {"name": "web-02", "ip_address": "192.168.1.101", "ssh_user": "ubuntu"},
    ]


@pytest.mark.asyncio
async def test_deploy_patch_with_ssh(executor, sample_patch, sample_assets):
    """Test deploying patch with SSH"""
    with patch.object(executor, '_deploy_with_ssh') as mock_deploy:
        mock_deploy.return_value = {"success": True}

        result = await executor.deploy_patch(
            sample_patch,
            sample_assets,
            strategy="rolling",
            strategy_options={"batch_size": 1, "wait_between_batches": 0},
        )

        assert "successful" in result
        assert result["total_assets"] == 2


@pytest.mark.asyncio
async def test_deploy_with_ssh_success(executor, sample_patch):
    """Test SSH deployment success"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.deployment_engine.executor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": True,
            "exit_code": 0,
            "stdout": "Success",
            "stderr": "",
        }
        mock_get_mgr.return_value = mock_mgr

        result = await executor._deploy_with_ssh(asset, sample_patch)

        assert result["success"] is True
        mock_mgr.connect.assert_called_once()
        mock_mgr.disconnect.assert_called()


@pytest.mark.asyncio
async def test_deploy_with_ssh_connection_failure(executor, sample_patch):
    """Test SSH deployment with connection failure"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.deployment_engine.executor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = False
        mock_get_mgr.return_value = mock_mgr

        result = await executor._deploy_with_ssh(asset, sample_patch)

        assert result["success"] is False
        assert "connect" in result["error"].lower()


@pytest.mark.asyncio
async def test_deploy_with_ssh_patch_failure(executor, sample_patch):
    """Test SSH deployment with patch execution failure"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.deployment_engine.executor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error",
        }
        mock_get_mgr.return_value = mock_mgr

        result = await executor._deploy_with_ssh(asset, sample_patch)

        assert result["success"] is False


@pytest.mark.asyncio
async def test_deploy_with_ansible(executor, sample_patch):
    """Test Ansible deployment"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.deployment_engine.executor.AnsibleRunner') as mock_runner_class:
        mock_runner = MagicMock()
        mock_runner.deploy_to_asset.return_value = {"success": True}
        mock_runner_class.return_value = mock_runner

        result = await executor._deploy_with_ansible(asset, sample_patch)

        assert result["success"] is True
        mock_runner.deploy_to_asset.assert_called_once()
        mock_runner.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_rollback_deployment(executor, sample_assets):
    """Test deployment rollback"""
    rollback_script = "#!/bin/bash\necho rollback"

    with patch.object(executor, '_execute_rollback') as mock_rollback:
        mock_rollback.return_value = {"success": True}

        result = await executor.rollback_deployment(
            deployment_id=1,
            assets=sample_assets,
            rollback_script=rollback_script,
        )

        assert result["success"] is True
        assert result["successful_rollbacks"] == 2
        assert result["failed_rollbacks"] == 0


@pytest.mark.asyncio
async def test_execute_rollback_success(executor):
    """Test executing rollback successfully"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}
    rollback_script = "#!/bin/bash\necho rollback"

    with patch('services.deployment_engine.executor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.execute_command.return_value = {"success": True}
        mock_get_mgr.return_value = mock_mgr

        result = await executor._execute_rollback(asset, rollback_script)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_verify_deployment(executor, sample_assets):
    """Test deployment verification"""
    verification_script = "#!/bin/bash\necho verify"

    with patch.object(executor, '_verify_single_asset') as mock_verify:
        mock_verify.return_value = {"success": True}

        result = await executor.verify_deployment(sample_assets, verification_script)

        assert result["verified"] == 2
        assert result["failed"] == 0
        assert result["all_verified"] is True


@pytest.mark.asyncio
async def test_verify_deployment_with_failures(executor, sample_assets):
    """Test deployment verification with failures"""
    verification_script = "#!/bin/bash\nexit 1"

    with patch.object(executor, '_verify_single_asset') as mock_verify:
        # First succeeds, second fails
        mock_verify.side_effect = [
            {"success": True},
            {"success": False, "error": "Verification failed"},
        ]

        result = await executor.verify_deployment(sample_assets, verification_script)

        assert result["verified"] == 1
        assert result["failed"] == 1
        assert result["all_verified"] is False


@pytest.mark.asyncio
async def test_verify_single_asset(executor):
    """Test verifying single asset"""
    asset = {"name": "web-01", "ip_address": "192.168.1.100"}
    verification_script = "#!/bin/bash\necho test"

    with patch('services.deployment_engine.executor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.execute_command.return_value = {"success": True}
        mock_get_mgr.return_value = mock_mgr

        result = await executor._verify_single_asset(asset, verification_script)

        assert result["success"] is True
