"""
Tests for rollback manager
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.monitoring.rollback_manager import RollbackManager


@pytest.fixture
def manager():
    """Create rollback manager"""
    return RollbackManager()


@pytest.fixture
def sample_assets():
    """Sample assets"""
    return [
        {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"},
        {"id": 2, "name": "web-02", "ip_address": "192.168.1.101"},
    ]


def test_add_rollback_rule(manager):
    """Test adding rollback rule"""
    rule = {
        "name": "test_rule",
        "threshold": 5,
        "severity": "medium",
    }

    manager.add_rollback_rule(rule)

    assert any(r["name"] == "test_rule" for r in manager.rollback_rules)


def test_remove_rollback_rule(manager):
    """Test removing rollback rule"""
    initial_count = len(manager.rollback_rules)

    # Add and remove a rule
    manager.add_rollback_rule({"name": "test_rule", "threshold": 5})
    manager.remove_rollback_rule("test_rule")

    assert len(manager.rollback_rules) == initial_count


def test_check_rollback_triggers_no_trigger(manager):
    """Test rollback triggers when everything is healthy"""
    health_results = {
        "asset_1": {"healthy": True},
        "asset_2": {"healthy": True},
    }

    should_rollback = manager.check_rollback_triggers(
        deployment_id=1,
        health_results=health_results,
        metrics={},
    )

    assert should_rollback is False


def test_check_rollback_triggers_consecutive_failures(manager):
    """Test rollback trigger for consecutive failures"""
    health_results = {
        "asset_1": {"healthy": False},
    }

    # Simulate 3 consecutive failures
    for _ in range(3):
        manager.check_rollback_triggers(
            deployment_id=1,
            health_results=health_results,
            metrics={},
        )

    # Fourth check should trigger rollback
    should_rollback = manager.check_rollback_triggers(
        deployment_id=1,
        health_results=health_results,
        metrics={},
    )

    assert should_rollback is True


def test_check_rollback_triggers_high_failure_rate(manager):
    """Test rollback trigger for high failure rate"""
    health_results = {
        "asset_1": {"healthy": False},
        "asset_2": {"healthy": False},
        "asset_3": {"healthy": True},
        "asset_4": {"healthy": True},
    }

    should_rollback = manager.check_rollback_triggers(
        deployment_id=1,
        health_results=health_results,
        metrics={},
    )

    # 50% failure rate should trigger rollback
    assert should_rollback is True


def test_check_rollback_triggers_high_cpu(manager):
    """Test rollback trigger for high CPU usage"""
    health_results = {
        "asset_1": {"healthy": True},
    }

    metrics = {
        "asset_1": {"cpu_usage": 95.0},  # Above threshold
    }

    should_rollback = manager.check_rollback_triggers(
        deployment_id=1,
        health_results=health_results,
        metrics=metrics,
    )

    assert should_rollback is True


def test_check_rollback_triggers_high_memory(manager):
    """Test rollback trigger for high memory usage"""
    health_results = {
        "asset_1": {"healthy": True},
    }

    metrics = {
        "asset_1": {"memory_usage": 92.0},  # Above threshold
    }

    should_rollback = manager.check_rollback_triggers(
        deployment_id=1,
        health_results=health_results,
        metrics=metrics,
    )

    assert should_rollback is True


@pytest.mark.asyncio
async def test_execute_rollback(manager, sample_assets):
    """Test executing rollback"""
    rollback_script = "#!/bin/bash\necho rollback"

    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": True,
            "exit_code": 0,
            "stdout": "Rolled back",
        }
        mock_get_mgr.return_value = mock_mgr

        result = await manager.execute_rollback(
            deployment_id=1,
            assets=sample_assets,
            rollback_script=rollback_script,
            reason="test_rollback",
        )

        assert result["success"] is True
        assert result["successful_rollbacks"] == 2
        assert result["failed_rollbacks"] == 0


@pytest.mark.asyncio
async def test_execute_rollback_partial_failure(manager, sample_assets):
    """Test executing rollback with partial failures"""
    rollback_script = "#!/bin/bash\necho rollback"

    call_count = [0]

    def mock_execute(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"success": True, "exit_code": 0}
        return {"success": False, "exit_code": 1, "stderr": "Failed"}

    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.side_effect = mock_execute
        mock_get_mgr.return_value = mock_mgr

        result = await manager.execute_rollback(
            deployment_id=1,
            assets=sample_assets,
            rollback_script=rollback_script,
            reason="test_rollback",
        )

        assert result["successful_rollbacks"] == 1
        assert result["failed_rollbacks"] == 1


@pytest.mark.asyncio
async def test_rollback_single_asset(manager):
    """Test rolling back single asset"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}
    rollback_script = "#!/bin/bash\necho rollback"

    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": True,
            "exit_code": 0,
            "stdout": "Success",
        }
        mock_get_mgr.return_value = mock_mgr

        result = await manager._rollback_single_asset(asset, rollback_script)

        assert result["success"] is True


