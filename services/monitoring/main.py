"""
Monitoring Service
==================

Centralized monitoring and metrics aggregation service.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware
from shared.tracing import setup_tracing, instrument_fastapi, instrument_sqlalchemy, instrument_redis
from shared.monitoring import (
    update_application_info,
    update_db_pool_metrics,
    update_cache_metrics,
    update_celery_metrics,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Monitoring Service...")

    # Initialize Sentry error tracking
    try:
        from shared.monitoring.sentry_config import init_sentry_for_environment
        import os
        environment = os.getenv("ENVIRONMENT", "development")
        release = os.getenv("RELEASE_VERSION") or os.getenv("GIT_COMMIT_SHA")
        if init_sentry_for_environment(environment, release=release):
            logger.info(f"✓ Sentry initialized (environment={environment})")
    except Exception as e:
        logger.warning(f"⚠ Sentry initialization failed: {e}")

    # Setup tracing
    try:
        setup_tracing("monitoring-service")
        instrument_fastapi(app)

        from shared.config.database import engine
        instrument_sqlalchemy(engine)

        instrument_redis()
        logger.info("✓ Tracing initialized")
    except Exception as e:
        logger.warning(f"⚠ Tracing initialization failed: {e}")

    # Initialize monitoring
    try:
        update_application_info()
        logger.info("✓ Monitoring initialized")
    except Exception as e:
        logger.warning(f"⚠ Monitoring initialization failed: {e}")

    logger.info("✓ Monitoring Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Monitoring Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Monitoring Service",
    description="Centralized monitoring and metrics service",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)


# Health check
@app.get("/health")
async def health_check():
    """Service health check"""
    health_status = {
        "service": "monitoring",
        "status": "healthy",
        "version": "0.1.0",
    }

    # Check database
    try:
        from shared.config.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        from shared.cache import get_redis_client
        redis = await get_redis_client()
        await redis.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = "disconnected"

    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VulnZero Monitoring Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
        },
    }


# Metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns all application metrics in Prometheus format.
    """
    # Update dynamic metrics before exporting
    try:
        update_db_pool_metrics()
        await update_cache_metrics()
        await update_celery_metrics()
    except Exception as e:
        logger.warning(f"Failed to update dynamic metrics: {e}")

    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


@router.get("/metrics/system")
async def get_system_metrics():
    """Get system-level metrics"""
    import psutil

    return {
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "percent": psutil.disk_usage('/').percent,
        },
    }


@router.get("/metrics/services")
async def get_service_metrics():
    """Get service health metrics"""
    services = ["aggregator", "patch-generator", "deployment-orchestrator", "digital-twin"]

    service_status = {}
    for service in services:
        # Try to ping each service
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{service}:800{services.index(service)+1}/health")
                service_status[service] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds(),
                }
        except Exception as e:
            service_status[service] = {
                "status": "unreachable",
                "error": str(e),
            }

    return service_status


@router.get("/metrics/database")
async def get_database_metrics():
    """Get database metrics"""
    from shared.config.database import engine

    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.size() - pool.checkedout(),
    }


@router.get("/metrics/cache")
async def get_cache_metrics():
    """Get cache metrics"""
    from shared.cache import get_redis_client

    try:
        redis = await get_redis_client()
        info = await redis.info()

        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "0"),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1),
        }
    except Exception as e:
        return {"error": str(e), "status": "disconnected"}


@router.get("/metrics/celery")
async def get_celery_metrics():
    """Get Celery worker metrics"""
    try:
        from services.monitoring.tasks.celery_app import celery_app

        stats = celery_app.control.inspect().stats()
        active = celery_app.control.inspect().active()

        return {
            "workers": len(stats) if stats else 0,
            "active_tasks": sum(len(tasks) for tasks in active.values()) if active else 0,
            "stats": stats,
        }
    except Exception as e:
        return {"error": str(e), "status": "disconnected"}


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.monitoring.main:app",
        host="0.0.0.0",
        port=8005,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
