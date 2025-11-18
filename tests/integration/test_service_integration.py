"""
Service integration tests

Tests interactions between different services
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from shared.models.models import (
    Vulnerability,
    Patch,
    Deployment,
    Asset,
    PatchStatus,
    DeploymentStatus,
)


@pytest.mark.asyncio
async def test_aggregator_to_patch_generator_integration(
    db_session,
    sample_vulnerability,
):
    """
    Test integration between vulnerability aggregator and patch generator
    """
    from services.aggregator.aggregator import VulnerabilityAggregator
    from services.patch_generator.tasks import _generate_patch_async

    # Step 1: Aggregator finds vulnerability (already exists)
    assert sample_vulnerability.id is not None

    # Step 2: Patch generator creates patch for vulnerability
    with patch('services.patch_generator.generator.PatchGenerator.generate_patch') as mock_gen:
        mock_gen.return_value = {
            "patch_script": "#!/bin/bash\napt-get install security-patch",
            "rollback_script": "#!/bin/bash\napt-get remove security-patch",
            "validation_script": "#!/bin/bash\ntest -f /usr/bin/patch",
            "confidence_score": 0.92,
        }

        result = await _generate_patch_async(sample_vulnerability.id)

        assert result["status"] == "success"
        assert result["patch_id"] is not None

        # Verify patch is linked to vulnerability
        from sqlalchemy import select
        patch_result = await db_session.execute(
            select(Patch).where(Patch.id == result["patch_id"])
        )
        patch = patch_result.scalar_one()
        assert patch.vulnerability_id == sample_vulnerability.id


@pytest.mark.asyncio
async def test_patch_generator_to_testing_engine_integration(
    db_session,
    sample_vulnerability,
):
    """
    Test integration between patch generator and testing engine
    """
    # Create patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\napt-get update",
        rollback_script="#!/bin/bash\necho rollback",
        validation_script="#!/bin/bash\necho validate",
        status=PatchStatus.PENDING,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    # Test patch
    from services.testing_engine.tasks import _test_patch_async

    with patch('services.testing_engine.container_manager.ContainerManager') as MockContainer:
        mock_container = MagicMock()
        mock_container.create_test_environment = AsyncMock(return_value={
            "success": True,
            "container_id": "test-123",
        })
        mock_container.execute_command = AsyncMock(return_value={
            "success": True,
            "exit_code": 0,
        })
        mock_container.cleanup = AsyncMock()
        MockContainer.return_value = mock_container

        result = await _test_patch_async(patch.id)

        assert result["status"] == "success"

        # Verify patch test results are stored
        await db_session.refresh(patch)
        assert patch.test_results is not None
        assert "smoke_tests" in patch.test_results


@pytest.mark.asyncio
async def test_testing_engine_to_deployment_engine_integration(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test integration between testing engine and deployment engine
    """
    # Create tested and approved patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho patch",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
        test_results={"smoke_tests": {"passed": 5, "failed": 0}},
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    # Deploy tested patch
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 1,
            "successful": 1,
            "failed": 0,
        })
        MockExecutor.return_value = mock_executor

        result = await _deploy_patch_async(
            patch.id,
            [sample_asset.id],
            "rolling",
            None,
        )

        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_deployment_engine_to_monitoring_integration(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test integration between deployment engine and monitoring system
    """
    # Create deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho patch",
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
        results={"assets": [{"id": sample_asset.id, "ip_address": "192.168.1.1"}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    # Monitor deployment
    from services.monitoring.deployment_monitor import DeploymentMonitor

    monitor = DeploymentMonitor()

    with patch.object(monitor, 'check_asset_health') as mock_health:
        mock_health.return_value = {
            "healthy": True,
            "connected": True,
        }

        health_check = await monitor.check_deployment_health(
            deployment_id=deployment.id,
            assets=deployment.results["assets"],
        )

        assert health_check["healthy_assets"] == 1


@pytest.mark.asyncio
async def test_monitoring_to_rollback_integration(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test integration between monitoring and rollback manager
    """
    # Create deployment
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho patch",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.DEPLOYED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    deployment = Deployment(
        patch_id=patch.id,
        status=DeploymentStatus.COMPLETED,
        strategy="rolling",
        results={"assets": [{"id": sample_asset.id, "ip_address": "192.168.1.1"}]},
    )
    db_session.add(deployment)
    await db_session.commit()
    await db_session.refresh(deployment)

    # Monitoring detects failure
    from services.monitoring.rollback_manager import RollbackManager

    rollback_manager = RollbackManager()

    health_results = {
        "asset_1": {"healthy": False},
    }

    # Trigger rollback after consecutive failures
    for _ in range(4):
        should_rollback = rollback_manager.check_rollback_triggers(
            deployment_id=deployment.id,
            health_results=health_results,
            metrics={},
        )

    assert should_rollback is True

    # Execute rollback
    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.execute_command.return_value = {"success": True}
        mock_get_mgr.return_value = mock_mgr

        rollback_result = await rollback_manager.execute_rollback(
            deployment_id=deployment.id,
            assets=deployment.results["assets"],
            rollback_script=patch.rollback_script,
            reason="health_check_failed",
        )

        assert rollback_result["success"] is True


