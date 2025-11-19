"""
Digital Twin Service
====================

Provides isolated testing environments for patch validation.
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
    logger.info("🚀 Starting Digital Twin Service...")

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
        setup_tracing("digital-twin-service")
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

    # Check Docker availability
    try:
        import docker
        client = docker.from_env()
        client.ping()
        logger.info("✓ Docker connection established")
    except Exception as e:
        logger.warning(f"⚠ Docker connection failed: {e}")

    logger.info("✓ Digital Twin Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Digital Twin Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Digital Twin Service",
    description="Isolated testing environment service",
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
        "service": "digital-twin",
        "status": "healthy",
        "version": "0.1.0",
    }

    # Check Docker
    try:
        import docker
        client = docker.from_env()
        client.ping()
        health_status["docker"] = "connected"

        # Check available resources
        info = client.info()
        health_status["docker_containers"] = info.get("Containers", 0)
        health_status["docker_images"] = len(client.images.list())
    except Exception as e:
        health_status["docker"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Celery
    try:
        from services.digital_twin.tasks.celery_app import celery_app
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
        "service": "VulnZero Digital Twin Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["digital-twin"])


class TestEnvironmentRequest(BaseModel):
    asset_id: int
    patch_id: int
    test_suite: str = "default"


@router.post("/test/create")
async def create_test_environment(request: TestEnvironmentRequest):
    """
    Create an isolated test environment

    Args:
        request: Test environment creation request
    """
    from services.digital_twin.tasks.testing_tasks import create_test_environment_task

    task = create_test_environment_task.delay(
        asset_id=request.asset_id,
        patch_id=request.patch_id,
        test_suite=request.test_suite,
    )

    return {
        "task_id": task.id,
        "status": "creating",
        "asset_id": request.asset_id,
        "patch_id": request.patch_id,
    }


@router.post("/test/run")
async def run_tests(environment_id: str, test_suite: str = "default"):
    """
    Run tests in a digital twin environment

    Args:
        environment_id: ID of the test environment
        test_suite: Test suite to run
    """
    from services.digital_twin.tasks.testing_tasks import run_tests_task

    task = run_tests_task.delay(
        environment_id=environment_id,
        test_suite=test_suite,
    )

    return {
        "task_id": task.id,
        "status": "running",
        "environment_id": environment_id,
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


@router.delete("/test/cleanup/{environment_id}")
async def cleanup_environment(environment_id: str):
    """
    Cleanup a test environment

    Args:
        environment_id: ID of the environment to cleanup
    """
    from services.digital_twin.tasks.testing_tasks import cleanup_environment_task

    task = cleanup_environment_task.delay(environment_id)

    return {
        "task_id": task.id,
        "status": "cleaning_up",
        "environment_id": environment_id,
    }


@router.get("/environments")
async def list_environments():
    """List all active test environments"""
    try:
        import docker
        client = docker.from_env()

        # List containers with label 'vulnzero.type=test-environment'
        containers = client.containers.list(
            filters={"label": "vulnzero.type=test-environment"}
        )

        environments = []
        for container in containers:
            environments.append({
                "id": container.short_id,
                "name": container.name,
                "status": container.status,
                "created": container.attrs["Created"],
                "labels": container.labels,
            })

        return {
            "count": len(environments),
            "environments": environments,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list environments: {str(e)}")


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.digital_twin.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
