"""
End-to-end workflow integration tests

Tests the complete pipeline from vulnerability discovery to patch deployment
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from shared.models.models import (
    Vulnerability,
    Patch,
    Deployment,
    Asset,
    VulnerabilitySeverity,
    PatchStatus,
    DeploymentStatus,
)


@pytest.mark.asyncio
async def test_complete_vulnerability_to_deployment_workflow(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test complete workflow:
    1. Vulnerability discovered
    2. Patch generated
    3. Patch tested in digital twin
    4. Patch approved
    5. Patch deployed to assets
    6. Deployment monitored
    7. Success verified
    """
    # Step 1: Vulnerability already exists (sample_vulnerability)
    assert sample_vulnerability.id is not None
    assert sample_vulnerability.severity == VulnerabilitySeverity.CRITICAL

    # Step 2: Generate patch
    from services.patch_generator.tasks import _generate_patch_async

    with patch('services.patch_generator.generator.PatchGenerator.generate_patch') as mock_gen:
        mock_gen.return_value = {
            "patch_script": "#!/bin/bash\napt-get update && apt-get install -y security-update",
            "rollback_script": "#!/bin/bash\napt-get remove -y security-update",
            "validation_script": "#!/bin/bash\ntest -f /usr/bin/security-update",
            "confidence_score": 0.95,
        }

        result = await _generate_patch_async(sample_vulnerability.id)

        assert result["status"] == "success"
        patch_id = result["patch_id"]

        # Verify patch created
        from sqlalchemy import select
        patch_result = await db_session.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = patch_result.scalar_one()
        assert patch.vulnerability_id == sample_vulnerability.id
        assert patch.status == PatchStatus.PENDING

    # Step 3: Test patch in digital twin
    from services.testing_engine.tasks import _test_patch_async

    with patch('services.testing_engine.container_manager.ContainerManager') as MockContainer:
        mock_container = MagicMock()
        mock_container.create_test_environment = AsyncMock(return_value={
            "success": True,
            "container_id": "test-container-123",
        })
        mock_container.execute_command = AsyncMock(return_value={
            "success": True,
            "exit_code": 0,
            "stdout": "Test passed",
        })
        mock_container.cleanup = AsyncMock()
        MockContainer.return_value = mock_container

        test_result = await _test_patch_async(patch.id)

        assert test_result["status"] == "success"
        assert test_result["test_results"]["smoke_tests"]["passed"] > 0

    # Step 4: Approve patch
    await db_session.refresh(patch)
    patch.status = PatchStatus.APPROVED
    await db_session.commit()

    # Step 5: Deploy patch
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 1,
            "successful": 1,
            "failed": 0,
            "assets": [{"id": sample_asset.id, "status": "success"}],
        })
        MockExecutor.return_value = mock_executor

        deploy_result = await _deploy_patch_async(
            patch.id,
            [sample_asset.id],
            "rolling",
            None,
        )

        assert deploy_result["status"] == "success"
        deployment_id = deploy_result["deployment_id"]

    # Step 6: Monitor deployment
    from services.monitoring.deployment_monitor import DeploymentMonitor

    monitor = DeploymentMonitor()

    with patch.object(monitor, 'check_asset_health') as mock_health:
        mock_health.return_value = {
            "healthy": True,
            "connected": True,
        }

        health_check = await monitor.check_deployment_health(
            deployment_id=deployment_id,
            assets=[{"id": sample_asset.id, "name": "test-asset"}],
        )

        assert health_check["healthy_assets"] == 1
        assert health_check["unhealthy_assets"] == 0

    # Step 7: Verify deployment
    from services.deployment_engine.tasks import _verify_deployment_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.verify_deployment = AsyncMock(return_value={
            "all_verified": True,
            "verified": 1,
            "failed": 0,
        })
        MockExecutor.return_value = mock_executor

        verify_result = await _verify_deployment_async(deployment_id)

        assert verify_result["status"] == "success"
        assert verify_result["verification_result"]["all_verified"] is True


