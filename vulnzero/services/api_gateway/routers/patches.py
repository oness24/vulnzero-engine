"""Patch management endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vulnzero.services.patch_generator.storage import PatchStorageService
from vulnzero.shared.models import PatchStatus

from ..dependencies import get_db_session, get_storage_service

router = APIRouter()


# Pydantic schemas for request/response
class PatchResponse(BaseModel):
    """Patch response schema."""

    id: int
    patch_id: str
    vulnerability_id: int
    cve_id: str
    status: str
    confidence_score: float
    llm_model: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    test_status: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PatchDetailResponse(PatchResponse):
    """Detailed patch response with content."""

    patch_content: str
    rollback_script: Optional[str] = None
    test_report: Optional[str] = None
    validation_report: Optional[str] = None


class PatchApprovalRequest(BaseModel):
    """Patch approval request schema."""

    approver: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None


class PatchRejectionRequest(BaseModel):
    """Patch rejection request schema."""

    rejector: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=1)


class PatchListResponse(BaseModel):
    """Paginated patch list response."""

    patches: List[PatchResponse]
    total: int
    page: int
    page_size: int


class PatchStatisticsResponse(BaseModel):
    """Patch statistics response."""

    total_patches: int
    approved: int
    rejected: int
    pending_review: int
    average_confidence: float
    approval_rate: float


@router.get("/patches", response_model=PatchListResponse)
async def list_patches(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    storage: PatchStorageService = Depends(get_storage_service),
) -> PatchListResponse:
    """
    List all patches with optional filtering.

    Args:
        status: Filter by patch status
        page: Page number
        page_size: Items per page
        storage: Patch storage service

    Returns:
        Paginated list of patches
    """
    # Get patches based on status filter
    if status:
        try:
            patch_status = PatchStatus[status.upper()]
            all_patches = storage.get_patches_by_status(patch_status, limit=1000)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        all_patches = storage.get_recent_patches(limit=1000)

    # Calculate pagination
    total = len(all_patches)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_patches = all_patches[start_idx:end_idx]

    # Convert to response models
    patch_responses = [
        PatchResponse(
            id=p.id,
            patch_id=p.patch_id,
            vulnerability_id=p.vulnerability_id,
            cve_id=p.vulnerability.cve_id,
            status=p.status,
            confidence_score=p.confidence_score,
            llm_model=p.llm_model,
            approved_by=p.approved_by,
            approved_at=p.approved_at.isoformat() if p.approved_at else None,
            rejection_reason=p.rejection_reason,
            test_status=p.test_status,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in paginated_patches
    ]

    return PatchListResponse(
        patches=patch_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/patches/{patch_id}", response_model=PatchDetailResponse)
async def get_patch(
    patch_id: str,
    storage: PatchStorageService = Depends(get_storage_service),
) -> PatchDetailResponse:
    """
    Get detailed information about a specific patch.

    Args:
        patch_id: Patch identifier
        storage: Patch storage service

    Returns:
        Detailed patch information

    Raises:
        HTTPException: If patch not found
    """
    patch = storage.get_patch_by_id(patch_id)

    if not patch:
        raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")

    return PatchDetailResponse(
        id=patch.id,
        patch_id=patch.patch_id,
        vulnerability_id=patch.vulnerability_id,
        cve_id=patch.vulnerability.cve_id,
        status=patch.status,
        confidence_score=patch.confidence_score,
        llm_model=patch.llm_model,
        approved_by=patch.approved_by,
        approved_at=patch.approved_at.isoformat() if patch.approved_at else None,
        rejection_reason=patch.rejection_reason,
        test_status=patch.test_status,
        created_at=patch.created_at.isoformat(),
        updated_at=patch.updated_at.isoformat(),
        patch_content=patch.patch_content,
        rollback_script=patch.rollback_script,
        test_report=patch.test_report,
        validation_report=patch.validation_report,
    )


@router.post("/patches/{patch_id}/approve", response_model=PatchResponse)
async def approve_patch(
    patch_id: str,
    request: PatchApprovalRequest,
    storage: PatchStorageService = Depends(get_storage_service),
) -> PatchResponse:
    """
    Approve a patch for deployment.

    Args:
        patch_id: Patch identifier
        request: Approval request with approver info
        storage: Patch storage service

    Returns:
        Updated patch information

    Raises:
        HTTPException: If patch not found or validation error
    """
    try:
        patch = storage.approve_patch(patch_id, request.approver, request.notes)

        return PatchResponse(
            id=patch.id,
            patch_id=patch.patch_id,
            vulnerability_id=patch.vulnerability_id,
            cve_id=patch.vulnerability.cve_id,
            status=patch.status,
            confidence_score=patch.confidence_score,
            llm_model=patch.llm_model,
            approved_by=patch.approved_by,
            approved_at=patch.approved_at.isoformat() if patch.approved_at else None,
            rejection_reason=patch.rejection_reason,
            test_status=patch.test_status,
            created_at=patch.created_at.isoformat(),
            updated_at=patch.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/patches/{patch_id}/reject", response_model=PatchResponse)
async def reject_patch(
    patch_id: str,
    request: PatchRejectionRequest,
    storage: PatchStorageService = Depends(get_storage_service),
) -> PatchResponse:
    """
    Reject a patch.

    Args:
        patch_id: Patch identifier
        request: Rejection request with rejector and reason
        storage: Patch storage service

    Returns:
        Updated patch information

    Raises:
        HTTPException: If patch not found or validation error
    """
    try:
        patch = storage.reject_patch(patch_id, request.rejector, request.reason)

        return PatchResponse(
            id=patch.id,
            patch_id=patch.patch_id,
            vulnerability_id=patch.vulnerability_id,
            cve_id=patch.vulnerability.cve_id,
            status=patch.status,
            confidence_score=patch.confidence_score,
            llm_model=patch.llm_model,
            approved_by=patch.approved_by,
            approved_at=patch.approved_at.isoformat() if patch.approved_at else None,
            rejection_reason=patch.rejection_reason,
            test_status=patch.test_status,
            created_at=patch.created_at.isoformat(),
            updated_at=patch.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/patches/stats", response_model=PatchStatisticsResponse)
async def get_patch_statistics(
    storage: PatchStorageService = Depends(get_storage_service),
) -> PatchStatisticsResponse:
    """
    Get patch statistics.

    Args:
        storage: Patch storage service

    Returns:
        Patch statistics including approval rate and average confidence
    """
    stats = storage.get_statistics()

    return PatchStatisticsResponse(
        total_patches=stats["total_patches"],
        approved=stats["approved"],
        rejected=stats["rejected"],
        pending_review=stats["pending_review"],
        average_confidence=stats["average_confidence"],
        approval_rate=stats["approval_rate"],
    )


@router.get("/patches/vulnerability/{vulnerability_id}", response_model=List[PatchResponse])
async def get_patches_for_vulnerability(
    vulnerability_id: int,
    storage: PatchStorageService = Depends(get_storage_service),
) -> List[PatchResponse]:
    """
    Get all patches for a specific vulnerability.

    Args:
        vulnerability_id: Vulnerability ID
        storage: Patch storage service

    Returns:
        List of patches for the vulnerability
    """
    patches = storage.get_patches_for_vulnerability(vulnerability_id)

    return [
        PatchResponse(
            id=p.id,
            patch_id=p.patch_id,
            vulnerability_id=p.vulnerability_id,
            cve_id=p.vulnerability.cve_id,
            status=p.status,
            confidence_score=p.confidence_score,
            llm_model=p.llm_model,
            approved_by=p.approved_by,
            approved_at=p.approved_at.isoformat() if p.approved_at else None,
            rejection_reason=p.rejection_reason,
            test_status=p.test_status,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in patches
    ]
