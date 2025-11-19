"""
Vulnerability Aggregator Service
=================================

Collects and normalizes vulnerability data from multiple sources.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware
from shared.tracing import setup_tracing, instrument_fastapi, instrument_sqlalchemy, instrument_redis
from shared.monitoring import update_application_info

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Vulnerability Aggregator Service...")

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
        setup_tracing("aggregator-service")
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

    # Initialize database
    try:
        from shared.config.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("✓ Database connection established")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")

    # Initialize Redis
    try:
        from shared.cache import get_redis_client
        redis = await get_redis_client()
        await redis.ping()
        logger.info("✓ Redis connection established")
    except Exception as e:
        logger.warning(f"⚠ Redis connection failed: {e}")

    logger.info("✓ Aggregator Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Aggregator Service...")

    try:
        from shared.cache import close_redis_client
        await close_redis_client()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    try:
        from shared.config.database import engine
        engine.dispose()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Aggregator Service",
    description="Vulnerability aggregation and normalization service",
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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    health_status = {
        "service": "aggregator",
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

    # Check Celery
    try:
        from services.aggregator.tasks.celery_app import celery_app
        stats = celery_app.control.inspect().stats()
        if stats:
            health_status["celery"] = "connected"
            health_status["workers"] = len(stats)
        else:
            health_status["celery"] = "no_workers"
    except Exception as e:
        health_status["celery"] = "disconnected"

    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "VulnZero Aggregator Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["aggregator"])


@router.post("/scan/trigger")
async def trigger_scan(scanner: str, target: str):
    """
    Trigger a vulnerability scan

    Args:
        scanner: Scanner to use (wazuh, trivy, grype)
        target: Target to scan (asset ID or hostname)
    """
    from services.aggregator.tasks.scan_tasks import scan_asset_task

    task = scan_asset_task.delay(scanner, target)

    return {
        "task_id": task.id,
        "status": "started",
        "scanner": scanner,
        "target": target,
    }


@router.get("/scan/status/{task_id}")
async def get_scan_status(task_id: str):
    """Get status of a scan task"""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.post("/normalize")
async def normalize_vulnerabilities(data: dict):
    """
    Normalize vulnerability data from scanner

    Args:
        data: Raw scanner output
    """
    from services.aggregator.normalizer import normalize_scanner_data

    normalized = normalize_scanner_data(data)

    return {
        "status": "success",
        "count": len(normalized),
        "vulnerabilities": normalized,
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.aggregator.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
