"""
Vulnerability management routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from shared.models.database import get_db
from shared.models.models import Vulnerability, VulnerabilityStatus, VulnerabilitySeverity
from shared.models.schemas import (
    VulnerabilityResponse,
    VulnerabilityCreate,
    VulnerabilityUpdate,
    VulnerabilityListResponse,
    VulnerabilityStats,
)
from services.api_gateway.auth import get_current_active_user, require_operator

router = APIRouter()


@router.get("", response_model=VulnerabilityListResponse)
async def list_vulnerabilities(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    severity: VulnerabilitySeverity | None = None,
    status: VulnerabilityStatus | None = None,
    min_cvss: float | None = Query(None, ge=0.0, le=10.0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    List all vulnerabilities with filtering and pagination
    """
    # Build query
    query = select(Vulnerability)

    # Apply filters
    if severity:
        query = query.where(Vulnerability.severity == severity)
    if status:
        query = query.where(Vulnerability.status == status)
    if min_cvss is not None:
        query = query.where(Vulnerability.cvss_score >= min_cvss)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Vulnerability.priority_score.desc())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    vulnerabilities = result.scalars().all()

    return {
        "items": vulnerabilities,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/stats", response_model=VulnerabilityStats)
async def get_vulnerability_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get vulnerability statistics for dashboard
    """
    # Total count
    total_query = select(func.count()).select_from(Vulnerability)
    result = await db.execute(total_query)
    total = result.scalar() or 0

    # Count by severity
    severity_query = select(
        Vulnerability.severity, func.count(Vulnerability.id)
    ).group_by(Vulnerability.severity)
    result = await db.execute(severity_query)
    by_severity = {str(severity): count for severity, count in result.all()}

    # Count by status
    status_query = select(
        Vulnerability.status, func.count(Vulnerability.id)
    ).group_by(Vulnerability.status)
    result = await db.execute(status_query)
    by_status = {str(status): count for status, count in result.all()}

    # Calculate remediation rate
    remediated_query = select(func.count()).select_from(Vulnerability).where(
        Vulnerability.status == VulnerabilityStatus.REMEDIATED
    )
    result = await db.execute(remediated_query)
    remediated = result.scalar() or 0
    remediation_rate = (remediated / total * 100) if total > 0 else 0

    return {
        "total": total,
        "by_severity": by_severity,
        "by_status": by_status,
        "remediation_rate": round(remediation_rate, 2),
        "avg_time_to_remediate": None,  # TODO: Calculate from deployment data
    }


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vuln_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a specific vulnerability by ID
    """
    query = select(Vulnerability).where(Vulnerability.id == vuln_id)
    result = await db.execute(query)
    vulnerability = result.scalar_one_or_none()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vuln_id} not found",
        )

    return vulnerability


@router.post("", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_vulnerability(
    vulnerability_data: VulnerabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Create a new vulnerability (typically called by scanners)
    """
    # Check if vulnerability with same CVE ID already exists
    query = select(Vulnerability).where(Vulnerability.cve_id == vulnerability_data.cve_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Vulnerability with CVE ID {vulnerability_data.cve_id} already exists",
        )

    # Create new vulnerability
    vulnerability = Vulnerability(**vulnerability_data.model_dump())
    db.add(vulnerability)
    await db.commit()
    await db.refresh(vulnerability)

    return vulnerability


@router.patch("/{vuln_id}", response_model=VulnerabilityResponse)
async def update_vulnerability(
    vuln_id: int,
    update_data: VulnerabilityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Update a vulnerability
    """
    query = select(Vulnerability).where(Vulnerability.id == vuln_id)
    result = await db.execute(query)
    vulnerability = result.scalar_one_or_none()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vuln_id} not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(vulnerability, field, value)

    await db.commit()
    await db.refresh(vulnerability)

    return vulnerability


@router.post("/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Trigger a manual vulnerability scan

    This will enqueue a Celery task to scan all configured vulnerability scanners.
    """
    # TODO: Trigger Celery task for scanning
    # from services.aggregator.tasks import scan_all_sources
    # task = scan_all_sources.delay()

    return {
        "message": "Vulnerability scan triggered",
        "task_id": "mock-task-id",  # TODO: Return actual Celery task ID
    }
