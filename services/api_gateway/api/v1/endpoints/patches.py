"""
VulnZero API Gateway - Patch Endpoints (Full Implementation)
Complete CRUD operations for AI-generated patches with database queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from datetime import datetime

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user, require_role
from services.api_gateway.schemas.patch import (
    PatchResponse,
    PatchList,
    PatchCreate,
    PatchUpdate,
)
from shared.models import Patch, Vulnerability, AuditLog
from shared.models.patch import PatchStatus, PatchType
from shared.models.audit_log import AuditAction, AuditResourceType

# Import Celery task for AI patch generation
from services.patch_generator.tasks.generation_tasks import generate_patch_for_vulnerability

router = APIRouter()


@router.get(
    "",
    response_model=PatchList,
    summary="List Patches",
    description="Get a paginated list of AI-generated patches with optional filtering and sorting.",
)
async def list_patches(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status (generated, validated, approved, rejected)"),
    patch_type: Optional[str] = Query(None, description="Filter by patch type (code, config, dependency)"),
    vulnerability_id: Optional[int] = Query(None, description="Filter by vulnerability ID"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    sort_by: str = Query("confidence_score", description="Sort field (confidence_score, created_at, validation_score)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all AI-generated patches with pagination and filtering.

    **Filters:**
    - status: generated, validated, approved, rejected, deployed
    - patch_type: code, config, dependency
    - vulnerability_id: Filter by specific vulnerability
    - min_confidence: Minimum confidence score (0.0-1.0)

    **Sorting:**
    - Sort by: confidence_score, created_at, validation_score
    - Order: asc or desc
    """
    # Build query
    query = db.query(Patch)

    # Apply filters
    if status:
        query = query.filter(Patch.status == status)

    if patch_type:
        query = query.filter(Patch.patch_type == patch_type)

    if vulnerability_id:
        query = query.filter(Patch.vulnerability_id == vulnerability_id)

    if min_confidence is not None:
        query = query.filter(Patch.confidence_score >= min_confidence)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Patch, sort_by, Patch.confidence_score)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    patches = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return PatchList(
        items=[PatchResponse.from_orm(p) for p in patches],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=PatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Patch",
    description="Manually create a patch record (for AI-generated or manual patches).",
)
async def create_patch(
    patch_data: PatchCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Create a new patch record.
    Requires operator or admin role.
    """
    # Verify vulnerability exists
    vulnerability = db.query(Vulnerability).filter(
        Vulnerability.id == patch_data.vulnerability_id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {patch_data.vulnerability_id} not found"
        )

    # Create new patch
    new_patch = Patch(
        vulnerability_id=patch_data.vulnerability_id,
        title=patch_data.title,
        patch_type=patch_data.patch_type,
        status=PatchStatus.GENERATED,
        confidence_score=0.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_patch)

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_GENERATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(new_patch.id) if new_patch.id else "new",
        resource_name=patch_data.title,
        description=f"Patch '{patch_data.title}' created for {vulnerability.cve_id} by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)

    db.commit()
    db.refresh(new_patch)

    return PatchResponse.from_orm(new_patch)


@router.get(
    "/{patch_id}",
    response_model=PatchResponse,
    summary="Get Patch",
    description="Get detailed information about a specific patch.",
)
async def get_patch(
    patch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get patch by ID with full details"""
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    return PatchResponse.from_orm(patch)


@router.patch(
    "/{patch_id}",
    response_model=PatchResponse,
    summary="Update Patch",
    description="Update patch details (status, etc.).",
)
async def update_patch(
    patch_id: int,
    update_data: PatchUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Update patch information.
    Requires operator or admin role.
    """
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.status is not None:
        old_status = patch.status
        patch.status = update_data.status
        changes["status"] = {"old": old_status.value if old_status else None, "new": update_data.status}

    patch.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_APPROVED if update_data.status == "approved" else AuditAction.PATCH_GENERATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(patch_id),
        resource_name=patch.title,
        description=f"Patch '{patch.title}' updated by {current_user.get('email')}",
        success=1,
        severity="info",
        changes=changes,
    )
    db.add(audit_log)

    db.commit()
    db.refresh(patch)

    return PatchResponse.from_orm(patch)


@router.delete(
    "/{patch_id}",
    summary="Delete Patch",
    description="Delete a patch (admin only).",
)
async def delete_patch(
    patch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    Delete patch.
    Requires admin role.
    """
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    # Check if patch is already deployed
    if patch.status == PatchStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a deployed patch. Please roll back the deployment first."
        )

    patch_title = patch.title

    # Create audit log before deletion
    audit_log = AuditLog(
        action=AuditAction.PATCH_GENERATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(patch_id),
        resource_name=patch_title,
        description=f"Patch '{patch_title}' deleted by {current_user.get('email')}",
        success=1,
        severity="high",
    )
    db.add(audit_log)

    db.delete(patch)
    db.commit()

    return {
        "message": f"Patch '{patch_title}' deleted successfully",
        "id": patch_id,
    }


@router.post(
    "/{patch_id}/approve",
    response_model=PatchResponse,
    summary="Approve Patch",
    description="Approve a patch for deployment.",
)
async def approve_patch(
    patch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Approve patch for deployment.
    Requires operator or admin role.
    """
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    # Check if patch is in appropriate status
    if patch.status not in [PatchStatus.GENERATED, PatchStatus.VALIDATED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve patch with status '{patch.status.value}'"
        )

    # Update patch status
    old_status = patch.status
    patch.status = PatchStatus.APPROVED
    patch.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_APPROVED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(patch_id),
        resource_name=patch.title,
        description=f"Patch '{patch.title}' approved by {current_user.get('email')}",
        success=1,
        severity="info",
        changes={"status": {"old": old_status.value, "new": "approved"}},
    )
    db.add(audit_log)

    db.commit()
    db.refresh(patch)

    return PatchResponse.from_orm(patch)


@router.post(
    "/{patch_id}/reject",
    summary="Reject Patch",
    description="Reject a patch and prevent deployment.",
)
async def reject_patch(
    patch_id: int,
    reason: Optional[str] = Query(None, description="Reason for rejection"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Reject patch.
    Requires operator or admin role.
    """
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found"
        )

    # Check if patch is already deployed
    if patch.status == PatchStatus.DEPLOYED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject a deployed patch. Please roll back the deployment first."
        )

    # Update patch status
    old_status = patch.status
    patch.status = PatchStatus.REJECTED
    patch.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_GENERATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(patch_id),
        resource_name=patch.title,
        description=f"Patch '{patch.title}' rejected by {current_user.get('email')}{': ' + reason if reason else ''}",
        success=1,
        severity="info",
        changes={"status": {"old": old_status.value, "new": "rejected"}, "reason": reason},
    )
    db.add(audit_log)

    db.commit()
    db.refresh(patch)

    return {
        "message": f"Patch '{patch.title}' rejected successfully",
        "patch_id": patch_id,
        "status": patch.status.value,
    }


