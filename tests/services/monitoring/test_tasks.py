"""
Tests for monitoring Celery tasks
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.monitoring.tasks import (
    _monitor_deployment_async,
    _rollback_deployment_async,
    _check_deployment_health_async,
    _generate_deployment_report_async,
    _cleanup_old_data_async,
    _check_all_active_deployments_async,
    _send_deployment_summary_async,
)
from shared.models.models import Deployment, Patch, DeploymentStatus, PatchStatus


@pytest.mark.asyncio
async def test_monitor_deployment_task(db_session, sample_vulnerability, sample_asset):
    """Test monitor_deployment task"""
    # Create patch and deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": sample_asset.id, "name": "test-asset"}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks.deployment_monitor") as mock_monitor:
            mock_monitor.monitor_deployment = AsyncMock(return_value={
                "all_healthy": True,
                "healthy_assets": 1,
                "unhealthy_assets": 0,
            })

            with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
                mock_analytics.track_deployment_start = AsyncMock(return_value={})
                mock_analytics.track_deployment_completion = AsyncMock(return_value={})

                result = await _monitor_deployment_async(
                    deployment.id,
                    check_interval=1,
                    max_duration=5,
                )

                assert result["status"] == "success"
                assert "monitoring_result" in result


@pytest.mark.asyncio
async def test_monitor_deployment_not_found(db_session):
    """Test monitor_deployment with non-existent deployment"""
    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _monitor_deployment_async(99999)

        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


@pytest.mark.asyncio
async def test_monitor_deployment_no_assets(db_session, sample_vulnerability):
    """Test monitor_deployment with no assets"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={},  # No assets
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _monitor_deployment_async(deployment.id)

        assert result["status"] == "error"
        assert "no assets" in result["message"].lower()


@pytest.mark.asyncio
async def test_rollback_deployment_task(db_session, sample_vulnerability):
    """Test rollback_deployment task"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.COMPLETED,
        strategy="rolling",
        results={"assets": [{"id": 1, "name": "test"}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks.rollback_manager") as mock_manager:
            mock_manager.execute_rollback = AsyncMock(return_value={
                "success": True,
                "rollback_id": 1,
                "successful_rollbacks": 1,
            })

            with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
                mock_analytics.track_rollback = AsyncMock(return_value={})

                result = await _rollback_deployment_async(deployment.id)

                assert result["status"] == "success"
                assert "rollback_result" in result


@pytest.mark.asyncio
async def test_rollback_deployment_not_found(db_session):
    """Test rollback with non-existent deployment"""
    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        result = await _rollback_deployment_async(99999)

        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_check_deployment_health_task(db_session, sample_vulnerability):
    """Test check_deployment_health task"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": 1}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks.deployment_monitor") as mock_monitor:
            mock_monitor.check_deployment_health = AsyncMock(return_value={
                "healthy": True,
                "asset_health": {},
                "metrics": {},
            })

            with patch("services.monitoring.tasks.rollback_manager") as mock_manager:
                mock_manager.check_rollback_triggers.return_value = False

                result = await _check_deployment_health_async(deployment.id)

                assert result["status"] == "success"
                assert result["rollback_triggered"] is False


@pytest.mark.asyncio
async def test_check_deployment_health_triggers_rollback(db_session, sample_vulnerability):
    """Test health check that triggers rollback"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": 1}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks.deployment_monitor") as mock_monitor:
            mock_monitor.check_deployment_health = AsyncMock(return_value={
                "healthy": False,
                "asset_health": {},
                "metrics": {},
            })

            with patch("services.monitoring.tasks.rollback_manager") as mock_manager:
                # Trigger rollback
                mock_manager.check_rollback_triggers.return_value = True

                with patch("services.monitoring.tasks._rollback_deployment_async") as mock_rollback:
                    mock_rollback.delay = MagicMock()

                    result = await _check_deployment_health_async(deployment.id)

                    assert result["rollback_triggered"] is True


@pytest.mark.asyncio
async def test_generate_deployment_report():
    """Test generate_deployment_report task"""
    with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
        mock_analytics.get_deployment_stats = AsyncMock(return_value={
            "total_deployments": 10,
            "success_rate": 90.0,
        })
        mock_analytics.get_failure_analysis = AsyncMock(return_value={
            "total_failures": 1,
        })
        mock_analytics.get_performance_metrics = AsyncMock(return_value={
            "average_duration_seconds": 120.0,
        })
        mock_analytics.deployment_history = [{"started_at": "2024-01-01T00:00:00"}]

        result = await _generate_deployment_report_async(hours=24)

        assert result["status"] == "success"
        assert "report" in result
        assert result["report"]["statistics"]["total_deployments"] == 10


@pytest.mark.asyncio
async def test_cleanup_old_data():
    """Test cleanup_old_data task"""
    with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
        mock_analytics.clear_old_history = AsyncMock(return_value=5)

        with patch("services.monitoring.tasks.rollback_manager") as mock_manager:
            mock_manager.clear_old_rollbacks.return_value = 3

            result = await _cleanup_old_data_async(days=30)

            assert result["status"] == "success"
            assert result["records_cleared"] == 5


@pytest.mark.asyncio
async def test_check_all_active_deployments(db_session, sample_vulnerability):
    """Test check_all_active_deployments task"""
    # Create active deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment1 = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": 1}]},
    )
    deployment2 = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": 2}]},
    )
    db_session.add(deployment1)
    db_session.add(deployment2)
    await db_session.commit()

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks._check_deployment_health_async") as mock_check:
            mock_check.return_value = {"rollback_triggered": False}

            result = await _check_all_active_deployments_async()

            assert result["status"] == "success"
            assert result["checked"] == 2
            assert result["rollbacks_triggered"] == 0


@pytest.mark.asyncio
async def test_send_deployment_summary():
    """Test send_deployment_summary task"""
    with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
        mock_analytics.get_deployment_stats = AsyncMock(return_value={
            "total_deployments": 10,
            "success_rate": 90.0,
            "rollback_rate": 5.0,
        })

        with patch("services.monitoring.tasks.alert_manager") as mock_alert_mgr:
            mock_alert_mgr.get_alert_summary.return_value = {
                "total_alerts": 5,
                "active_alerts": 2,
            }
            mock_alert_mgr.create_alert.return_value = {
                "id": 1,
                "title": "Deployment Summary",
            }

            result = await _send_deployment_summary_async(hours=24)

            assert result["status"] == "success"
            assert result["alert_id"] == 1
            assert "stats" in result


@pytest.mark.asyncio
async def test_monitor_deployment_with_rollback_recommendation(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """Test monitoring that recommends rollback"""
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.IN_PROGRESS,
        strategy="rolling",
        results={"assets": [{"id": sample_asset.id}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    with patch("services.monitoring.tasks.AsyncSessionLocal") as MockSession:
        MockSession.return_value.__aenter__.return_value = db_session

        with patch("services.monitoring.tasks.deployment_monitor") as mock_monitor:
            mock_monitor.monitor_deployment = AsyncMock(return_value={
                "all_healthy": False,
                "rollback_recommended": True,
                "rollback_reason": "Health checks failed",
                "metrics": {},
            })

            with patch("services.monitoring.tasks.deployment_analytics") as mock_analytics:
                mock_analytics.track_deployment_start = AsyncMock(return_value={})
                mock_analytics.track_deployment_completion = AsyncMock(return_value={})

                with patch("services.monitoring.tasks._rollback_deployment_async") as mock_rollback:
                    mock_rollback.delay = MagicMock()

                    result = await _monitor_deployment_async(deployment.id)

                    assert result["status"] == "success"
                    # Verify rollback was triggered
                    mock_rollback.delay.assert_called_once_with(deployment.id)
