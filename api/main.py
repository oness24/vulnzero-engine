"""
Main FastAPI application for VulnZero platform
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from api.routes import (
    vulnerabilities,
    patches,
    deployments,
    monitoring,
    websocket,
    dashboard,
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="VulnZero API",
    description="Automated vulnerability management and patch deployment platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    Health check endpoint
    """
    return {
        "status": "healthy",
        "service": "vulnzero-api",
        "version": "1.0.0",
    }


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