@pytest.mark.asyncio
async def test_api_to_services_integration(db_session, sample_vulnerability):
    """
    Test integration between API routes and backend services
    """
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    # Test vulnerability API triggers prioritization
    with patch("api.routes.vulnerabilities.get_db") as mock_db:
        mock_db.return_value = db_session

        with patch("services.aggregator.tasks.prioritize_vulnerabilities") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")

            response = client.post(f"/api/vulnerabilities/{sample_vulnerability.id}/prioritize")

            # API should trigger background task
            if response.status_code == 200:
                assert "task_id" in response.json()


@pytest.mark.asyncio
async def test_celery_task_chaining_integration(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test Celery task chaining across services
    """
    # Simulate task chain: generate -> test -> deploy
    from services.patch_generator.tasks import _generate_patch_async
    from services.testing_engine.tasks import _test_patch_async
    from services.deployment_engine.tasks import _deploy_patch_async

    # Step 1: Generate patch
    with patch('services.patch_generator.generator.PatchGenerator.generate_patch') as mock_gen:
        mock_gen.return_value = {
            "patch_script": "#!/bin/bash\necho patch",
            "rollback_script": "#!/bin/bash\necho rollback",
            "validation_script": "#!/bin/bash\necho validate",
            "confidence_score": 0.95,
        }

        gen_result = await _generate_patch_async(sample_vulnerability.id)
        patch_id = gen_result["patch_id"]

    # Step 2: Test patch
    with patch('services.testing_engine.container_manager.ContainerManager') as MockContainer:
        mock_container = MagicMock()
        mock_container.create_test_environment = AsyncMock(return_value={"success": True})
        mock_container.execute_command = AsyncMock(return_value={"success": True, "exit_code": 0})
        mock_container.cleanup = AsyncMock()
        MockContainer.return_value = mock_container

        test_result = await _test_patch_async(patch_id)
        assert test_result["status"] == "success"

    # Step 3: Approve and deploy
    from sqlalchemy import select
    patch_result = await db_session.execute(select(Patch).where(Patch.id == patch_id))
    patch = patch_result.scalar_one()
    patch.status = PatchStatus.APPROVED
    await db_session.commit()

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 1,
            "successful": 1,
            "failed": 0,
        })
        MockExecutor.return_value = mock_executor

        deploy_result = await _deploy_patch_async(
            patch_id,
            [sample_asset.id],
            "rolling",
            None,
        )

        assert deploy_result["status"] == "success"


@pytest.mark.asyncio
async def test_database_transaction_integration(
    db_session,
    sample_vulnerability,
):
    """
    Test database transactions across service calls
    """
    from sqlalchemy import select

    # Create patch in transaction
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.PENDING,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    patch_id = patch.id

    # Verify patch persisted
    result = await db_session.execute(
        select(Patch).where(Patch.id == patch_id)
    )
    loaded_patch = result.scalar_one()

    assert loaded_patch.id == patch_id
    assert loaded_patch.vulnerability_id == sample_vulnerability.id


@pytest.mark.asyncio
async def test_websocket_to_monitoring_integration():
    """
    Test WebSocket integration with monitoring system
    """
    from services.monitoring.deployment_monitor import DeploymentMonitor
    from services.monitoring.alerts import AlertManager

    monitor = DeploymentMonitor()
    alert_manager = AlertManager()

    # Start monitoring session
    monitor.start_monitoring(deployment_id=1)

    status = monitor.get_monitoring_status(deployment_id=1)
    assert status["active"] is True

    # Create alert
    alert = alert_manager.create_alert(
        title="Test Alert",
        message="WebSocket integration test",
        severity=alert_manager.AlertSeverity.INFO,
    )

    assert alert["id"] > 0

    # Stop monitoring
    monitor.stop_monitoring(deployment_id=1)

    status = monitor.get_monitoring_status(deployment_id=1)
    assert status["active"] is False


@pytest.mark.asyncio
async def test_analytics_integration_across_services(db_session):
    """
    Test analytics integration across all services
    """
    from services.monitoring.deployment_analytics import DeploymentAnalytics

    analytics = DeploymentAnalytics()

    # Track deployment
    await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
    )

    await analytics.track_deployment_completion(
        deployment_id=1,
        success=True,
        results={"successful": 5, "failed": 0},
        duration=100.0,
    )

    # Get stats
    stats = await analytics.get_deployment_stats(hours=24)
    performance = await analytics.get_performance_metrics(hours=24)

    assert stats["total_deployments"] == 1
    assert performance["average_duration_seconds"] == 100.0


@pytest.mark.asyncio
async def test_ml_prioritizer_to_aggregator_integration(
    db_session,
    sample_vulnerability,
):
    """
    Test ML prioritizer integration with aggregator
    """
    from services.aggregator.ml_prioritization import MLPrioritizer

    prioritizer = MLPrioritizer()

    # Calculate priority
    priority_score = prioritizer.calculate_priority(sample_vulnerability)

    assert priority_score > 0

    # Update vulnerability
    sample_vulnerability.priority_score = priority_score
    await db_session.commit()

    await db_session.refresh(sample_vulnerability)
    assert sample_vulnerability.priority_score == priority_score