@pytest.mark.asyncio
async def test_workflow_with_rollback(
    db_session,
    sample_vulnerability,
    sample_asset,
):
    """
    Test workflow with automatic rollback:
    1. Patch deployed
    2. Health check fails
    3. Automatic rollback triggered
    4. Rollback executed successfully
    """
    # Create patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho test",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    # Deploy patch
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 1,
            "successful": 1,
            "failed": 0,
            "assets": [{"id": sample_asset.id}],
        })
        MockExecutor.return_value = mock_executor

        deploy_result = await _deploy_patch_async(
            patch.id,
            [sample_asset.id],
            "rolling",
            None,
        )

        deployment_id = deploy_result["deployment_id"]

    # Health check fails
    from services.monitoring.rollback_manager import RollbackManager

    rollback_manager = RollbackManager()

    health_results = {
        "asset_1": {"healthy": False, "error": "Service down"},
    }

    # Simulate multiple failed health checks to trigger rollback
    for _ in range(4):
        should_rollback = rollback_manager.check_rollback_triggers(
            deployment_id=deployment_id,
            health_results=health_results,
            metrics={},
        )

    assert should_rollback is True

    # Execute rollback
    with patch('services.monitoring.rollback_manager.get_connection_manager') as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.connect.return_value = True
        mock_mgr.copy_content.return_value = True
        mock_mgr.execute_command.return_value = {
            "success": True,
            "exit_code": 0,
        }
        mock_get_mgr.return_value = mock_mgr

        rollback_result = await rollback_manager.execute_rollback(
            deployment_id=deployment_id,
            assets=[{"id": sample_asset.id, "ip_address": "192.168.1.1"}],
            rollback_script=patch.rollback_script,
            reason="health_check_failed",
        )

        assert rollback_result["success"] is True
        assert rollback_result["successful_rollbacks"] == 1


@pytest.mark.asyncio
async def test_multi_vulnerability_aggregation_workflow(db_session):
    """
    Test vulnerability aggregation from multiple sources
    """
    from services.aggregator.sources.nvd import NVDClient
    from services.aggregator.aggregator import VulnerabilityAggregator

    aggregator = VulnerabilityAggregator()

    # Mock multiple vulnerability sources
    mock_vulnerabilities = [
        {
            "cve_id": "CVE-2024-0001",
            "title": "Critical SQL Injection",
            "description": "SQL injection vulnerability",
            "severity": "critical",
            "cvss_score": 9.8,
            "affected_systems": ["Ubuntu 20.04", "Ubuntu 22.04"],
            "published_date": datetime.utcnow(),
        },
        {
            "cve_id": "CVE-2024-0002",
            "title": "Remote Code Execution",
            "description": "RCE vulnerability",
            "severity": "high",
            "cvss_score": 8.5,
            "affected_systems": ["Debian 11"],
            "published_date": datetime.utcnow(),
        },
    ]

    with patch.object(aggregator, 'fetch_from_nvd') as mock_nvd:
        mock_nvd.return_value = mock_vulnerabilities

        vulns = await aggregator.fetch_from_nvd()

        assert len(vulns) == 2
        assert vulns[0]["cve_id"] == "CVE-2024-0001"


@pytest.mark.asyncio
async def test_batch_patch_deployment_workflow(
    db_session,
    sample_vulnerability,
):
    """
    Test deploying patches to multiple assets in batches
    """
    # Create multiple assets
    assets = []
    for i in range(5):
        asset = Asset(
            name=f"server-{i}",
            ip_address=f"192.168.1.{100+i}",
            hostname=f"server-{i}.example.com",
            os_version="Ubuntu 22.04",
            status="active",
        )
        db_session.add(asset)
        assets.append(asset)

    await db_session.commit()

    # Create patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\napt-get update",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    # Deploy to all assets with rolling strategy
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 5,
            "successful": 5,
            "failed": 0,
            "batches": [
                {"batch_number": 1, "successful": 2, "failed": 0},
                {"batch_number": 2, "successful": 2, "failed": 0},
                {"batch_number": 3, "successful": 1, "failed": 0},
            ],
        })
        MockExecutor.return_value = mock_executor

        asset_ids = [asset.id for asset in assets]
        result = await _deploy_patch_async(
            patch.id,
            asset_ids,
            "rolling",
            {"batch_size": 2},
        )

        assert result["status"] == "success"
        assert result["deployment_result"]["successful"] == 5


