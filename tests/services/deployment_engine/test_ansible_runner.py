"""
Tests for Ansible runner
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from services.deployment_engine.ansible_runner import AnsibleRunner
import tempfile


@pytest.fixture
def ansible_runner():
    """Create Ansible runner instance"""
    return AnsibleRunner()


@pytest.fixture
def sample_asset():
    """Sample asset dictionary"""
    return {
        "name": "web-server-01",
        "ip_address": "192.168.1.100",
        "ssh_user": "ubuntu",
        "ssh_port": 22,
    }


@pytest.fixture
def sample_assets():
    """Sample list of assets"""
    return [
        {"name": "web-01", "ip_address": "192.168.1.100", "ssh_user": "ubuntu"},
        {"name": "web-02", "ip_address": "192.168.1.101", "ssh_user": "ubuntu"},
    ]


def test_create_playbook(ansible_runner):
    """Test creating Ansible playbook"""
    patch_script = "#!/bin/bash\napt-get install -y nginx"
    rollback_script = "#!/bin/bash\napt-get remove -y nginx"

    playbook_path = ansible_runner.create_playbook(
        patch_script,
        rollback_script,
    )

    assert playbook_path is not None
    assert playbook_path.endswith('.yml')
    assert playbook_path in ansible_runner.temp_files


def test_create_inventory(ansible_runner, sample_assets):
    """Test creating Ansible inventory"""
    inventory_path = ansible_runner.create_inventory(sample_assets)

    assert inventory_path is not None
    assert inventory_path.endswith('.yml')
    assert inventory_path in ansible_runner.temp_files


def test_run_playbook_success(ansible_runner):
    """Test running Ansible playbook successfully"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PLAY RECAP\nweb-01 : ok=5 changed=2",
            stderr="",
        )

        result = ansible_runner.run_playbook(
            "/tmp/test.yml",
            inventory_path="/tmp/inventory.yml",
        )

        assert result["success"] is True
        assert result["return_code"] == 0


def test_run_playbook_failure(ansible_runner):
    """Test running Ansible playbook with failure"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Connection failed",
        )

        result = ansible_runner.run_playbook("/tmp/test.yml")

        assert result["success"] is False
        assert result["return_code"] == 1


def test_run_playbook_timeout(ansible_runner):
    """Test playbook timeout"""
    with patch('subprocess.run') as mock_run:
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 600)

        result = ansible_runner.run_playbook("/tmp/test.yml")

        assert result["success"] is False
        assert "timeout" in result["error"].lower()


def test_deploy_to_asset(ansible_runner, sample_asset):
    """Test deploying to single asset"""
    patch_script = "#!/bin/bash\necho test"
    rollback_script = "#!/bin/bash\necho rollback"

    with patch.object(ansible_runner, 'create_inventory') as mock_inventory:
        with patch.object(ansible_runner, 'create_playbook') as mock_playbook:
            with patch.object(ansible_runner, 'run_playbook') as mock_run:
                mock_inventory.return_value = "/tmp/inventory.yml"
                mock_playbook.return_value = "/tmp/playbook.yml"
                mock_run.return_value = {"success": True}

                result = ansible_runner.deploy_to_asset(
                    sample_asset,
                    patch_script,
                    rollback_script,
                )

                assert result["success"] is True
                mock_inventory.assert_called_once()
                mock_playbook.assert_called_once()


def test_deploy_to_multiple_assets(ansible_runner, sample_assets):
    """Test deploying to multiple assets"""
    patch_script = "#!/bin/bash\necho test"
    rollback_script = "#!/bin/bash\necho rollback"

    with patch.object(ansible_runner, 'create_inventory') as mock_inventory:
        with patch.object(ansible_runner, 'create_playbook') as mock_playbook:
            with patch.object(ansible_runner, 'run_playbook') as mock_run:
                mock_inventory.return_value = "/tmp/inventory.yml"
                mock_playbook.return_value = "/tmp/playbook.yml"
                mock_run.return_value = {"success": True}

                result = ansible_runner.deploy_to_multiple_assets(
                    sample_assets,
                    patch_script,
                    rollback_script,
                )

                assert result["success"] is True


def test_check_connectivity(ansible_runner, sample_assets):
    """Test checking connectivity to assets"""
    with patch.object(ansible_runner, 'create_inventory'):
        with patch.object(ansible_runner, 'run_playbook') as mock_run:
            mock_run.return_value = {
                "success": True,
                "output": {
                    "stats": {
                        "web-01": {"ok": 1},
                        "web-02": {"ok": 1},
                    }
                },
            }

            connectivity = ansible_runner.check_connectivity(sample_assets)

            assert connectivity["web-01"] is True
            assert connectivity["web-02"] is True


def test_check_connectivity_failures(ansible_runner, sample_assets):
    """Test connectivity check with failures"""
    with patch.object(ansible_runner, 'create_inventory'):
        with patch.object(ansible_runner, 'run_playbook') as mock_run:
            mock_run.return_value = {
                "success": False,
            }

            connectivity = ansible_runner.check_connectivity(sample_assets)

            # All should be False when check fails
            assert connectivity["web-01"] is False
            assert connectivity["web-02"] is False


def test_cleanup(ansible_runner):
    """Test cleanup of temporary files"""
    # Create some temp files
    ansible_runner.temp_files = [
        tempfile.NamedTemporaryFile(delete=False).name,
        tempfile.NamedTemporaryFile(delete=False).name,
    ]

    ansible_runner.cleanup()

    assert len(ansible_runner.temp_files) == 0


def test_parse_ansible_output(ansible_runner):
    """Test parsing Ansible output"""
    output = """
PLAY RECAP *********************************************************************
web-01 : ok=5 changed=2 failed=0
web-02 : ok=5 changed=2 failed=0
"""

    result = ansible_runner._parse_ansible_output(output)

    assert "stats" in result
    assert "web-01" in result["stats"]
