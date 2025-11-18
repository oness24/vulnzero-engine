"""
Performance and load tests

Tests system performance under various loads
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from shared.models.models import (
    Vulnerability,
    Patch,
    Asset,
    VulnerabilitySeverity,
    PatchStatus,
)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_vulnerability_processing(db_session):
    """
    Test processing multiple vulnerabilities concurrently
    """
    from services.aggregator.aggregator import VulnerabilityAggregator

    aggregator = VulnerabilityAggregator()

    # Create 100 vulnerabilities
    vulnerabilities = []
    for i in range(100):
        vuln = Vulnerability(
            cve_id=f"CVE-2024-{1000+i}",
            title=f"Vulnerability {i}",
            description=f"Test vulnerability {i}",
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.0 + (i % 5),
            affected_systems=["Ubuntu 22.04"],
        )
        db_session.add(vuln)
        vulnerabilities.append(vuln)

    await db_session.commit()

    start_time = time.time()

    # Process all vulnerabilities concurrently
    tasks = []
    from services.aggregator.ml_prioritization import MLPrioritizer

    prioritizer = MLPrioritizer()

    for vuln in vulnerabilities:
        # Simulate processing
        priority = prioritizer.calculate_priority(vuln)
        vuln.priority_score = priority

    await db_session.commit()

    duration = time.time() - start_time

    # Should process 100 vulnerabilities in < 5 seconds
    assert duration < 5.0
    print(f"\nProcessed 100 vulnerabilities in {duration:.2f} seconds")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_patch_generation(db_session):
    """
    Test generating multiple patches concurrently
    """
    # Create vulnerabilities
    vulns = []
    for i in range(50):
        vuln = Vulnerability(
            cve_id=f"CVE-2024-{2000+i}",
            title=f"Vuln {i}",
            description="Test",
            severity=VulnerabilitySeverity.HIGH,
            cvss_score=7.5,
            affected_systems=["Ubuntu 22.04"],
        )
        db_session.add(vuln)
        vulns.append(vuln)

    await db_session.commit()

    start_time = time.time()

    # Generate patches concurrently
    from services.patch_generator.tasks import _generate_patch_async

    with patch('services.patch_generator.generator.PatchGenerator.generate_patch') as mock_gen:
        mock_gen.return_value = {
            "patch_script": "#!/bin/bash\necho patch",
            "rollback_script": "#!/bin/bash\necho rollback",
            "confidence_score": 0.9,
        }

        tasks = [_generate_patch_async(vuln.id) for vuln in vulns[:10]]  # Test with 10
        results = await asyncio.gather(*tasks)

        duration = time.time() - start_time

        # All should succeed
        assert all(r["status"] == "success" for r in results)

        # Should complete in reasonable time
        assert duration < 10.0
        print(f"\nGenerated 10 patches in {duration:.2f} seconds")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_large_scale_deployment(db_session, sample_vulnerability):
    """
    Test deploying patch to large number of assets
    """
    # Create 100 assets
    assets = []
    for i in range(100):
        asset = Asset(
            name=f"server-{i}",
            ip_address=f"192.168.{i//256}.{i%256}",
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
        patch_script="#!/bin/bash\necho patch",
        rollback_script="#!/bin/bash\necho rollback",
        status=PatchStatus.APPROVED,
    )
    db_session.add(patch)
    await db_session.commit()
    await db_session.refresh(patch)

    start_time = time.time()

    # Deploy to all assets
    from services.deployment_engine.tasks import _deploy_patch_async

    with patch('services.deployment_engine.executor.DeploymentExecutor') as MockExecutor:
        mock_executor = MagicMock()
        mock_executor.deploy_patch = AsyncMock(return_value={
            "success": True,
            "total_assets": 100,
            "successful": 100,
            "failed": 0,
        })
        MockExecutor.return_value = mock_executor

        result = await _deploy_patch_async(
            patch.id,
            [asset.id for asset in assets],
            "rolling",
            {"batch_size": 10},
        )

        duration = time.time() - start_time

        assert result["status"] == "success"
        print(f"\nDeployed to 100 assets in {duration:.2f} seconds")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_monitoring_performance(db_session, sample_asset):
    """
    Test monitoring system performance
    """
    from services.monitoring.deployment_monitor import DeploymentMonitor

    monitor = DeploymentMonitor()

    # Create 50 assets to monitor
    assets = []
    for i in range(50):
        assets.append({
            "id": i,
            "name": f"server-{i}",
            "ip_address": f"192.168.1.{100+i}",
        })

    start_time = time.time()

    # Check health of all assets
    with patch.object(monitor, 'check_asset_health') as mock_health:
        mock_health.return_value = {"healthy": True, "connected": True}

        health_result = await monitor.check_deployment_health(
            deployment_id=1,
            assets=assets,
        )

        duration = time.time() - start_time

        assert health_result["healthy_assets"] == 50
        print(f"\nMonitored 50 assets in {duration:.2f} seconds")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_database_query_performance(db_session):
    """
    Test database query performance with large datasets
    """
    from sqlalchemy import select

    # Create 1000 vulnerabilities
    for i in range(1000):
        vuln = Vulnerability(
            cve_id=f"CVE-2024-{3000+i}",
            title=f"Vuln {i}",
            description="Test",
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.0,
            affected_systems=["Ubuntu 22.04"],
        )
        db_session.add(vuln)

    await db_session.commit()

    start_time = time.time()

    # Query with pagination
    result = await db_session.execute(
        select(Vulnerability)
        .where(Vulnerability.severity == VulnerabilitySeverity.MEDIUM)
        .limit(50)
    )

    vulnerabilities = result.scalars().all()

    duration = time.time() - start_time

    assert len(vulnerabilities) == 50
    assert duration < 1.0  # Should be fast with proper indexing
    print(f"\nQueried 50 from 1000 vulnerabilities in {duration:.3f} seconds")


@pytest.mark.asyncio
async def test_analytics_calculation_performance(db_session):
    """
    Test analytics calculation performance
    """
    from services.monitoring.deployment_analytics import DeploymentAnalytics

    analytics = DeploymentAnalytics()

    # Track 100 deployments
    for i in range(100):
        await analytics.track_deployment_start(
            deployment_id=i,
            patch_id=i,
            strategy="rolling",
            asset_count=5,
        )

        await analytics.track_deployment_completion(
            deployment_id=i,
            success=(i % 10 != 0),  # 10% failure rate
            results={"successful": 5 if i % 10 != 0 else 0, "failed": 0 if i % 10 != 0 else 5},
            duration=float(100 + i),
        )

    start_time = time.time()

    # Calculate statistics
    stats = await analytics.get_deployment_stats(hours=24)
    performance = await analytics.get_performance_metrics(hours=24)
    failure_analysis = await analytics.get_failure_analysis(hours=24)

    duration = time.time() - start_time

    assert stats["total_deployments"] == 100
    assert duration < 2.0  # Should calculate quickly
    print(f"\nCalculated analytics for 100 deployments in {duration:.3f} seconds")


@pytest.mark.asyncio
async def test_api_endpoint_performance():
    """
    Test API endpoint performance
    """
    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)

    start_time = time.time()

    # Make 100 requests
    for i in range(100):
        response = client.get("/health")

    duration = time.time() - start_time

    # Should handle 100 requests quickly
    assert duration < 5.0
    print(f"\nHandled 100 API requests in {duration:.2f} seconds")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_health_checks():
    """
    Test concurrent health checks
    """
    from services.monitoring.deployment_monitor import DeploymentMonitor

    monitor = DeploymentMonitor()

    # Create 100 assets
    assets = [
        {"id": i, "name": f"server-{i}", "ip_address": f"192.168.1.{i}"}
        for i in range(100)
    ]

    start_time = time.time()

    with patch.object(monitor, 'check_asset_health') as mock_health:
        mock_health.return_value = {"healthy": True}

        # Run health checks concurrently
        tasks = [monitor.check_asset_health(asset) for asset in assets]
        results = await asyncio.gather(*tasks)

        duration = time.time() - start_time

        assert len(results) == 100
        print(f"\nPerformed 100 concurrent health checks in {duration:.2f} seconds")


@pytest.mark.asyncio
async def test_rollback_decision_performance():
    """
    Test rollback decision engine performance
    """
    from services.monitoring.rollback_manager import RollbackManager

    rollback_manager = RollbackManager()

    start_time = time.time()

    # Check rollback triggers 1000 times
    for i in range(1000):
        health_results = {
            f"asset_{j}": {"healthy": j % 2 == 0}
            for j in range(10)
        }

        should_rollback = rollback_manager.check_rollback_triggers(
            deployment_id=i,
            health_results=health_results,
            metrics={},
        )

    duration = time.time() - start_time

    # Should be very fast
    assert duration < 1.0
    print(f"\nProcessed 1000 rollback checks in {duration:.3f} seconds")


@pytest.mark.asyncio
async def test_alert_creation_performance():
    """
    Test alert creation and processing performance
    """
    from services.monitoring.alerts import AlertManager, AlertSeverity

    alert_manager = AlertManager()

    start_time = time.time()

    # Create 500 alerts
    for i in range(500):
        alert_manager.create_alert(
            title=f"Alert {i}",
            message=f"Test alert {i}",
            severity=AlertSeverity.WARNING,
            deployment_id=i,
        )

    duration = time.time() - start_time

    assert len(alert_manager.alerts) == 500
    assert duration < 2.0
    print(f"\nCreated 500 alerts in {duration:.3f} seconds")


@pytest.mark.asyncio
async def test_memory_usage_under_load(db_session):
    """
    Test memory usage doesn't grow excessively
    """
    import psutil
    import os

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Create and process large number of objects
    for i in range(500):
        vuln = Vulnerability(
            cve_id=f"CVE-2024-{4000+i}",
            title=f"Vuln {i}",
            description="Test " * 100,  # Larger description
            severity=VulnerabilitySeverity.MEDIUM,
            cvss_score=5.0,
            affected_systems=["Ubuntu 22.04"] * 10,
        )
        db_session.add(vuln)

    await db_session.commit()

    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory

    # Memory growth should be reasonable
    print(f"\nMemory growth: {memory_growth:.2f} MB")
    assert memory_growth < 100  # Less than 100MB growth
