"""
VulnZero API Gateway - Deployment Endpoints (Full Implementation)
Complete CRUD operations for patch deployments with database queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from datetime import datetime
import logging

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user, require_role
from services.api_gateway.schemas.deployment import (
    DeploymentResponse,
    DeploymentList,
    DeploymentCreate,
    DeploymentUpdate,
)
from shared.models import Deployment, Patch, Asset, Vulnerability, AuditLog
from shared.models.deployment import DeploymentStatus, DeploymentStrategy
from shared.models.patch import PatchStatus
from shared.models.audit_log import AuditAction, AuditResourceType

# Import Celery tasks for async execution
from services.deployment_orchestrator.tasks.deployment_tasks import deploy_patch as deploy_patch_task, rollback_deployment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=DeploymentList,
    summary="List Deployments",
    description="Get a paginated list of patch deployments with optional filtering and sorting.",
)
async def list_deployments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (pending, in_progress, completed, failed, rolled_back)"),
    strategy: Optional[str] = Query(None, description="Filter by deployment strategy"),
    patch_id: Optional[int] = Query(None, description="Filter by patch ID"),
    asset_id: Optional[int] = Query(None, description="Filter by asset ID"),
    sort_by: str = Query("created_at", description="Sort field (created_at, started_at, completed_at)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get deployment history with pagination and filtering.

    **Filters:**
    - status: pending, in_progress, completed, failed, rolled_back
    - strategy: blue_green, canary, rolling, immediate
    - patch_id: Filter by specific patch
    - asset_id: Filter by specific asset

    **Sorting:**
    - Sort by: created_at, started_at, completed_at
    - Order: asc or desc
    """
    # Build query
    query = db.query(Deployment)

    # Apply filters
    if status:
        query = query.filter(Deployment.status == status)

    if strategy:
        query = query.filter(Deployment.strategy == strategy)

    if patch_id:
        query = query.filter(Deployment.patch_id == patch_id)

    if asset_id:
        query = query.filter(Deployment.asset_id == asset_id)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Deployment, sort_by, Deployment.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    deployments = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return DeploymentList(
        items=[DeploymentResponse.from_orm(d) for d in deployments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Deployment",
    description="Create and trigger a new patch deployment.",
)
async def create_deployment(
    deployment_data: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Create and trigger a new patch deployment.
    Requires operator or admin role.
    """
    # Verify patch exists and is approved
    patch = db.query(Patch).filter(Patch.id == deployment_data.patch_id).first()
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {deployment_data.patch_id} not found"
        )

    if patch.status != PatchStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deploy patch with status '{patch.status.value}'. Patch must be approved first."
        )

    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == deployment_data.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {deployment_data.asset_id} not found"
        )

    # Generate deployment ID
    deployment_id_str = f"DEP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{deployment_data.patch_id}"

    # Create new deployment
    new_deployment = Deployment(
        deployment_id=deployment_id_str,
        patch_id=deployment_data.patch_id,
        asset_id=deployment_data.asset_id,
        strategy=deployment_data.strategy,
        status=DeploymentStatus.PENDING,
        deployment_method="automated",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_deployment)

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_DEPLOYED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.DEPLOYMENT,
        resource_id=deployment_id_str,
        resource_name=f"Deploy {patch.title} to {asset.name}",
        description=f"Deployment {deployment_id_str} created by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)

    db.commit()
    db.refresh(new_deployment)

    # Trigger async deployment via Celery
    task = deploy_patch_task.delay(
        patch_id=new_deployment.patch_id,
        asset_ids=[new_deployment.asset_id],
        strategy=new_deployment.strategy or "all-at-once",
        user_id=current_user["id"]
    )
    logger.info(f"Deployment task triggered: {task.id} for deployment {new_deployment.id}")

    return DeploymentResponse.from_orm(new_deployment)


@router.get(
    "/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Get Deployment",
    description="Get detailed information about a specific deployment.",
)
async def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get deployment details by ID"""
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found"
        )

    return DeploymentResponse.from_orm(deployment)


@router.patch(
    "/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Update Deployment",
    description="Update deployment details (status, etc.).",
)
async def update_deployment(
    deployment_id: int,
    update_data: DeploymentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Update deployment information.
    Requires operator or admin role.
    """
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.status is not None:
        old_status = deployment.status
        deployment.status = update_data.status
        changes["status"] = {"old": old_status.value if old_status else None, "new": update_data.status}

        # Update timestamps based on status
        if update_data.status == "in_progress" and not deployment.started_at:
            deployment.started_at = datetime.utcnow()
        elif update_data.status in ["completed", "failed"] and not deployment.completed_at:
            deployment.completed_at = datetime.utcnow()

    deployment.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_DEPLOYED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.DEPLOYMENT,
        resource_id=str(deployment_id),
        resource_name=deployment.deployment_id,
        description=f"Deployment {deployment.deployment_id} updated by {current_user.get('email')}",
        success=1,
        severity="info",
        changes=changes,
    )
    db.add(audit_log)

    db.commit()
    db.refresh(deployment)

    return DeploymentResponse.from_orm(deployment)


@router.delete(
    "/{deployment_id}",
    summary="Delete Deployment",
    description="Delete a deployment record (admin only).",
)
async def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    Delete deployment record.
    Requires admin role.
    """
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found"
        )

    # Prevent deletion of active deployments
    if deployment.status in [DeploymentStatus.PENDING, DeploymentStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete deployment with status '{deployment.status.value}'. Please cancel or wait for completion."
        )

    deployment_identifier = deployment.deployment_id

    # Create audit log before deletion
    audit_log = AuditLog(
        action=AuditAction.PATCH_DEPLOYED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.DEPLOYMENT,
        resource_id=str(deployment_id),
        resource_name=deployment_identifier,
        description=f"Deployment {deployment_identifier} deleted by {current_user.get('email')}",
        success=1,
        severity="high",
    )
    db.add(audit_log)

    db.delete(deployment)
    db.commit()

    return {
        "message": f"Deployment {deployment_identifier} deleted successfully",
        "id": deployment_id,
    }


@router.post(
    "/{deployment_id}/rollback",
    response_model=DeploymentResponse,
    summary="Rollback Deployment",
    description="Manually trigger deployment rollback.",
)
async def rollback_deployment(
    deployment_id: int,
    reason: Optional[str] = Query(None, description="Reason for rollback"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Manually trigger deployment rollback.
    Requires operator or admin role.
    """
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found"
        )

    # Check if deployment can be rolled back
    if deployment.status not in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot rollback deployment with status '{deployment.status.value}'"
        )

    if deployment.rollback_completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment has already been rolled back"
        )

    # Update deployment status
    old_status = deployment.status
    deployment.status = DeploymentStatus.ROLLED_BACK
    deployment.rollback_initiated_at = datetime.utcnow()
    deployment.rollback_completed_at = datetime.utcnow()
    deployment.updated_at = datetime.utcnow()

    # Update related patch status if needed
    patch = db.query(Patch).filter(Patch.id == deployment.patch_id).first()
    if patch and patch.status == PatchStatus.DEPLOYED:
        patch.status = PatchStatus.APPROVED
        patch.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_DEPLOYED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.DEPLOYMENT,
        resource_id=str(deployment_id),
        resource_name=deployment.deployment_id,
        description=f"Deployment {deployment.deployment_id} rolled back by {current_user.get('email')}{': ' + reason if reason else ''}",
        success=1,
        severity="high",
        changes={"status": {"old": old_status.value, "new": "rolled_back"}, "reason": reason},
    )
    db.add(audit_log)

    db.commit()
    db.refresh(deployment)

    # Trigger async rollback via Celery
    task = rollback_deployment.delay(
        deployment_id=deployment.id,
        reason=reason or "Manual rollback requested",
        user_id=current_user["id"]
    )
    logger.info(f"Rollback task triggered: {task.id} for deployment {deployment.id}")

    return DeploymentResponse.from_orm(deployment)


@router.post(
    "/deploy",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy Patch",
    description="Quick deployment endpoint - creates and triggers deployment in one call.",
)
async def deploy_patch(
    patch_id: int = Query(..., description="Patch ID to deploy"),
    asset_id: int = Query(..., description="Asset ID to deploy to"),
    strategy: str = Query("immediate", description="Deployment strategy"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Quick deployment endpoint.
    Creates and triggers deployment in one call.
    Requires operator or admin role.
    """
    # Verify patch exists and is approved
    patch = db.query(Patch).filter(Patch.id == patch_id).first()
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    if patch.status != PatchStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot deploy patch with status '{patch.status.value}'. Patch must be approved first."
        )

    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    # Get vulnerability for better audit logging
    vulnerability = db.query(Vulnerability).filter(Vulnerability.id == patch.vulnerability_id).first()

    # Generate deployment ID
    deployment_id_str = f"DEP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{patch_id}"

    # Create new deployment
    new_deployment = Deployment(
        deployment_id=deployment_id_str,
        patch_id=patch_id,
        asset_id=asset_id,
        strategy=strategy,
        status=DeploymentStatus.PENDING,
        deployment_method="automated",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_deployment)

    # Update patch status to deployed
    patch.status = PatchStatus.DEPLOYED
    patch.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_DEPLOYED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.DEPLOYMENT,
        resource_id=deployment_id_str,
        resource_name=f"Deploy {patch.title} to {asset.name}",
        description=f"Patch '{patch.title}' for {vulnerability.cve_id if vulnerability else 'unknown'} deployed to {asset.name} by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)

    db.commit()
    db.refresh(new_deployment)

    # Trigger async deployment via Celery
    task = deploy_patch_task.delay(
        patch_id=new_deployment.patch_id,
        asset_ids=[new_deployment.asset_id],
        strategy=new_deployment.strategy or "immediate",
        user_id=current_user["id"]
    )
    logger.info(f"Quick deployment task triggered: {task.id} for deployment {new_deployment.id}")

    return DeploymentResponse.from_orm(new_deployment)


@router.get(
    "/stats",
    summary="Get Deployment Statistics",
    description="Get dashboard statistics for deployments.",
)
async def get_deployment_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get deployment statistics for dashboard.

    Returns:
    - Total deployments
    - Deployments by status
    - Deployments by strategy
    - Success rate
    - Average deployment time
    """
    # Total deployments
    total = db.query(func.count(Deployment.id)).scalar()

    # Count by status
    by_status = {}
    for deploy_status in DeploymentStatus:
        count = db.query(func.count(Deployment.id)).filter(
            Deployment.status == deploy_status
        ).scalar()
        by_status[deploy_status.value] = count

    # Count by strategy
    by_strategy = {}
    for deploy_strategy in DeploymentStrategy:
        count = db.query(func.count(Deployment.id)).filter(
            Deployment.strategy == deploy_strategy
        ).scalar()
        by_strategy[deploy_strategy.value] = count

    # Success rate
    successful = db.query(func.count(Deployment.id)).filter(
        Deployment.status == DeploymentStatus.COMPLETED
    ).scalar()
    success_rate = (successful / total * 100) if total > 0 else 0.0

    # Failed deployments
    failed = db.query(func.count(Deployment.id)).filter(
        Deployment.status == DeploymentStatus.FAILED
    ).scalar()

    # Rolled back deployments
    rolled_back = db.query(func.count(Deployment.id)).filter(
        Deployment.status == DeploymentStatus.ROLLED_BACK
    ).scalar()

    # In progress
    in_progress = db.query(func.count(Deployment.id)).filter(
        Deployment.status == DeploymentStatus.IN_PROGRESS
    ).scalar()

    # Deployments this week
    from datetime import timedelta
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    this_week = db.query(func.count(Deployment.id)).filter(
        Deployment.created_at >= one_week_ago
    ).scalar()

    return {
        "total": total,
        "by_status": by_status,
        "by_strategy": by_strategy,
        "success_rate": round(success_rate, 2),
        "successful": successful,
        "failed": failed,
        "rolled_back": rolled_back,
        "in_progress": in_progress,
        "this_week": this_week,
    }
