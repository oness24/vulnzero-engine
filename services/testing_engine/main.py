"""
Testing Engine Service
======================

Automated testing and validation service.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware
from shared.tracing import setup_tracing, instrument_fastapi
from shared.monitoring import update_application_info

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Testing Engine Service...")

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
        setup_tracing("testing-engine-service")
        instrument_fastapi(app)
        logger.info("✓ Tracing initialized")
    except Exception as e:
        logger.warning(f"⚠ Tracing initialization failed: {e}")

    # Initialize monitoring
    try:
        update_application_info()
        logger.info("✓ Monitoring initialized")
    except Exception as e:
        logger.warning(f"⚠ Monitoring initialization failed: {e}")

    logger.info("✓ Testing Engine Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Testing Engine Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Testing Engine Service",
    description="Automated testing and validation service",
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
        "service": "testing-engine",
        "status": "healthy",
        "version": "0.1.0",
    }

    # Check Docker availability
    try:
        import docker
        client = docker.from_env()
        client.ping()
        health_status["docker"] = "connected"
    except Exception as e:
        health_status["docker"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Celery
    try:
        from services.testing_engine.tasks.celery_app import celery_app
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
        "service": "VulnZero Testing Engine Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["testing"])


class TestRequest(BaseModel):
    patch_id: int
    test_suite: str = "default"
    environment_id: str = None


@router.post("/test/run")
async def run_tests(request: TestRequest):
    """
    Run tests for a patch

    Args:
        request: Test execution request
    """
    from services.testing_engine.tasks import run_test_suite_task

    task = run_test_suite_task.delay(
        patch_id=request.patch_id,
        test_suite=request.test_suite,
        environment_id=request.environment_id,
    )

    return {
        "task_id": task.id,
        "status": "running",
        "patch_id": request.patch_id,
        "test_suite": request.test_suite,
    }


@router.get("/test/status/{task_id}")
async def get_test_status(task_id: str):
    """Get status of a test task"""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


class ValidationRequest(BaseModel):
    patch_id: int
    validation_type: str = "security"  # security, functionality, performance


@router.post("/validate")
async def validate_patch(request: ValidationRequest):
    """
    Validate a patch

    Args:
        request: Validation request
    """
    from services.testing_engine.tasks import validate_patch_task

    task = validate_patch_task.delay(
        patch_id=request.patch_id,
        validation_type=request.validation_type,
    )

    return {
        "task_id": task.id,
        "status": "validating",
        "patch_id": request.patch_id,
        "validation_type": request.validation_type,
    }


@router.get("/test-suites")
async def list_test_suites():
    """List available test suites"""
    return {
        "test_suites": [
            {
                "name": "default",
                "description": "Default test suite",
                "tests": ["unit", "integration", "security"],
            },
            {
                "name": "security",
                "description": "Security-focused tests",
                "tests": ["owasp-top10", "cwe-checks", "penetration"],
            },
            {
                "name": "functionality",
                "description": "Functionality tests",
                "tests": ["unit", "integration", "e2e"],
            },
            {
                "name": "performance",
                "description": "Performance and load tests",
                "tests": ["load", "stress", "spike"],
            },
        ]
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.testing_engine.main:app",
        host="0.0.0.0",
        port=8006,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
