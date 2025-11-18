"""
Tests for deployment strategies
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.deployment_engine.strategies import (
    RollingDeployment,
    BlueGreenDeployment,
    CanaryDeployment,
    get_deployment_strategy,
)


@pytest.fixture
def sample_assets():
    """Sample assets"""
    return [
        {"name": "web-01", "ip_address": "192.168.1.100"},
        {"name": "web-02", "ip_address": "192.168.1.101"},
        {"name": "web-03", "ip_address": "192.168.1.102"},
        {"name": "web-04", "ip_address": "192.168.1.103"},
    ]


@pytest.mark.asyncio
async def test_rolling_deployment_success(sample_assets):
    """Test successful rolling deployment"""
    strategy = RollingDeployment(batch_size=2, wait_between_batches=0)

    # Mock deployment function
    async def mock_deploy(asset, **kwargs):
        return {"success": True, "asset": asset["name"]}

    result = await strategy.deploy(sample_assets, mock_deploy)

    assert result["success"] is True
    assert result["successful"] == 4
    assert result["failed"] == 0
    assert len(result["batches"]) == 2


@pytest.mark.asyncio
async def test_rolling_deployment_partial_failure(sample_assets):
    """Test rolling deployment with some failures"""
    strategy = RollingDeployment(batch_size=2, wait_between_batches=0)

    # Mock deployment function that fails on second asset
    call_count = [0]

    async def mock_deploy(asset, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            return {"success": False, "error": "Deployment failed"}
        return {"success": True, "asset": asset["name"]}

    result = await strategy.deploy(sample_assets, mock_deploy)

    assert result["success"] is False
    assert result["successful"] == 3
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_blue_green_deployment_success():
    """Test successful blue-green deployment"""
    strategy = BlueGreenDeployment()

    green_assets = [
        {"name": "web-green-01", "environment": "green"},
        {"name": "web-green-02", "environment": "green"},
    ]
    blue_assets = [
        {"name": "web-blue-01", "environment": "blue"},
        {"name": "web-blue-02", "environment": "blue"},
    ]

    assets = green_assets + blue_assets

    async def mock_deploy(asset, **kwargs):
        return {"success": True, "asset": asset["name"]}

    result = await strategy.deploy(assets, mock_deploy)

    assert result["success"] is True
    assert result["successful"] == 4
    assert result["failed"] == 0
    assert "green" in result["phases"]
    assert "blue" in result["phases"]


@pytest.mark.asyncio
async def test_blue_green_deployment_green_failure():
    """Test blue-green deployment with green environment failure"""
    strategy = BlueGreenDeployment()

    green_assets = [{"name": "web-green-01", "environment": "green"}]
    blue_assets = [{"name": "web-blue-01", "environment": "blue"}]
    assets = green_assets + blue_assets

    async def mock_deploy(asset, **kwargs):
        if asset["environment"] == "green":
            return {"success": False, "error": "Green deployment failed"}
        return {"success": True}

    result = await strategy.deploy(assets, mock_deploy)

    # Should fail and not proceed to blue
    assert result["success"] is False
    assert "green" in result["phases"]
    assert result["phases"]["green"]["failed"] == 1


@pytest.mark.asyncio
async def test_canary_deployment_success(sample_assets):
    """Test successful canary deployment"""
    strategy = CanaryDeployment(canary_percentage=25.0, monitor_duration=0)

    async def mock_deploy(asset, **kwargs):
        return {"success": True, "asset": asset["name"]}

    result = await strategy.deploy(sample_assets, mock_deploy)

    assert result["success"] is True
    assert "canary" in result["phases"]
    assert "full_rollout" in result["phases"]


@pytest.mark.asyncio
async def test_canary_deployment_canary_failure(sample_assets):
    """Test canary deployment with canary failure"""
    strategy = CanaryDeployment(canary_percentage=25.0, monitor_duration=0)

    call_count = [0]

    async def mock_deploy(asset, **kwargs):
        call_count[0] += 1
        # First deployment (canary) fails
        if call_count[0] == 1:
            return {"success": False, "error": "Canary failed"}
        return {"success": True}

    result = await strategy.deploy(sample_assets, mock_deploy)

    # Should fail at canary and not proceed
    assert result["success"] is False
    assert result["phases"]["canary"]["failed"] >= 1


@pytest.mark.asyncio
async def test_canary_deployment_with_health_check(sample_assets):
    """Test canary deployment with health checks"""
    strategy = CanaryDeployment(canary_percentage=25.0, monitor_duration=0)

    async def mock_deploy(asset, **kwargs):
        return {"success": True}

    async def mock_health_check(asset):
        return {"healthy": True}

    result = await strategy.deploy(
        sample_assets,
        mock_deploy,
        health_check_func=mock_health_check,
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_canary_deployment_failed_health_check(sample_assets):
    """Test canary deployment with failed health check"""
    strategy = CanaryDeployment(canary_percentage=25.0, monitor_duration=0)

    async def mock_deploy(asset, **kwargs):
        return {"success": True}

    async def mock_health_check(asset):
        return {"healthy": False}

    result = await strategy.deploy(
        sample_assets,
        mock_deploy,
        health_check_func=mock_health_check,
    )

    # Should fail due to health check
    assert result["success"] is False


def test_get_deployment_strategy_rolling():
    """Test getting rolling strategy"""
    strategy = get_deployment_strategy("rolling", batch_size=3)

    assert isinstance(strategy, RollingDeployment)
    assert strategy.batch_size == 3


def test_get_deployment_strategy_blue_green():
    """Test getting blue-green strategy"""
    strategy = get_deployment_strategy("blue_green")

    assert isinstance(strategy, BlueGreenDeployment)


def test_get_deployment_strategy_canary():
    """Test getting canary strategy"""
    strategy = get_deployment_strategy("canary", canary_percentage=20.0)

    assert isinstance(strategy, CanaryDeployment)
    assert strategy.canary_percentage == 20.0


def test_get_deployment_strategy_unknown():
    """Test getting unknown strategy raises error"""
    with pytest.raises(ValueError):
        get_deployment_strategy("unknown")


@pytest.mark.asyncio
async def test_rolling_deployment_single_batch(sample_assets):
    """Test rolling deployment with single batch"""
    strategy = RollingDeployment(batch_size=10, wait_between_batches=0)

    async def mock_deploy(asset, **kwargs):
        return {"success": True}

    result = await strategy.deploy(sample_assets, mock_deploy)

    assert len(result["batches"]) == 1
    assert result["success"] is True