@pytest.mark.asyncio
async def test_rollback_single_asset_connection_failure(manager):
    """Test rolling back with connection failure"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}
    rollback_script = "#!/bin/bash\necho rollback"

    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = False
        mock_get_mgr.return_value = mock_mgr

        result = await manager._rollback_single_asset(asset, rollback_script)

        assert result["success"] is False
        assert "connect" in result["error"].lower()


def test_get_rollback_history(manager):
    """Test getting rollback history"""
    # Add some rollback records
    manager.rollback_history.append({
        "rollback_id": 1,
        "deployment_id": 1,
        "timestamp": "2024-01-01T00:00:00",
    })

    history = manager.get_rollback_history(deployment_id=1)

    assert len(history) == 1
    assert history[0]["deployment_id"] == 1


def test_get_rollback_history_all_deployments(manager):
    """Test getting rollback history for all deployments"""
    manager.rollback_history.append({
        "rollback_id": 1,
        "deployment_id": 1,
        "timestamp": "2024-01-01T00:00:00",
    })
    manager.rollback_history.append({
        "rollback_id": 2,
        "deployment_id": 2,
        "timestamp": "2024-01-01T01:00:00",
    })

    history = manager.get_rollback_history()

    assert len(history) == 2


def test_clear_old_rollbacks(manager):
    """Test clearing old rollback history"""
    from datetime import datetime, timedelta

    # Add old and recent rollbacks
    old_time = (datetime.utcnow() - timedelta(days=40)).isoformat()
    recent_time = datetime.utcnow().isoformat()

    manager.rollback_history.append({
        "rollback_id": 1,
        "timestamp": old_time,
    })
    manager.rollback_history.append({
        "rollback_id": 2,
        "timestamp": recent_time,
    })

    cleared = manager.clear_old_rollbacks(days=30)

    assert cleared == 1
    assert len(manager.rollback_history) == 1


def test_reset_failure_tracking(manager):
    """Test resetting failure tracking"""
    manager.failure_tracking[1] = {"consecutive_failures": 5}

    manager.reset_failure_tracking(deployment_id=1)

    assert manager.failure_tracking[1]["consecutive_failures"] == 0


def test_get_trigger_status(manager):
    """Test getting trigger status"""
    manager.failure_tracking[1] = {
        "consecutive_failures": 2,
        "total_checks": 5,
    }

    status = manager.get_trigger_status(deployment_id=1)

    assert status["deployment_id"] == 1
    assert status["consecutive_failures"] == 2
    assert status["total_checks"] == 5


def test_get_trigger_status_not_found(manager):
    """Test getting trigger status for non-existent deployment"""
    status = manager.get_trigger_status(deployment_id=999)

    assert status["deployment_id"] == 999
    assert status["consecutive_failures"] == 0
