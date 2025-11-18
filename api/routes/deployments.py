"""
API routes for deployments
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field
from datetime import datetime

from shared.database.session import get_db
from shared.models.models import Deployment, Patch, Asset, DeploymentStatus
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/deployments", tags=["deployments"])


# Pydantic schemas
class DeploymentResponse(BaseModel):
    id: int
    patch_id: int
    status: str
    strategy: str
    results: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    deployments: List[DeploymentResponse]


class DeploymentDetailResponse(DeploymentResponse):
    patch: dict
    assets: List[dict]
    monitoring_status: Optional[dict]


class DeploymentCreateRequest(BaseModel):
    patch_id: int
    asset_ids: List[int]
    strategy: str = Field(
        default="rolling",
        description="Deployment strategy (rolling, blue_green, canary)"
    )
    strategy_options: Optional[dict] = Field(
        default=None,
        description="Strategy-specific options"
    )


class DeploymentStatsResponse(BaseModel):
    total_deployments: int
    by_status: dict
    by_strategy: dict
    success_rate: float
    average_duration: Optional[float]


@router.get("/", response_model=DeploymentListResponse)
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    patch_id: Optional[int] = Query(None, description="Filter by patch"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    List deployments with filtering and pagination
    """
    try:
        query = select(Deployment)

        # Apply filters
        if status:
            query = query.where(Deployment.status == status)

        if patch_id:
            query = query.where(Deployment.patch_id == patch_id)

        if strategy:
            query = query.where(Deployment.strategy == strategy)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply sorting
        sort_column = getattr(Deployment, sort_by, Deployment.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        deployments = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "deployments": deployments,
        }

    except Exception as e:
        logger.error("list_deployments_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}", response_model=DeploymentDetailResponse)
async def get_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get deployment details
    """
    try:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Get patch
        result = await db.execute(
            select(Patch).where(Patch.id == deployment.patch_id)
        )
        patch = result.scalar_one_or_none()

        patch_data = {
            "id": patch.id,
            "vulnerability_id": patch.vulnerability_id,
            "status": patch.status,
        } if patch else {}

        # Get assets from results
        assets = deployment.results.get("assets", []) if deployment.results else []

        # Get monitoring status (would query monitoring service)
        monitoring_status = None

        response_data = {
            **deployment.__dict__,
            "patch": patch_data,
            "assets": assets,
            "monitoring_status": monitoring_status,
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_deployment_failed", deployment_id=deployment_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment_data: DeploymentCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create and start a new deployment
    """
    try:
        # Verify patch exists
        result = await db.execute(
            select(Patch).where(Patch.id == deployment_data.patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        # Verify assets exist
        result = await db.execute(
            select(Asset).where(Asset.id.in_(deployment_data.asset_ids))
        )
        assets = result.scalars().all()

        if len(assets) != len(deployment_data.asset_ids):
            raise HTTPException(status_code=404, detail="Some assets not found")

        # Create deployment
        deployment = Deployment(
            patch_id=deployment_data.patch_id,
            status=DeploymentStatus.PENDING,
            strategy=deployment_data.strategy,
            results={},
        )

        db.add(deployment)
        await db.commit()
        await db.refresh(deployment)

        logger.info(
            "deployment_created",
            deployment_id=deployment.id,
            patch_id=patch.id,
            asset_count=len(assets),
        )

        # Trigger deployment task
        from services.deployment_engine.tasks import deploy_patch

        task = deploy_patch.delay(
            patch.id,
            deployment_data.asset_ids,
            deployment_data.strategy,
            deployment_data.strategy_options,
        )

        return deployment

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_deployment_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger deployment rollback
    """
    try:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        if deployment.status != DeploymentStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Can only rollback completed deployments"
            )

        # Trigger rollback task
        from services.deployment_engine.tasks import rollback_deployment as rollback_task

        task = rollback_task.delay(deployment.id)

        return {
            "message": "Rollback task started",
            "task_id": task.id,
            "deployment_id": deployment.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rollback_deployment_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{deployment_id}/verify")
async def verify_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger deployment verification
    """
    try:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Trigger verification task
        from services.deployment_engine.tasks import verify_deployment as verify_task

        task = verify_task.delay(deployment.id)

        return {
            "message": "Verification task started",
            "task_id": task.id,
            "deployment_id": deployment.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("verify_deployment_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}/status")
async def get_deployment_status(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time deployment status
    """
    try:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Calculate progress
        results = deployment.results or {}
        total_assets = results.get("total_assets", 0)
        successful = results.get("successful", 0)
        failed = results.get("failed", 0)
        in_progress = total_assets - (successful + failed)

        progress = (successful + failed) / total_assets * 100 if total_assets > 0 else 0

        return {
            "deployment_id": deployment.id,
            "status": deployment.status,
            "strategy": deployment.strategy,
            "progress": progress,
            "total_assets": total_assets,
            "successful": successful,
            "failed": failed,
            "in_progress": in_progress,
            "started_at": deployment.started_at,
            "completed_at": deployment.completed_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_deployment_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=DeploymentStatsResponse)
async def get_deployment_stats(
    hours: int = Query(24, description="Time period in hours"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deployment statistics
    """
    try:
        from datetime import timedelta

        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Total count (within time period)
        result = await db.execute(
            select(func.count(Deployment.id)).where(
                Deployment.created_at >= cutoff
            )
        )
        total = result.scalar()

        # By status
        result = await db.execute(
            select(
                Deployment.status,
                func.count(Deployment.id),
            ).where(
                Deployment.created_at >= cutoff
            ).group_by(Deployment.status)
        )
        by_status = {status: count for status, count in result.all()}

        # By strategy
        result = await db.execute(
            select(
                Deployment.strategy,
                func.count(Deployment.id),
            ).where(
                Deployment.created_at >= cutoff
            ).group_by(Deployment.strategy)
        )
        by_strategy = {strategy: count for strategy, count in result.all()}

        # Calculate success rate
        completed = by_status.get(DeploymentStatus.COMPLETED.value, 0)
        failed = by_status.get(DeploymentStatus.FAILED.value, 0)
        success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0.0

        # Average duration (simplified - would need duration calculation)
        average_duration = None

        return {
            "total_deployments": total,
            "by_status": by_status,
            "by_strategy": by_strategy,
            "success_rate": success_rate,
            "average_duration": average_duration,
        }

    except Exception as e:
        logger.error("get_deployment_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deployment logs
    """
    try:
        result = await db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")

        # Get logs from results
        logs = []
        if deployment.results:
            # Extract asset-level logs
            for asset_result in deployment.results.get("assets", []):
                if "logs" in asset_result:
                    logs.extend(asset_result["logs"])

        # Sort by timestamp and limit
        logs = sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

        return {
            "deployment_id": deployment.id,
            "total_logs": len(logs),
            "logs": logs,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_deployment_logs_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
