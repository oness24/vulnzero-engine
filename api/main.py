"""
Main FastAPI application for VulnZero platform
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import time

from api.routes import (
    auth,
    vulnerabilities,
    patches,
    deployments,
    monitoring,
    websocket,
    dashboard,
)
from api.middleware import AuditLogMiddleware
from shared.config.settings import settings

logger = structlog.get_logger()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="VulnZero API",
    description="Automated vulnerability management and patch deployment platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - secure configuration based on environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.is_production else ["*"],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit logging middleware - enabled based on settings
if settings.enable_audit_logging:
    app.add_middleware(AuditLogMiddleware)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all HTTP requests
    """
    start_time = time.time()

    # Log request
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    try:
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

        return response

    except Exception as e:
        logger.error(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            exc_info=True,
        )
        raise


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Enhanced health check endpoint
    Checks all critical dependencies: database, Redis, and Celery workers
    Returns HTTP 503 if any dependency is unhealthy
    """
    from datetime import datetime
    from sqlalchemy import text
    import redis
    from shared.models.database import AsyncSessionLocal

    health = {
        "status": "healthy",
        "service": "vulnzero-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
        "details": {}
    }

    # Check Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health["checks"]["database"] = "ok"
        health["details"]["database"] = "PostgreSQL connection verified"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = "error"
        health["details"]["database"] = f"Database error: {str(e)}"
        logger.error("health_check_database_failed", error=str(e))

    # Check Redis
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        health["checks"]["redis"] = "ok"
        health["details"]["redis"] = "Redis connection verified"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["redis"] = "error"
        health["details"]["redis"] = f"Redis error: {str(e)}"
        logger.error("health_check_redis_failed", error=str(e))

    # Check Celery Workers
    try:
        from shared.celery_app import app as celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            active_workers = len(stats)
            health["checks"]["celery"] = "ok"
            health["details"]["celery"] = f"{active_workers} workers active"
        else:
            health["status"] = "degraded"
            health["checks"]["celery"] = "warning"
            health["details"]["celery"] = "No workers found"
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["celery"] = "warning"
        health["details"]["celery"] = f"Celery check error: {str(e)}"
        logger.warning("health_check_celery_warning", error=str(e))

    # Return appropriate status code
    status_code = 200 if health["status"] in ["healthy", "degraded"] else 503
    return JSONResponse(content=health, status_code=status_code)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "name": "VulnZero API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(vulnerabilities.router, prefix="/api")
app.include_router(patches.router, prefix="/api")
app.include_router(deployments.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup
    """
    logger.info("vulnzero_api_starting")

    # Initialize services if needed
    try:
        # Database connection check
        from shared.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")

        logger.info("database_connection_verified")

    except Exception as e:
        logger.error("startup_failed", error=str(e), exc_info=True)
        # Don't raise - allow app to start even if DB is temporarily unavailable

    logger.info("vulnzero_api_started")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown
    """
    logger.info("vulnzero_api_shutting_down")

    # Cleanup tasks
    # Close database connections, etc.

    logger.info("vulnzero_api_shutdown_complete")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
