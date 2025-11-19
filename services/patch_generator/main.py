"""
Patch Generator Service
=======================

AI-powered patch generation service using LLMs.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.config.settings import settings
from shared.middleware import SecurityHeadersMiddleware
from shared.tracing import setup_tracing, instrument_fastapi, instrument_sqlalchemy, instrument_redis
from shared.monitoring import update_application_info

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Patch Generator Service...")

    # Setup tracing
    try:
        setup_tracing("patch-generator-service")
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

    # Check LLM API keys
    if not settings.openai_api_key and not settings.anthropic_api_key:
        logger.warning("⚠ No LLM API keys configured")
    else:
        logger.info("✓ LLM API keys configured")

    logger.info("✓ Patch Generator Service ready")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Patch Generator Service...")


# Create FastAPI app
app = FastAPI(
    title="VulnZero Patch Generator Service",
    description="AI-powered patch generation service",
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
        "service": "patch-generator",
        "status": "healthy",
        "version": "0.1.0",
    }

    # Check LLM availability
    llm_configured = bool(settings.openai_api_key or settings.anthropic_api_key)
    health_status["llm"] = "configured" if llm_configured else "not_configured"

    if not llm_configured:
        health_status["status"] = "degraded"

    # Check Celery
    try:
        from services.patch_generator.tasks.celery_app import celery_app
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
        "service": "VulnZero Patch Generator Service",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
        },
    }


# API routes
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["patch-generator"])


class PatchGenerationRequest(BaseModel):
    vulnerability_id: int
    code_context: str
    language: str
    framework: str = None


@router.post("/generate")
async def generate_patch(request: PatchGenerationRequest):
    """
    Generate a patch for a vulnerability

    Args:
        request: Patch generation request with vulnerability details
    """
    from services.patch_generator.tasks.generation_tasks import generate_patch_task

    task = generate_patch_task.delay(
        vulnerability_id=request.vulnerability_id,
        code_context=request.code_context,
        language=request.language,
        framework=request.framework,
    )

    return {
        "task_id": task.id,
        "status": "started",
        "vulnerability_id": request.vulnerability_id,
    }


@router.get("/generate/status/{task_id}")
async def get_generation_status(task_id: str):
    """Get status of a patch generation task"""
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


class PatchValidationRequest(BaseModel):
    patch_code: str
    original_code: str
    language: str


@router.post("/validate")
async def validate_patch(request: PatchValidationRequest):
    """
    Validate a generated patch

    Args:
        request: Patch validation request
    """
    from services.patch_generator.validators.patch_validator import PatchValidator

    validator = PatchValidator()
    validation_result = validator.validate(
        patch_code=request.patch_code,
        original_code=request.original_code,
        language=request.language,
    )

    return {
        "valid": validation_result.is_valid,
        "confidence": validation_result.confidence,
        "issues": validation_result.issues,
    }


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.patch_generator.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
