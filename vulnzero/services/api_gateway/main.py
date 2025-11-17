"""FastAPI application for VulnZero API Gateway."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vulnzero.shared.config import get_settings

from .middleware import AuthenticationMiddleware, RateLimitMiddleware, RequestLoggingMiddleware
from .routers import health, patches, vulnerabilities

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting VulnZero API Gateway...")
    yield
    # Shutdown
    print("Shutting down VulnZero API Gateway...")


# Create FastAPI application
app = FastAPI(
    title="VulnZero API",
    description="Autonomous Vulnerability Remediation Platform - REST API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(AuthenticationMiddleware)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(patches.router, prefix="/api/v1", tags=["patches"])
app.include_router(vulnerabilities.router, prefix="/api/v1", tags=["vulnerabilities"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "VulnZero API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "operational",
    }
