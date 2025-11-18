"""
API routes for patches
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field
from datetime import datetime

from shared.database.session import get_db
from shared.models.models import Patch, Vulnerability, PatchStatus
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/patches", tags=["patches"])


# Pydantic schemas
class PatchResponse(BaseModel):
    id: int
    vulnerability_id: int
    patch_script: str
    rollback_script: str
    validation_script: Optional[str]
    status: str
    test_results: Optional[dict]
    confidence_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatchListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    patches: List[PatchResponse]


class PatchDetailResponse(PatchResponse):
    vulnerability: dict
    deployments: List[dict]
    test_history: List[dict]


class PatchCreateRequest(BaseModel):
    vulnerability_id: int
    patch_script: str
    rollback_script: str
    validation_script: Optional[str] = None


class PatchStatusUpdate(BaseModel):
    status: str = Field(..., description="New status (pending, approved, rejected, deployed)")
    reason: Optional[str] = Field(None, description="Reason for status change")


@router.get("/", response_model=PatchListResponse)
async def list_patches(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    vulnerability_id: Optional[int] = Query(None, description="Filter by vulnerability"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    List patches with filtering and pagination
    """
    try:
        query = select(Patch)

        # Apply filters
        if status:
            query = query.where(Patch.status == status)

        if vulnerability_id:
            query = query.where(Patch.vulnerability_id == vulnerability_id)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply sorting
        sort_column = getattr(Patch, sort_by, Patch.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        patches = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "patches": patches,
        }

    except Exception as e:
        logger.error("list_patches_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patch_id}", response_model=PatchDetailResponse)
async def get_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get patch details
    """
    try:
        result = await db.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        # Get vulnerability
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == patch.vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        vulnerability_data = {
            "id": vulnerability.id,
            "cve_id": vulnerability.cve_id,
            "title": vulnerability.title,
            "severity": vulnerability.severity,
        } if vulnerability else {}

        # Get deployments (would query Deployment model)
        deployments = []

        # Build test history
        test_history = []
        if patch.test_results:
            test_history.append({
                "timestamp": patch.updated_at.isoformat(),
                "results": patch.test_results,
                "status": patch.status,
            })

        response_data = {
            **patch.__dict__,
            "vulnerability": vulnerability_data,
            "deployments": deployments,
            "test_history": test_history,
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_patch_failed", patch_id=patch_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=PatchResponse)
async def create_patch(
    patch_data: PatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new patch
    """
    try:
        # Verify vulnerability exists
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == patch_data.vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        # Create patch
        patch = Patch(
            vulnerability_id=patch_data.vulnerability_id,
            patch_script=patch_data.patch_script,
            rollback_script=patch_data.rollback_script,
            validation_script=patch_data.validation_script,
            status=PatchStatus.PENDING,
        )

        db.add(patch)
        await db.commit()
        await db.refresh(patch)

        logger.info("patch_created", patch_id=patch.id, vulnerability_id=vulnerability.id)

        return patch

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_patch_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{patch_id}/generate")
async def generate_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger AI-based patch generation
    """
    try:
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == patch_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        # Import here to avoid circular dependency
        from services.patch_generator.tasks import generate_patch as generate_patch_task

        # Trigger async task
        task = generate_patch_task.delay(vulnerability.id)

        return {
            "message": "Patch generation task started",
            "task_id": task.id,
            "vulnerability_id": vulnerability.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("generate_patch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{patch_id}/test")
async def test_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger patch testing in digital twin
    """
    try:
        result = await db.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        # Import here to avoid circular dependency
        from services.testing_engine.tasks import test_patch as test_patch_task

        # Trigger async task
        task = test_patch_task.delay(patch.id)

        return {
            "message": "Patch testing task started",
            "task_id": task.id,
            "patch_id": patch.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_patch_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{patch_id}/status", response_model=PatchResponse)
async def update_patch_status(
    patch_id: int,
    status_update: PatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update patch status (approve, reject, etc.)
    """
    try:
        result = await db.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        # Validate status
        valid_statuses = ["pending", "approved", "rejected", "deployed", "failed"]
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )

        # Update status
        patch.status = status_update.status

        # Add status change to metadata
        if not patch.test_results:
            patch.test_results = {}

        if "status_history" not in patch.test_results:
            patch.test_results["status_history"] = []

        patch.test_results["status_history"].append({
            "status": status_update.status,
            "reason": status_update.reason,
            "timestamp": datetime.utcnow().isoformat(),
        })

        await db.commit()
        await db.refresh(patch)

        logger.info(
            "patch_status_updated",
            patch_id=patch.id,
            new_status=status_update.status,
        )

        return patch

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_patch_status_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patch_id}/test-results")
async def get_test_results(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get patch test results
    """
    try:
        result = await db.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        return {
            "patch_id": patch.id,
            "status": patch.status,
            "test_results": patch.test_results or {},
            "confidence_score": patch.confidence_score,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_test_results_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{patch_id}")
async def delete_patch(
    patch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a patch
    """
    try:
        result = await db.execute(
            select(Patch).where(Patch.id == patch_id)
        )
        patch = result.scalar_one_or_none()

        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        # Check if patch is deployed
        if patch.status == PatchStatus.DEPLOYED:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete deployed patch. Rollback first."
            )

        await db.delete(patch)
        await db.commit()

        logger.info("patch_deleted", patch_id=patch_id)

        return {"message": "Patch deleted successfully", "patch_id": patch_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_patch_failed", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_patch_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get patch statistics
    """
    try:
        # Total count
        result = await db.execute(select(func.count(Patch.id)))
        total = result.scalar()

        # By status
        result = await db.execute(
            select(
                Patch.status,
                func.count(Patch.id),
            ).group_by(Patch.status)
        )
        by_status = {status: count for status, count in result.all()}

        # Average confidence score
        result = await db.execute(
            select(func.avg(Patch.confidence_score))
        )
        avg_confidence = result.scalar() or 0.0

        return {
            "total_patches": total,
            "by_status": by_status,
            "average_confidence": float(avg_confidence),
        }

    except Exception as e:
        logger.error("get_patch_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
