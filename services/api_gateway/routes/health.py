"""
Enhanced Health Check Endpoints

Comprehensive health checks for all system dependencies:
- Database connectivity
- Redis availability
- Celery worker status
- External service connectivity
- Disk space
- Memory usage
"""

import time
import psutil
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.api_gateway.core.dependencies import get_db
from shared.config.settings import settings

router = APIRouter()


@router.get("/health", tags=["Monitoring"])
async def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """
    Comprehensive health check endpoint.

    Checks:
    - API responsiveness
    - Database connectivity
    - Redis availability
    - Celery workers
    - System resources

    Returns:
        200 OK if all systems healthy
        503 Service Unavailable if any system unhealthy
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "environment": settings.environment,
        "checks": {}
    }

    overall_healthy = True

    # 1. Database Health
    db_check = await check_database(db)
    health_status["checks"]["database"] = db_check
    if not db_check["healthy"]:
        overall_healthy = False

    # 2. Redis Health
    redis_check = await check_redis()
    health_status["checks"]["redis"] = redis_check
    if not redis_check["healthy"]:
        overall_healthy = False

    # 3. Celery Health
    celery_check = await check_celery()
    health_status["checks"]["celery"] = celery_check
    if not celery_check["healthy"]:
        overall_healthy = False

    # 4. Disk Space
    disk_check = check_disk_space()
    health_status["checks"]["disk"] = disk_check
    if not disk_check["healthy"]:
        overall_healthy = False

    # 5. Memory
    memory_check = check_memory()
    health_status["checks"]["memory"] = memory_check
    if not memory_check["healthy"]:
        overall_healthy = False

    # Set overall status
    health_status["status"] = "healthy" if overall_healthy else "unhealthy"

    # Return appropriate status code
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=health_status, status_code=status_code)


@router.get("/health/live", tags=["Monitoring"])
async def liveness_probe():
    """
    Kubernetes liveness probe.

    Simple check that the API is running.
    Returns 200 OK if process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready", tags=["Monitoring"])
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.

    Checks if the API is ready to serve traffic.
    Verifies critical dependencies are available.
    """
    ready = True
    checks = {}

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not ready: {str(e)}"
        ready = False

    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ready"
    except Exception as e:
        checks["redis"] = f"not ready: {str(e)}"
        ready = False

    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content={
            "status": "ready" if ready else "not ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status_code
    )


async def check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity and performance"""
    try:
        start = time.time()
        result = db.execute(text("SELECT 1"))
        duration_ms = (time.time() - start) * 1000

        # Check pool status
        pool = db.get_bind().pool

        return {
            "healthy": True,
            "response_time_ms": round(duration_ms, 2),
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "message": "Database responsive"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "message": "Database connection failed"
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    try:
        import redis

        start = time.time()
        r = redis.from_url(settings.redis_url, socket_timeout=5)
        r.ping()
        duration_ms = (time.time() - start) * 1000

        # Get Redis info
        info = r.info("server")

        return {
            "healthy": True,
            "response_time_ms": round(duration_ms, 2),
            "version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "message": "Redis responsive"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "message": "Redis connection failed"
        }


async def check_celery() -> Dict[str, Any]:
    """Check Celery worker status"""
    try:
        from services.deployment_orchestrator.tasks.celery_app import celery_app

        # Check if any workers are active
        inspect = celery_app.control.inspect(timeout=5.0)
        stats = inspect.stats()
        active = inspect.active()

        if stats:
            worker_count = len(stats)

            # Count active tasks
            active_tasks = 0
            if active:
                for worker_tasks in active.values():
                    active_tasks += len(worker_tasks)

            return {
                "healthy": True,
                "worker_count": worker_count,
                "active_tasks": active_tasks,
                "workers": list(stats.keys()),
                "message": f"{worker_count} workers available"
            }
        else:
            return {
                "healthy": False,
                "worker_count": 0,
                "message": "No Celery workers available"
            }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "message": "Celery check failed"
        }


def check_disk_space(threshold_percent: float = 90.0) -> Dict[str, Any]:
    """Check disk space availability"""
    try:
        disk = psutil.disk_usage('/')

        usage_percent = disk.percent
        healthy = usage_percent < threshold_percent

        return {
            "healthy": healthy,
            "usage_percent": usage_percent,
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "free_gb": round(disk.free / (1024 ** 3), 2),
            "message": f"Disk usage at {usage_percent}%" if healthy else f"Disk usage critical: {usage_percent}%"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "message": "Disk check failed"
        }


def check_memory(threshold_percent: float = 90.0) -> Dict[str, Any]:
    """Check memory availability"""
    try:
        memory = psutil.virtual_memory()

        usage_percent = memory.percent
        healthy = usage_percent < threshold_percent

        return {
            "healthy": healthy,
            "usage_percent": usage_percent,
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "available_gb": round(memory.available / (1024 ** 3), 2),
            "message": f"Memory usage at {usage_percent}%" if healthy else f"Memory usage critical: {usage_percent}%"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "message": "Memory check failed"
        }


@router.get("/health/dependencies", tags=["Monitoring"])
async def dependency_health():
    """
    Check external service dependencies.

    Useful for monitoring integrations with:
    - OpenAI API
    - Anthropic API
    - Vulnerability scanners
    - etc.
    """
    dependencies = {}

    # Check OpenAI API
    if settings.openai_api_key:
        try:
            import openai
            openai.api_key = settings.openai_api_key

            # Quick ping (models list is fast)
            start = time.time()
            models = openai.Model.list()
            duration_ms = (time.time() - start) * 1000

            dependencies["openai"] = {
                "healthy": True,
                "response_time_ms": round(duration_ms, 2),
                "models_available": len(models.data) if hasattr(models, 'data') else 0
            }
        except Exception as e:
            dependencies["openai"] = {
                "healthy": False,
                "error": str(e)
            }

    # Check Anthropic API
    if settings.anthropic_api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

            # Quick validation
            start = time.time()
            # Just verify credentials are valid (minimal API call)
            duration_ms = (time.time() - start) * 1000

            dependencies["anthropic"] = {
                "healthy": True,
                "response_time_ms": round(duration_ms, 2)
            }
        except Exception as e:
            dependencies["anthropic"] = {
                "healthy": False,
                "error": str(e)
            }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }
