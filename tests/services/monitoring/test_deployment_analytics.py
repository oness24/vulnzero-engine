"""
Tests for deployment analytics
"""

import pytest
from datetime import datetime, timedelta
from services.monitoring.deployment_analytics import DeploymentAnalytics


@pytest.fixture
def analytics():
    """Create deployment analytics"""
    return DeploymentAnalytics()


@pytest.mark.asyncio
async def test_track_deployment_start(analytics):
    """Test tracking deployment start"""
    record = await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
        metadata={"test": "data"},
    )

    assert record["deployment_id"] == 1
    assert record["patch_id"] == 10
    assert record["strategy"] == "rolling"
    assert record["asset_count"] == 5
    assert record["status"] == "in_progress"
    assert len(analytics.deployment_history) == 1


@pytest.mark.asyncio
async def test_track_deployment_completion(analytics):
    """Test tracking deployment completion"""
    # Start deployment
    await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
    )

    # Complete deployment
    results = {"successful": 5, "failed": 0}
    record = await analytics.track_deployment_completion(
        deployment_id=1,
        success=True,
        results=results,
        duration=120.5,
    )

    assert record["status"] == "completed"
    assert record["success"] is True
    assert record["results"] == results
    assert record["duration_seconds"] == 120.5


@pytest.mark.asyncio
async def test_track_deployment_completion_calculates_duration(analytics):
    """Test that completion calculates duration if not provided"""
    await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
    )

    record = await analytics.track_deployment_completion(
        deployment_id=1,
        success=True,
        results={},
    )

    assert "duration_seconds" in record
    assert record["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_track_rollback(analytics):
    """Test tracking rollback"""
    await analytics.track_deployment_start(
        deployment_id=1,
        patch_id=10,
        strategy="rolling",
        asset_count=5,
    )

    rollback_record = await analytics.track_rollback(
        deployment_id=1,
        rollback_id=100,
        reason="health_check_failed",
        success=True,
        results={"rolled_back": 5},
    )

    assert rollback_record["deployment_id"] == 1
    assert rollback_record["rollback_id"] == 100
    assert rollback_record["success"] is True

    # Check deployment record is updated
    deployment = analytics.deployment_history[0]
    assert deployment["rolled_back"] is True


@pytest.mark.asyncio
async def test_get_deployment_stats(analytics):
    """Test getting deployment statistics"""
    # Create some deployments
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {"successful": 5})

    await analytics.track_deployment_start(2, 11, "canary", 10)
    await analytics.track_deployment_completion(2, False, {"failed": 10})

    stats = await analytics.get_deployment_stats(hours=24)

    assert stats["total_deployments"] == 2
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["success_rate"] == 50.0
    assert stats["failure_rate"] == 50.0


@pytest.mark.asyncio
async def test_get_deployment_stats_by_strategy(analytics):
    """Test getting stats filtered by strategy"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {})

    await analytics.track_deployment_start(2, 11, "canary", 10)
    await analytics.track_deployment_completion(2, True, {})

    stats = await analytics.get_deployment_stats(hours=24, strategy="rolling")

    assert stats["total_deployments"] == 1


@pytest.mark.asyncio
async def test_get_deployment_stats_with_rollbacks(analytics):
    """Test stats include rollback rate"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {})
    await analytics.track_rollback(1, 100, "test", True)

    stats = await analytics.get_deployment_stats(hours=24)

    assert stats["rolled_back"] == 1
    assert stats["rollback_rate"] == 100.0


@pytest.mark.asyncio
async def test_get_strategy_breakdown(analytics):
    """Test getting breakdown by strategy"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {})

    await analytics.track_deployment_start(2, 11, "rolling", 5)
    await analytics.track_deployment_completion(2, False, {})

    await analytics.track_deployment_start(3, 12, "canary", 5)
    await analytics.track_deployment_completion(3, True, {})

    deployments = analytics.deployment_history
    breakdown = analytics._get_strategy_breakdown(deployments)

    assert "rolling" in breakdown
    assert "canary" in breakdown
    assert breakdown["rolling"]["total"] == 2
    assert breakdown["rolling"]["completed"] == 1
    assert breakdown["rolling"]["failed"] == 1
    assert breakdown["canary"]["total"] == 1


@pytest.mark.asyncio
async def test_get_average_duration(analytics):
    """Test calculating average duration"""
    deployments = [
        {"duration_seconds": 100},
        {"duration_seconds": 200},
        {"duration_seconds": 300},
    ]

    avg = analytics._get_average_duration(deployments)

    assert avg == 200.0


@pytest.mark.asyncio
async def test_get_average_duration_empty(analytics):
    """Test average duration with no deployments"""
    avg = analytics._get_average_duration([])

    assert avg is None


@pytest.mark.asyncio
async def test_get_patch_deployment_stats(analytics):
    """Test getting stats for specific patch"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(
        1,
        True,
        {"total_assets": 5, "successful": 5, "failed": 0},
    )

    await analytics.track_deployment_start(2, 10, "canary", 10)
    await analytics.track_deployment_completion(
        2,
        True,
        {"total_assets": 10, "successful": 8, "failed": 2},
    )

    stats = await analytics.get_patch_deployment_stats(patch_id=10)

    assert stats["patch_id"] == 10
    assert stats["total_deployments"] == 2
    assert stats["total_assets"] == 15
    assert stats["successful_assets"] == 13
    assert stats["failed_assets"] == 2


