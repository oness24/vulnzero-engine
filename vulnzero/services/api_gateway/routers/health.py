"""Health check and monitoring endpoints."""
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vulnzero.shared.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "VulnZero API Gateway",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/database")
async def database_health(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Check database connectivity.

    Args:
        db: Database session

    Returns:
        Database health status
    """
    try:
        # Simple query to test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "component": "database",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "component": "database",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.

    Args:
        db: Database session

    Returns:
        Readiness status
    """
    try:
        # Check database connectivity
        db.execute("SELECT 1")

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
