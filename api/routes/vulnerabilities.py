"""
API routes for vulnerabilities
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field
from datetime import datetime

from shared.database.session import get_db
from shared.models.models import Vulnerability, Asset, VulnerabilitySeverity
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/vulnerabilities", tags=["vulnerabilities"])


# Pydantic schemas
class VulnerabilityResponse(BaseModel):
    id: int
    cve_id: str
    title: str
    description: str
    severity: str
    cvss_score: float
    affected_systems: List[str]
    remediation: Optional[str]
    source: str
    published_date: Optional[datetime]
    priority_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VulnerabilityListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    vulnerabilities: List[VulnerabilityResponse]


class VulnerabilityStatsResponse(BaseModel):
    total_vulnerabilities: int
    by_severity: dict
    by_source: dict
    patched: int
    unpatched: int
    in_progress: int


class VulnerabilityDetailResponse(VulnerabilityResponse):
    affected_assets: List[dict]
    patches: List[dict]
    timeline: List[dict]


@router.get("/", response_model=VulnerabilityListResponse)
async def list_vulnerabilities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status (patched, unpatched)"),
    search: Optional[str] = Query(None, description="Search in CVE ID or title"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
):
    """
    List vulnerabilities with filtering and pagination
    """
    try:
        # Build query
        query = select(Vulnerability)

        # Apply filters
        if severity:
            query = query.where(Vulnerability.severity == severity)

        if source:
            query = query.where(Vulnerability.source == source)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Vulnerability.cve_id.ilike(search_pattern)) |
                (Vulnerability.title.ilike(search_pattern))
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # Apply sorting
        sort_column = getattr(Vulnerability, sort_by, Vulnerability.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await db.execute(query)
        vulnerabilities = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "vulnerabilities": vulnerabilities,
        }

    except Exception as e:
        logger.error("list_vulnerabilities_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=VulnerabilityStatsResponse)
async def get_vulnerability_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Get vulnerability statistics
    """
    try:
        # Total count
        result = await db.execute(select(func.count(Vulnerability.id)))
        total = result.scalar()

        # By severity
        result = await db.execute(
            select(
                Vulnerability.severity,
                func.count(Vulnerability.id),
            ).group_by(Vulnerability.severity)
        )
        by_severity = {severity: count for severity, count in result.all()}

        # By source
        result = await db.execute(
            select(
                Vulnerability.source,
                func.count(Vulnerability.id),
            ).group_by(Vulnerability.source)
        )
        by_source = {source: count for source, count in result.all()}

        # Status counts (simplified)
        stats = {
            "total_vulnerabilities": total,
            "by_severity": by_severity,
            "by_source": by_source,
            "patched": 0,  # Would need to join with patches
            "unpatched": total,
            "in_progress": 0,
        }

        return stats

    except Exception as e:
        logger.error("get_vulnerability_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vulnerability_id}", response_model=VulnerabilityDetailResponse)
async def get_vulnerability(
    vulnerability_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get vulnerability details
    """
    try:
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        # Get affected assets
        affected_assets = []
        for system in vulnerability.affected_systems:
            # Query assets matching the system
            result = await db.execute(
                select(Asset).where(Asset.os_version.ilike(f"%{system}%"))
            )
            assets = result.scalars().all()
            for asset in assets:
                affected_assets.append({
                    "id": asset.id,
                    "name": asset.name,
                    "ip_address": asset.ip_address,
                    "os_version": asset.os_version,
                })

        # Get patches (would need to query Patch model)
        patches = []

        # Build timeline
        timeline = [
            {
                "event": "discovered",
                "timestamp": vulnerability.created_at.isoformat(),
                "description": f"Vulnerability discovered from {vulnerability.source}",
            }
        ]

        if vulnerability.published_date:
            timeline.append({
                "event": "published",
                "timestamp": vulnerability.published_date.isoformat(),
                "description": "CVE published",
            })

        response_data = {
            **vulnerability.__dict__,
            "affected_assets": affected_assets,
            "patches": patches,
            "timeline": sorted(timeline, key=lambda x: x["timestamp"]),
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_vulnerability_failed",
            vulnerability_id=vulnerability_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vulnerability_id}/affected-assets")
async def get_affected_assets(
    vulnerability_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get assets affected by vulnerability
    """
    try:
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        affected_assets = []
        for system in vulnerability.affected_systems:
            result = await db.execute(
                select(Asset).where(Asset.os_version.ilike(f"%{system}%"))
            )
            assets = result.scalars().all()
            affected_assets.extend([
                {
                    "id": asset.id,
                    "name": asset.name,
                    "ip_address": asset.ip_address,
                    "os_version": asset.os_version,
                    "status": asset.status,
                }
                for asset in assets
            ])

        return {
            "vulnerability_id": vulnerability_id,
            "total_affected": len(affected_assets),
            "assets": affected_assets,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_affected_assets_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{vulnerability_id}/prioritize")
async def prioritize_vulnerability(
    vulnerability_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger ML-based prioritization for vulnerability
    """
    try:
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        # Import here to avoid circular dependency
        from services.aggregator.tasks import prioritize_vulnerabilities

        # Trigger async task
        task = prioritize_vulnerabilities.delay([vulnerability_id])

        return {
            "message": "Prioritization task started",
            "task_id": task.id,
            "vulnerability_id": vulnerability_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("prioritize_vulnerability_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vulnerability_id}/timeline")
async def get_vulnerability_timeline(
    vulnerability_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get vulnerability timeline (discovery, patches, deployments)
    """
    try:
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.id == vulnerability_id)
        )
        vulnerability = result.scalar_one_or_none()

        if not vulnerability:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        timeline = [
            {
                "event": "discovered",
                "timestamp": vulnerability.created_at.isoformat(),
                "description": f"Vulnerability discovered from {vulnerability.source}",
                "severity": vulnerability.severity,
            }
        ]

        if vulnerability.published_date:
            timeline.append({
                "event": "published",
                "timestamp": vulnerability.published_date.isoformat(),
                "description": "CVE officially published",
            })

        # Would add patch and deployment events here

        return {
            "vulnerability_id": vulnerability_id,
            "timeline": sorted(timeline, key=lambda x: x["timestamp"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_vulnerability_timeline_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