@pytest.mark.asyncio
async def test_get_failure_analysis(analytics):
    """Test getting failure analysis"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(
        1,
        False,
        {"error": "Connection failed", "failed": 5},
    )

    await analytics.track_deployment_start(2, 11, "canary", 10)
    await analytics.track_deployment_completion(
        2,
        False,
        {"failed": 10},
    )

    analysis = await analytics.get_failure_analysis(hours=24)

    assert analysis["total_failures"] == 2
    assert "failure_reasons" in analysis
    assert "failure_by_strategy" in analysis
    assert "failure_by_patch" in analysis


@pytest.mark.asyncio
async def test_get_performance_metrics(analytics):
    """Test getting performance metrics"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {}, duration=100)

    await analytics.track_deployment_start(2, 11, "rolling", 10)
    await analytics.track_deployment_completion(2, True, {}, duration=200)

    metrics = await analytics.get_performance_metrics(hours=24)

    assert metrics["total_deployments"] == 2
    assert metrics["average_duration_seconds"] == 150.0
    assert metrics["min_duration_seconds"] == 100
    assert metrics["max_duration_seconds"] == 200
    assert metrics["total_assets_deployed"] == 15


@pytest.mark.asyncio
async def test_get_performance_metrics_empty(analytics):
    """Test performance metrics with no deployments"""
    metrics = await analytics.get_performance_metrics(hours=24)

    assert metrics["total_deployments"] == 0
    assert "metrics" in metrics


@pytest.mark.asyncio
async def test_export_deployment_history(analytics):
    """Test exporting deployment history"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {})

    export = await analytics.export_deployment_history(hours=24, format="json")

    assert export["total_records"] == 1
    assert export["format"] == "json"
    assert len(export["deployments"]) == 1


@pytest.mark.asyncio
async def test_export_all_history(analytics):
    """Test exporting all history"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)

    export = await analytics.export_deployment_history()

    assert export["time_period_hours"] is None
    assert export["total_records"] == 1


@pytest.mark.asyncio
async def test_clear_old_history(analytics):
    """Test clearing old deployment history"""
    # Add old deployment
    old_time = (datetime.utcnow() - timedelta(days=40)).isoformat()
    analytics.deployment_history.append({
        "deployment_id": 1,
        "started_at": old_time,
    })

    # Add recent deployment
    await analytics.track_deployment_start(2, 10, "rolling", 5)

    cleared = await analytics.clear_old_history(days=30)

    assert cleared == 1
    assert len(analytics.deployment_history) == 1


@pytest.mark.asyncio
async def test_metrics_caching(analytics):
    """Test that metrics are cached"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(1, True, {})

    # First call
    stats1 = await analytics.get_deployment_stats(hours=24)

    # Second call should use cache
    stats2 = await analytics.get_deployment_stats(hours=24)

    assert stats1 == stats2
    assert len(analytics.metrics_cache) > 0


@pytest.mark.asyncio
async def test_cache_invalidation(analytics):
    """Test that cache is invalidated on updates"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)

    # Get stats (populates cache)
    await analytics.get_deployment_stats(hours=24)

    # Complete deployment (should clear cache)
    await analytics.track_deployment_completion(1, True, {})

    assert len(analytics.metrics_cache) == 0


@pytest.mark.asyncio
async def test_get_asset_deployment_history(analytics):
    """Test getting deployment history for specific asset"""
    await analytics.track_deployment_start(1, 10, "rolling", 5)
    await analytics.track_deployment_completion(
        1,
        True,
        {
            "assets": [
                {"asset_id": 100, "status": "success"},
                {"asset_id": 101, "status": "success"},
            ]
        },
    )

    history = await analytics.get_asset_deployment_history(asset_id=100, limit=10)

    assert len(history) == 1
    assert history[0]["asset_result"]["asset_id"] == 100
