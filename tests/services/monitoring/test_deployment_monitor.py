"""
Tests for deployment monitor
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.monitoring.deployment_monitor import DeploymentMonitor


@pytest.fixture
def monitor():
    """Create deployment monitor"""
    return DeploymentMonitor()


@pytest.fixture
def sample_assets():
    """Sample assets for testing"""
    return [
        {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"},
        {"id": 2, "name": "web-02", "ip_address": "192.168.1.101"},
    ]


@pytest.mark.asyncio
async def test_check_asset_health_success(monitor):
    """Test checking asset health successfully"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.monitoring.deployment_monitor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": True,
            "exit_code": 0,
            "stdout": "OK",
        }
        mock_get_mgr.return_value = mock_mgr

        result = await monitor.check_asset_health(asset)

        assert result["healthy"] is True
        assert result["connected"] is True


@pytest.mark.asyncio
async def test_check_asset_health_connection_failure(monitor):
    """Test asset health check with connection failure"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.monitoring.deployment_monitor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = False
        mock_get_mgr.return_value = mock_mgr

        result = await monitor.check_asset_health(asset)

        assert result["healthy"] is False
        assert result["connected"] is False


@pytest.mark.asyncio
async def test_check_asset_health_with_custom_check(monitor):
    """Test asset health check with custom health check"""
    asset = {"id": 1, "name": "web-01"}

    async def custom_check(asset_data):
        return {"healthy": True, "custom_metric": 100}

    result = await monitor.check_asset_health(asset, health_check_func=custom_check)

    assert result["healthy"] is True
    assert result["custom_metric"] == 100


@pytest.mark.asyncio
async def test_collect_metrics_success(monitor):
    """Test collecting metrics successfully"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.monitoring.deployment_monitor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True

        # Mock metric collection commands
        mock_mgr.execute_command.side_effect = [
            {"success": True, "stdout": "10.5"},  # CPU
            {"success": True, "stdout": "50.0"},  # Memory
            {"success": True, "stdout": "75.0"},  # Disk
        ]
        mock_get_mgr.return_value = mock_mgr

        result = await monitor.collect_metrics(asset)

        assert result["success"] is True
        assert "cpu_usage" in result["metrics"]
        assert "memory_usage" in result["metrics"]
        assert "disk_usage" in result["metrics"]


@pytest.mark.asyncio
async def test_collect_metrics_connection_failure(monitor):
    """Test collecting metrics with connection failure"""
    asset = {"id": 1, "name": "web-01", "ip_address": "192.168.1.100"}

    with patch('services.monitoring.deployment_monitor.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = False
        mock_get_mgr.return_value = mock_mgr

        result = await monitor.collect_metrics(asset)

        assert result["success"] is False


@pytest.mark.asyncio
async def test_check_deployment_health(monitor, sample_assets):
    """Test checking deployment health"""
    with patch.object(monitor, 'check_asset_health') as mock_check:
        mock_check.return_value = {"healthy": True, "connected": True}

        result = await monitor.check_deployment_health(
            deployment_id=1,
            assets=sample_assets,
        )

        assert result["deployment_id"] == 1
        assert result["total_assets"] == 2
        assert result["healthy_assets"] == 2
        assert result["unhealthy_assets"] == 0


@pytest.mark.asyncio
async def test_check_deployment_health_with_failures(monitor, sample_assets):
    """Test checking deployment health with some failures"""
    with patch.object(monitor, 'check_asset_health') as mock_check:
        # First healthy, second unhealthy
        mock_check.side_effect = [
            {"healthy": True, "connected": True},
            {"healthy": False, "connected": True, "error": "Service down"},
        ]

        result = await monitor.check_deployment_health(
            deployment_id=1,
            assets=sample_assets,
        )

        assert result["healthy_assets"] == 1
        assert result["unhealthy_assets"] == 1


@pytest.mark.asyncio
async def test_monitor_deployment(monitor, sample_assets):
    """Test monitoring deployment"""
    with patch.object(monitor, 'check_deployment_health') as mock_check:
        mock_check.return_value = {
            "deployment_id": 1,
            "total_assets": 2,
            "healthy_assets": 2,
            "unhealthy_assets": 0,
            "asset_health": {},
        }

        with patch.object(monitor, 'collect_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "success": True,
                "metrics": {"cpu_usage": 10.0, "memory_usage": 50.0},
            }

            result = await monitor.monitor_deployment(
                deployment_id=1,
                assets=sample_assets,
                check_interval=1,
                max_duration=5,
            )

            assert result["deployment_id"] == 1
            assert result["total_checks"] > 0
            assert result["all_healthy"] is True


@pytest.mark.asyncio
async def test_monitor_deployment_with_failures(monitor, sample_assets):
    """Test monitoring deployment with health check failures"""
    check_count = [0]

    async def mock_check(*args, **kwargs):
        check_count[0] += 1
        # Fail after 2 checks
        if check_count[0] > 2:
            return {
                "deployment_id": 1,
                "total_assets": 2,
                "healthy_assets": 1,
                "unhealthy_assets": 1,
                "asset_health": {},
            }
        return {
            "deployment_id": 1,
            "total_assets": 2,
            "healthy_assets": 2,
            "unhealthy_assets": 0,
            "asset_health": {},
        }

    with patch.object(monitor, 'check_deployment_health', side_effect=mock_check):
        with patch.object(monitor, 'collect_metrics') as mock_metrics:
            mock_metrics.return_value = {"success": True, "metrics": {}}

            result = await monitor.monitor_deployment(
                deployment_id=1,
                assets=sample_assets,
                check_interval=1,
                max_duration=5,
            )

            assert result["failed_checks"] > 0


@pytest.mark.asyncio
async def test_start_monitoring(monitor):
    """Test starting monitoring"""
    monitor.start_monitoring(deployment_id=1)

    assert 1 in monitor.monitoring_sessions
    assert monitor.monitoring_sessions[1]["active"] is True


@pytest.mark.asyncio
async def test_stop_monitoring(monitor):
    """Test stopping monitoring"""
    monitor.start_monitoring(deployment_id=1)
    monitor.stop_monitoring(deployment_id=1)

    assert monitor.monitoring_sessions[1]["active"] is False


@pytest.mark.asyncio
async def test_get_monitoring_status(monitor):
    """Test getting monitoring status"""
    monitor.start_monitoring(deployment_id=1)

    status = monitor.get_monitoring_status(deployment_id=1)

    assert status["deployment_id"] == 1
    assert status["active"] is True


@pytest.mark.asyncio
async def test_get_monitoring_status_not_found(monitor):
    """Test getting status for non-existent monitoring session"""
    status = monitor.get_monitoring_status(deployment_id=999)

    assert status["deployment_id"] == 999
    assert status["active"] is False
