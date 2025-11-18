"""
VulnZero API Gateway - Main application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import structlog
from datetime import datetime

from shared.config import settings
from services.api_gateway.routes import (
    auth_router,
    vulnerabilities_router,
    assets_router,
    patches_router,
    deployments_router,
    system_router,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("starting_vulnzero_api", environment=settings.environment)

    # Initialize database connection pool
    try:
        from shared.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("database_connection_verified")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e), exc_info=True)

    # Initialize Redis connection pool
    try:
        import redis
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_client.close()
        logger.info("redis_connection_verified")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    # Initialize background tasks (Celery broker connection check)
    try:
        from shared.celery_app import app as celery_app
        celery_app.connection().ensure_connection(max_retries=3)
        logger.info("celery_broker_connected")
        logger.info("background_tasks_initialized",
                   message="Celery workers should be started separately")
    except Exception as e:
        logger.warning("celery_initialization_warning", error=str(e),
                      message="Celery workers may need to be started manually")

    yield

    # Shutdown
    logger.info("shutting_down_vulnzero_api")

    # Close database connections
    try:
        from shared.models.database import engine
        if engine:
            await engine.dispose()
            logger.info("database_connections_closed")
    except Exception as e:
        logger.warning("database_shutdown_failed", error=str(e))

    # Close Redis connections
    try:
        import redis.asyncio as aioredis
        redis_client = getattr(app, 'redis', None)
        if redis_client:
            await redis_client.close()
            logger.info("redis_connections_closed")
    except Exception as e:
        logger.warning("redis_shutdown_failed", error=str(e))

    logger.info("vulnzero_api_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="VulnZero API",
    description="Zero-Touch Vulnerability Remediation Platform API",
    version="0.1.0",
    docs_url="/docs" if settings.enable_swagger_ui else None,
    redoc_url="/redoc" if settings.enable_redoc else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = datetime.utcnow()

    # Log request
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Log response
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration,
    )

    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(vulnerabilities_router, prefix="/api/v1/vulnerabilities", tags=["Vulnerabilities"])
app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(patches_router, prefix="/api/v1/patches", tags=["Patches"])
app.include_router(deployments_router, prefix="/api/v1/deployments", tags=["Deployments"])
app.include_router(system_router, prefix="/api/v1", tags=["System"])

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "VulnZero API",
        "version": "0.1.0",
        "status": "operational",
        "documentation": "/docs" if settings.enable_swagger_ui else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers,
        log_level=settings.log_level.lower(),
    )