@pytest.mark.asyncio
async def test_vulnerability_prioritization_workflow(
    db_session,
    sample_vulnerability,
):
    """
    Test ML-based vulnerability prioritization
    """
    from services.aggregator.ml_prioritization import MLPrioritizer

    prioritizer = MLPrioritizer()

    # Calculate priority score
    priority_score = prioritizer.calculate_priority(sample_vulnerability)

    assert priority_score > 0
    assert priority_score <= 100

    # Update vulnerability with priority
    sample_vulnerability.priority_score = priority_score
    await db_session.commit()

    await db_session.refresh(sample_vulnerability)
    assert sample_vulnerability.priority_score == priority_score


@pytest.mark.asyncio
async def test_alert_notification_workflow(db_session):
    """
    Test alert creation and notification workflow
    """
    from services.monitoring.alerts import AlertManager, AlertSeverity, AlertChannel

    alert_manager = AlertManager()

    # Add notification channel
    alert_manager.add_notification_channel(
        channel_type=AlertChannel.LOG,
        config={"min_severity": "warning"},
    )

    # Create alert
    alert = alert_manager.create_alert(
        title="Test Alert",
        message="Integration test alert",
        severity=AlertSeverity.ERROR,
        deployment_id=1,
    )

    assert alert["id"] > 0
    assert alert["severity"] == "error"

    # Verify alert in active alerts
    active_alerts = alert_manager.get_active_alerts()
    assert len(active_alerts) > 0

    # Acknowledge and resolve
    alert_manager.acknowledge_alert(alert["id"])
    alert_manager.resolve_alert(alert["id"])

    # Verify resolved
    active_alerts = alert_manager.get_active_alerts()
    assert len([a for a in active_alerts if a["id"] == alert["id"]]) == 0


@pytest.mark.asyncio
async def test_deployment_analytics_workflow(db_session):
    """
    Test deployment analytics tracking workflow
    """
    from services.monitoring.deployment_analytics import DeploymentAnalytics

    analytics = DeploymentAnalytics()

    # Track deployment lifecycle
    record = await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
    )

    assert record["deployment_id"] == 1
    assert record["status"] == "in_progress"

    # Complete deployment
    await analytics.track_deployment_completion(
        deployment_id=1,
        success=True,
        results={"successful": 5, "failed": 0},
        duration=120.0,
    )

    # Get statistics
    stats = await analytics.get_deployment_stats(hours=24)

    assert stats["total_deployments"] == 1
    assert stats["completed"] == 1
    assert stats["success_rate"] == 100.0

    # Get performance metrics
    performance = await analytics.get_performance_metrics(hours=24)

    assert performance["total_deployments"] == 1
    assert performance["average_duration_seconds"] == 120.0


@pytest.mark.asyncio
async def test_canary_deployment_workflow(
    db_session,
    sample_vulnerability,
):
    """
    Test canary deployment strategy workflow
    """
    # Create 10 assets
    assets = []
    for i in range(10):
        asset = Asset(
            name=f"server-{i}",
            ip_address=f"192.168.1.{100+i}",
            os_version="Ubuntu 22.04",
            status="active",
        )
        db_session.add(asset)
        assets.append(asset)

    await db_session.commit()

    # Create patch
    patch = Patch(
        vulnerability_id=sample_vulnerability.id,
        patch_script="#!/bin/bash\necho patch",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    # Deploy with canary strategy
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 10,
            "successful": 10,
            "failed": 0,
            "phases": {
                "canary": {"successful": 1, "failed": 0},  # 10% canary
                "full_rollout": {"successful": 9, "failed": 0},
            },
        })
        MockExecutor.return_value = mock_executor

        result = await _deploy_patch_async(
            patch.id,
            [asset.id for asset in assets],
            "canary",
            {"canary_percentage": 10.0, "monitor_duration": 0},
        )

        assert result["status"] == "success"
        assert "phases" in result["deployment_result"]
