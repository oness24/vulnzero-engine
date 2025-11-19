"""
Deployment Orchestrator Service
================================

Manages deployment strategies and orchestrates patch deployments.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware
from shared.tracing import setup_tracing, instrument_fastapi, instrument_sqlalchemy, instrument_redis
from shared.monitoring import update_application_info

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Deployment Orchestrator Service...")

    # Setup tracing
    try:
        setup_tracing("deployment-orchestrator-service")
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

    logger.info("✓ Deployment Orchestrator Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Deployment Orchestrator Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Deployment Orchestrator Service",
    description="Deployment strategy and orchestration service",
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
        "service": "deployment-orchestrator",
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

    # Check Celery
    try:
        from services.deployment_orchestrator.tasks.celery_app import celery_app
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
        "service": "VulnZero Deployment Orchestrator Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["deployment"])


class DeploymentStrategy(str, Enum):
    ROLLING = "rolling"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    ALL_AT_ONCE = "all_at_once"


class DeploymentRequest(BaseModel):
    patch_id: int
    asset_ids: list[int]
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    canary_percentage: int = 10  # For canary deployments
    batch_size: int = 1  # For rolling deployments


@router.post("/deploy")
async def deploy_patch(request: DeploymentRequest):
    """
    Deploy a patch using specified strategy

    Args:
        request: Deployment request with strategy and targets
    """
    from services.deployment_orchestrator.tasks.deployment_tasks import deploy_patch_task

    task = deploy_patch_task.delay(
        patch_id=request.patch_id,
        asset_ids=request.asset_ids,
        strategy=request.strategy.value,
        canary_percentage=request.canary_percentage,
        batch_size=request.batch_size,
    )

    return {
        "task_id": task.id,
        "status": "started",
        "patch_id": request.patch_id,
        "strategy": request.strategy.value,
        "asset_count": len(request.asset_ids),
    }


@router.get("/deploy/status/{task_id}")
async def get_deployment_status(task_id: str):
    """Get status of a deployment task"""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.post("/rollback/{deployment_id}")
async def rollback_deployment(deployment_id: int):
    """
    Rollback a deployment

    Args:
        deployment_id: ID of deployment to rollback
    """
    from services.deployment_orchestrator.tasks.deployment_tasks import rollback_deployment_task

    task = rollback_deployment_task.delay(deployment_id)

    return {
        "task_id": task.id,
        "status": "started",
        "deployment_id": deployment_id,
    }


class PreDeploymentCheck(BaseModel):
    patch_id: int
    asset_ids: list[int]


@router.post("/validate/pre-deployment")
async def pre_deployment_validation(request: PreDeploymentCheck):
    """
    Run pre-deployment validation checks

    Args:
        request: Pre-deployment validation request
    """
    from services.deployment_orchestrator.validators.pre_deploy import PreDeploymentValidator

    validator = PreDeploymentValidator()
    validation_result = validator.validate(
        patch_id=request.patch_id,
        asset_ids=request.asset_ids,
    )

    return {
        "valid": validation_result.is_valid,
        "checks": validation_result.checks,
        "warnings": validation_result.warnings,
        "errors": validation_result.errors,
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.deployment_orchestrator.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
