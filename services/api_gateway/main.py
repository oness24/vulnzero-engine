"""
VulnZero API Gateway - Main Application
FastAPI-based REST API for the VulnZero platform
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import time
import logging
from typing import AsyncGenerator

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware, MetricsMiddleware
from services.api_gateway.api.v1 import api_router
from services.api_gateway.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan events.
    Runs on startup and shutdown with graceful handling.
    """
    # Startup
    logger.info("🚀 Starting VulnZero API Gateway...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API Docs: http://localhost:8000/docs")

    # Initialize metrics
    try:
        from shared.monitoring import update_application_info
        update_application_info()
        logger.info("✓ Prometheus metrics initialized")
    except Exception as e:
        logger.warning(f"⚠ Metrics initialization failed (non-critical): {e}")

    # Initialize connections
    try:
        from shared.cache import get_redis_client
        await get_redis_client()
        logger.info("✓ Redis connection initialized")
    except Exception as e:
        logger.warning(f"⚠ Redis initialization failed (non-critical): {e}")

    yield

    # Graceful Shutdown
    logger.info("🛑 Initiating graceful shutdown...")

    # Close Redis connection
    try:
        from shared.cache import close_redis_client
        await close_redis_client()
        logger.info("✓ Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")

    # Close database connections
    try:
        from shared.config.database import engine
        engine.dispose()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

    logger.info("✓ Graceful shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="VulnZero API",
    description="""
    # VulnZero: Autonomous Vulnerability Remediation Platform

    **Zero-Touch Vulnerability Remediation. Zero Days of Exposure.**

    ## Features

    - 🔍 **Automated Vulnerability Detection**: Integrates with Wazuh, Qualys, Tenable
    - 🤖 **AI-Powered Patch Generation**: Uses GPT-4/Claude for context-aware patches
    - 🧪 **Digital Twin Testing**: Tests patches in isolated sandbox environments
    - ⚡ **Zero-Downtime Deployment**: Blue-green and canary deployment strategies
    - 📊 **Real-Time Monitoring**: Automatic rollback on anomaly detection
    - 🎯 **ML-Based Prioritization**: Intelligently prioritizes vulnerabilities

    ## Authentication

    Most endpoints require JWT authentication. Use `/api/v1/auth/login` to obtain tokens.

    ## Rate Limiting

    API requests are rate-limited to prevent abuse:
    - Default: 60 requests per minute per IP
    - Burst: 10 additional requests

    ## Support

    - **Documentation**: https://docs.vulnzero.com
    - **Support**: support@vulnzero.com
    - **GitHub**: https://github.com/oness24/vulnzero-engine
    """,
    version="0.1.0",
    docs_url="/docs" if settings.debug or settings.is_development else None,
    redoc_url="/redoc" if settings.debug or settings.is_development else None,
    openapi_url="/openapi.json" if settings.debug or settings.is_development else None,
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================================
# Middleware Configuration
# ============================================================================

# CORS Middleware - Allow cross-origin requests from web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# GZip Middleware - Compress responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security Headers middleware - adds comprehensive security headers to all responses
# Protects against XSS, clickjacking, MIME-sniffing, and other common vulnerabilities
app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=settings.is_production
)

# Metrics middleware - collects Prometheus metrics for all HTTP requests
# Tracks request count, duration, errors, and in-progress requests
app.add_middleware(MetricsMiddleware)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None),
        }
    )
    response = await call_next(request)
    logger.info(
        f"Response: {response.status_code}",
        extra={
            "status_code": response.status_code,
            "request_id": getattr(request.state, "request_id", None),
        }
    )
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={"request_id": getattr(request.state, "request_id", None)}
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": "VulnZero API",
        "version": "0.1.0",
        "status": "operational",
        "environment": settings.environment,
        "docs": "/docs" if settings.debug or settings.is_development else None,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.
    Returns detailed health status of the API and all its dependencies.

    Use for monitoring dashboards and detailed diagnostics.
    """
    from shared.health import health_checker

    health_status = await health_checker.check_health(include_optional=True)

    # Return 503 if unhealthy, 200 otherwise
    status_code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if health_status["status"] == "unhealthy"
        else status.HTTP_200_OK
    )

    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    This endpoint checks if the application is alive and running.
    It should always return 200 unless the application is truly dead.

    Kubernetes will restart the container if this fails.
    """
    from shared.health import health_checker

    liveness_status = await health_checker.check_liveness()
    return JSONResponse(content=liveness_status, status_code=status.HTTP_200_OK)


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.

    This endpoint checks if the application is ready to serve traffic.
    It validates that critical dependencies (database, redis) are available.

    Kubernetes will remove from load balancer if this fails.
    """
    from shared.health import health_checker

    readiness_status = await health_checker.check_readiness()

    # Return 503 if not ready
    status_code = (
        status.HTTP_200_OK
        if readiness_status["ready"]
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(content=readiness_status, status_code=status_code)


# ============================================================================
# Include API Routers
# ============================================================================

app.include_router(api_router, prefix="/api/v1")


# ============================================================================
# Run with uvicorn (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
