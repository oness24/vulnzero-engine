"""
Mock objects for testing

Provides reusable mock objects for common testing scenarios
"""

from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any, Optional


class MockContainerManager:
    """Mock container manager for testing"""

    def __init__(self):
        self.create_test_environment = AsyncMock(return_value={
            "success": True,
            "container_id": "test-container-123",
            "ip_address": "172.17.0.2",
        })

        self.execute_command = AsyncMock(return_value={
            "success": True,
            "exit_code": 0,
            "stdout": "Command executed successfully",
            "stderr": "",
        })

        self.create_snapshot = AsyncMock(return_value={
            "success": True,
            "snapshot_id": "snap-123",
        })

        self.restore_from_snapshot = AsyncMock(return_value={
            "success": True,
        })

        self.cleanup = AsyncMock()

    def set_execute_result(self, exit_code: int = 0, stdout: str = "", stderr: str = ""):
        """Set custom execution result"""
        self.execute_command.return_value = {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }


class MockConnectionManager:
    """Mock SSH connection manager for testing"""

    def __init__(self):
        self.connect = MagicMock(return_value=True)
        self.disconnect = MagicMock()
        self.execute_command = MagicMock(return_value={
            "success": True,
            "exit_code": 0,
            "stdout": "Success",
            "stderr": "",
        })
        self.copy_content = MagicMock(return_value=True)
        self.test_connection = MagicMock(return_value={"connected": True})

    def set_connection_failure(self):
        """Simulate connection failure"""
        self.connect.return_value = False

    def set_command_failure(self, exit_code: int = 1, stderr: str = "Error"):
        """Simulate command execution failure"""
        self.execute_command.return_value = {
            "success": False,
            "exit_code": exit_code,
            "stdout": "",
            "stderr": stderr,
        }


class MockDeploymentExecutor:
    """Mock deployment executor for testing"""

    def __init__(self):
        self.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 1,
            "successful": 1,
            "failed": 0,
            "assets": [{"id": 1, "status": "success"}],
        })

        self.rollback_deployment = AsyncMock(return_value={
            "success": True,
            "successful_rollbacks": 1,
            "failed_rollbacks": 0,
        })

        self.verify_deployment = AsyncMock(return_value={
            "all_verified": True,
            "verified": 1,
            "failed": 0,
        })

    def set_deployment_failure(self, failed_count: int = 1):
        """Simulate deployment failure"""
        total = self.deploy_patch.return_value["total_assets"]
        self.deploy_patch.return_value = {
            "success": False,
            "total_assets": total,
            "successful": total - failed_count,
            "failed": failed_count,
            "assets": [
                {"id": i, "status": "failed" if i < failed_count else "success"}
                for i in range(total)
            ],
        }


class MockPatchGenerator:
    """Mock patch generator for testing"""

    def __init__(self):
        self.generate_patch = MagicMock(return_value={
            "patch_script": "#!/bin/bash\napt-get update",
            "rollback_script": "#!/bin/bash\necho rollback",
            "validation_script": "#!/bin/bash\necho validate",
            "confidence_score": 0.92,
        })

    def set_low_confidence(self, score: float = 0.5):
        """Set low confidence score"""
        result = self.generate_patch.return_value.copy()
        result["confidence_score"] = score
        self.generate_patch.return_value = result


class MockVulnerabilityAggregator:
    """Mock vulnerability aggregator for testing"""

    def __init__(self):
        self.fetch_from_nvd = AsyncMock(return_value=[
            {
                "cve_id": "CVE-2024-0001",
                "title": "Test Vulnerability",
                "description": "Test description",
                "severity": "high",
                "cvss_score": 7.5,
                "affected_systems": ["Ubuntu 22.04"],
            }
        ])

        self.fetch_from_osv = AsyncMock(return_value=[])
        self.fetch_from_github = AsyncMock(return_value=[])

    def set_empty_results(self):
        """Return empty results"""
        self.fetch_from_nvd.return_value = []


class MockMLPrioritizer:
    """Mock ML prioritizer for testing"""

    def __init__(self):
        self.calculate_priority = MagicMock(return_value=75.5)
        self.predict_exploitability = MagicMock(return_value=0.8)

    def set_priority(self, score: float):
        """Set custom priority score"""
        self.calculate_priority.return_value = score


class MockAlertManager:
    """Mock alert manager for testing"""

    def __init__(self):
        self.create_alert = MagicMock(return_value={
            "id": 1,
            "title": "Test Alert",
            "message": "Test message",
            "severity": "warning",
            "acknowledged": False,
            "resolved": False,
        })

        self.acknowledge_alert = MagicMock(return_value=True)
        self.resolve_alert = MagicMock(return_value=True)
        self.get_active_alerts = MagicMock(return_value=[])


class MockDeploymentMonitor:
    """Mock deployment monitor for testing"""

    def __init__(self):
        self.check_deployment_health = AsyncMock(return_value={
            "deployment_id": 1,
            "total_assets": 1,
            "healthy_assets": 1,
            "unhealthy_assets": 0,
            "asset_health": {},
        })

        self.collect_metrics = AsyncMock(return_value={
            "success": True,
            "metrics": {
                "cpu_usage": 25.5,
                "memory_usage": 60.0,
                "disk_usage": 45.0,
            },
        })

        self.monitor_deployment = AsyncMock(return_value={
            "all_healthy": True,
            "total_checks": 5,
            "failed_checks": 0,
        })

    def set_unhealthy(self, unhealthy_count: int = 1):
        """Simulate unhealthy assets"""
        total = self.check_deployment_health.return_value["total_assets"]
        self.check_deployment_health.return_value = {
            "deployment_id": 1,
            "total_assets": total,
            "healthy_assets": total - unhealthy_count,
            "unhealthy_assets": unhealthy_count,
            "asset_health": {},
        }


def create_mock_db_session():
    """Create a mock database session"""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.delete = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock()
    return mock_session
