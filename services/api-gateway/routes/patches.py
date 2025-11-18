"""
Patch management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from shared.models.database import get_db
from shared.models.models import Patch, TestStatus
from shared.models.schemas import PatchResponse, PatchApproval, PatchRejection
from services.api_gateway.auth import get_current_active_user, require_operator

router = APIRouter()


@router.get("", response_model=list[PatchResponse])
async def list_patches(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    test_status: TestStatus | None = None,
    vulnerability_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    List all patches with filtering and pagination
    """
    query = select(Patch)

    # Apply filters
    if test_status:
        query = query.where(Patch.test_status == test_status)
    if vulnerability_id:
        query = query.where(Patch.vulnerability_id == vulnerability_id)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Patch.created_at.desc())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    patches = result.scalars().all()

    return patches


@router.get("/{patch_id}", response_model=PatchResponse)
async def get_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a specific patch by ID
    """
    query = select(Patch).where(Patch.id == patch_id)
    result = await db.execute(query)
    patch = result.scalar_one_or_none()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found",
        )

    return patch


@router.post("/{patch_id}/approve", response_model=PatchResponse)
async def approve_patch(
    patch_id: int,
    approval_data: PatchApproval,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Approve a patch for deployment
    """
    query = select(Patch).where(Patch.id == patch_id)
    result = await db.execute(query)
    patch = result.scalar_one_or_none()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found",
        )

    # Check if patch has passed testing
    if patch.test_status != TestStatus.PASSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve patch that hasn't passed testing",
        )

    # Approve patch
    patch.approved_by = approval_data.approved_by
    patch.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(patch)

    # Note: Approved patches will be automatically deployed by the auto_deploy_tested_patches
    # scheduled task, or can be manually deployed via the deployments endpoint.
    # This separation of approval and deployment provides better control.

    return patch


@router.post("/{patch_id}/reject", response_model=PatchResponse)
async def reject_patch(
    patch_id: int,
    rejection_data: PatchRejection,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Reject a patch
    """
    query = select(Patch).where(Patch.id == patch_id)
    result = await db.execute(query)
    patch = result.scalar_one_or_none()

    if not patch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patch with ID {patch_id} not found",
        )

    # Reject patch
    patch.rejection_reason = rejection_data.rejection_reason
    patch.test_status = TestStatus.FAILED

    await db.commit()
    await db.refresh(patch)

    return patch
