"""
Deployment Engine Service
==========================

Low-level deployment execution service.
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
    logger.info("🚀 Starting Deployment Engine Service...")

    # Setup tracing
    try:
        setup_tracing("deployment-engine-service")
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

    logger.info("✓ Deployment Engine Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Deployment Engine Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Deployment Engine Service",
    description="Low-level deployment execution service",
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
        "service": "deployment-engine",
        "status": "healthy",
        "version": "0.1.0",
    }

    # Check SSH connectivity
    try:
        import paramiko
        health_status["ssh"] = "available"
    except ImportError:
        health_status["ssh"] = "unavailable"
        health_status["status"] = "degraded"

    # Check Ansible availability
    try:
        import ansible
        health_status["ansible"] = "available"
    except ImportError:
        health_status["ansible"] = "unavailable"

    # Check Celery
    try:
        from services.deployment_engine.tasks.celery_app import celery_app
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
        "service": "VulnZero Deployment Engine Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["deployment-engine"])


class DeploymentExecutionRequest(BaseModel):
    deployment_id: int
    asset_id: int
    patch_content: str
    deployment_method: str = "ansible"  # ansible, ssh, docker


@router.post("/execute")
async def execute_deployment(request: DeploymentExecutionRequest):
    """
    Execute a deployment to a single asset

    Args:
        request: Deployment execution request
    """
    from services.deployment_engine.tasks import execute_deployment_task

    task = execute_deployment_task.delay(
        deployment_id=request.deployment_id,
        asset_id=request.asset_id,
        patch_content=request.patch_content,
        method=request.deployment_method,
    )

    return {
        "task_id": task.id,
        "status": "executing",
        "deployment_id": request.deployment_id,
        "asset_id": request.asset_id,
    }


@router.get("/execute/status/{task_id}")
async def get_execution_status(task_id: str):
    """Get status of a deployment execution task"""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


class ConnectionTest(BaseModel):
    asset_id: int
    connection_type: str = "ssh"  # ssh, ansible, docker


@router.post("/test-connection")
async def test_connection(request: ConnectionTest):
    """
    Test connection to an asset

    Args:
        request: Connection test request
    """
    from services.deployment_engine.connection_manager import test_connection

    try:
        result = test_connection(
            asset_id=request.asset_id,
            connection_type=request.connection_type,
        )

        return {
            "asset_id": request.asset_id,
            "connection_type": request.connection_type,
            "status": "success" if result else "failed",
            "reachable": result,
        }
    except Exception as e:
        return {
            "asset_id": request.asset_id,
            "connection_type": request.connection_type,
            "status": "error",
            "error": str(e),
        }


@router.get("/methods")
async def list_deployment_methods():
    """List available deployment methods"""
    return {
        "methods": [
            {
                "name": "ansible",
                "description": "Ansible playbook-based deployment",
                "supported": True,
            },
            {
                "name": "ssh",
                "description": "Direct SSH-based deployment",
                "supported": True,
            },
            {
                "name": "docker",
                "description": "Docker container-based deployment",
                "supported": True,
            },
            {
                "name": "kubernetes",
                "description": "Kubernetes-based deployment",
                "supported": False,  # Future enhancement
            },
        ]
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.deployment_engine.main:app",
        host="0.0.0.0",
        port=8007,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
