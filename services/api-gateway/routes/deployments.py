"""
Deployment management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from shared.models.database import get_db
from shared.models.models import Deployment, DeploymentStatus
from shared.models.schemas import (
    DeploymentResponse,
    DeploymentWithDetails,
    DeploymentRollback,
)
from services.api_gateway.auth import get_current_active_user, require_operator

router = APIRouter()


@router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: DeploymentStatus | None = None,
    asset_id: int | None = None,
    patch_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    List all deployments with filtering and pagination
    """
    query = select(Deployment)

    # Apply filters
    if status:
        query = query.where(Deployment.status == status)
    if asset_id:
        query = query.where(Deployment.asset_id == asset_id)
    if patch_id:
        query = query.where(Deployment.patch_id == patch_id)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Deployment.created_at.desc())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    deployments = result.scalars().all()

    return deployments


@router.get("/{deployment_id}", response_model=DeploymentWithDetails)
async def get_deployment(
    deployment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a specific deployment by ID with full details
    """
    query = (
        select(Deployment)
        .where(Deployment.id == deployment_id)
        .options(selectinload(Deployment.patch))
        .options(selectinload(Deployment.asset))
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found",
        )

    return deployment


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    deployment_id: int,
    rollback_data: DeploymentRollback,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Manually trigger rollback of a deployment
    """
    query = select(Deployment).where(Deployment.id == deployment_id)
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found",
        )

    # Check if deployment can be rolled back
    if deployment.status not in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot rollback deployment with status: {deployment.status}",
        )

    if deployment.status == DeploymentStatus.ROLLED_BACK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment has already been rolled back",
        )

    # Mark for rollback
    deployment.rollback_required = True
    deployment.rollback_reason = rollback_data.reason
    deployment.status = DeploymentStatus.ROLLED_BACK
    deployment.rolled_back_at = datetime.utcnow()

    await db.commit()
    await db.refresh(deployment)

    # TODO: Trigger rollback job
    # from services.deployment_engine.tasks import execute_rollback
    # execute_rollback.delay(deployment_id)

    return deployment