@router.post(
    "/generate",
    summary="Generate Patch",
    description="Trigger AI patch generation for a vulnerability.",
)
async def generate_patch(
    vulnerability_id: int = Query(..., description="Vulnerability ID to generate patch for"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Trigger AI-based patch generation for a vulnerability.
    Requires operator or admin role.
    """
    # Verify vulnerability exists
    vulnerability = db.query(Vulnerability).filter(
        Vulnerability.id == vulnerability_id
    ).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vulnerability_id} not found"
        )

    # Check if vulnerability already has patches
    existing_patches = db.query(func.count(Patch.id)).filter(
        Patch.vulnerability_id == vulnerability_id,
        Patch.status.in_([PatchStatus.GENERATED, PatchStatus.VALIDATED, PatchStatus.APPROVED, PatchStatus.DEPLOYED])
    ).scalar()

    if existing_patches > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vulnerability already has {existing_patches} active patch(es). Review existing patches first."
        )

    # Trigger Celery task for AI patch generation
    task = generate_patch_for_vulnerability.delay(
        vulnerability_id=vulnerability_id,
        llm_provider="openai"  # Default to OpenAI, can be made configurable
    )

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.PATCH_GENERATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.PATCH,
        resource_id=str(vulnerability_id),
        resource_name=vulnerability.cve_id,
        description=f"Patch generation triggered for {vulnerability.cve_id} by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)
    db.commit()

    return {
        "message": "Patch generation triggered successfully",
        "vulnerability_id": vulnerability_id,
        "cve_id": vulnerability.cve_id,
        "triggered_by": current_user.get("email"),
        "task_id": task.id,  # Celery task ID for tracking
        "status": "processing"
    }


@router.get(
    "/stats",
    summary="Get Patch Statistics",
    description="Get dashboard statistics for patches.",
)
async def get_patch_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get patch statistics for dashboard.

    Returns:
    - Total patches
    - Patches by status
    - Patches by type
    - Average confidence score
    - Approval rate
    """
    # Total patches
    total = db.query(func.count(Patch.id)).scalar()

    # Count by status
    by_status = {}
    for patch_status in PatchStatus:
        count = db.query(func.count(Patch.id)).filter(
            Patch.status == patch_status
        ).scalar()
        by_status[patch_status.value] = count

    # Count by type
    by_type = {}
    for patch_type in PatchType:
        count = db.query(func.count(Patch.id)).filter(
            Patch.patch_type == patch_type
        ).scalar()
        by_type[patch_type.value] = count

    # Average confidence score
    avg_confidence = db.query(func.avg(Patch.confidence_score)).scalar() or 0.0

    # Approval rate
    approved_count = db.query(func.count(Patch.id)).filter(
        Patch.status.in_([PatchStatus.APPROVED, PatchStatus.DEPLOYED])
    ).scalar()
    approval_rate = (approved_count / total * 100) if total > 0 else 0.0

    # High confidence patches (>= 0.8)
    high_confidence = db.query(func.count(Patch.id)).filter(
        Patch.confidence_score >= 0.8
    ).scalar()

    # Deployed patches
    deployed = db.query(func.count(Patch.id)).filter(
        Patch.status == PatchStatus.DEPLOYED
    ).scalar()

    return {
        "total": total,
        "by_status": by_status,
        "by_type": by_type,
        "avg_confidence_score": round(avg_confidence, 3),
        "approval_rate": round(approval_rate, 2),
        "high_confidence": high_confidence,
        "deployed": deployed,
    }
