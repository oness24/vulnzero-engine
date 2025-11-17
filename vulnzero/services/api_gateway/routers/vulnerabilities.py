"""Vulnerability management endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from vulnzero.services.patch_generator.storage import PatchStorageService
from vulnzero.shared.models import Vulnerability, VulnerabilitySeverity, VulnerabilityStatus

from ..dependencies import get_db_session, get_storage_service

router = APIRouter()


# Pydantic schemas for request/response
class VulnerabilityResponse(BaseModel):
    """Vulnerability response schema."""

    id: int
    cve_id: str
    title: str
    description: str
    severity: str
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    status: str
    package_name: Optional[str] = None
    vulnerable_version: Optional[str] = None
    fixed_version: Optional[str] = None
    priority_score: float
    patch_count: int = 0
    discovered_at: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class VulnerabilityCreateRequest(BaseModel):
    """Vulnerability creation request schema."""

    cve_id: str = Field(..., min_length=1, max_length=50)
    title: Optional[str] = None
    description: str = Field(default="")
    severity: str = Field(default="medium")
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    cvss_vector: Optional[str] = None
    package_name: Optional[str] = None
    vulnerable_version: Optional[str] = None
    fixed_version: Optional[str] = None


class VulnerabilityListResponse(BaseModel):
    """Paginated vulnerability list response."""

    vulnerabilities: List[VulnerabilityResponse]
    total: int
    page: int
    page_size: int


class VulnerabilityStatisticsResponse(BaseModel):
    """Vulnerability statistics response."""

    total_vulnerabilities: int
    by_severity: dict
    by_status: dict
    average_cvss: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int


@router.get("/vulnerabilities", response_model=VulnerabilityListResponse)
async def list_vulnerabilities(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db_session),
) -> VulnerabilityListResponse:
    """
    List all vulnerabilities with optional filtering.

    Args:
        severity: Filter by severity (critical, high, medium, low)
        status: Filter by status
        page: Page number
        page_size: Items per page
        db: Database session

    Returns:
        Paginated list of vulnerabilities
    """
    # Build query
    query = db.query(Vulnerability)

    # Apply filters
    if severity:
        if severity.lower() not in ["critical", "high", "medium", "low", "unknown"]:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        query = query.filter(Vulnerability.severity == severity.lower())

    if status:
        try:
            vuln_status = VulnerabilityStatus[status.upper()]
            query = query.filter(Vulnerability.status == vuln_status)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    vulnerabilities = (
        query.order_by(Vulnerability.discovered_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Convert to response models
    vuln_responses = []
    for v in vulnerabilities:
        # Count patches for this vulnerability
        patch_count = len(v.patches) if hasattr(v, "patches") else 0

        vuln_responses.append(
            VulnerabilityResponse(
                id=v.id,
                cve_id=v.cve_id,
                title=v.title,
                description=v.description,
                severity=v.severity,
                cvss_score=v.cvss_score,
                cvss_vector=v.cvss_vector,
                status=v.status,
                package_name=v.package_name,
                vulnerable_version=v.vulnerable_version,
                fixed_version=v.fixed_version,
                priority_score=v.priority_score,
                patch_count=patch_count,
                discovered_at=v.discovered_at.isoformat() if v.discovered_at else v.created_at.isoformat(),
                created_at=v.created_at.isoformat(),
                updated_at=v.updated_at.isoformat(),
            )
        )

    return VulnerabilityListResponse(
        vulnerabilities=vuln_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/vulnerabilities/{vulnerability_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vulnerability_id: int,
    db: Session = Depends(get_db_session),
) -> VulnerabilityResponse:
    """
    Get detailed information about a specific vulnerability.

    Args:
        vulnerability_id: Vulnerability ID
        db: Database session

    Returns:
        Detailed vulnerability information

    Raises:
        HTTPException: If vulnerability not found
    """
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vulnerability_id).first()

    if not vuln:
        raise HTTPException(
            status_code=404, detail=f"Vulnerability {vulnerability_id} not found"
        )

    # Count patches
    patch_count = len(vuln.patches) if hasattr(vuln, "patches") else 0

    return VulnerabilityResponse(
        id=vuln.id,
        cve_id=vuln.cve_id,
        title=vuln.title,
        description=vuln.description,
        severity=vuln.severity,
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        status=vuln.status,
        package_name=vuln.package_name,
        vulnerable_version=vuln.vulnerable_version,
        fixed_version=vuln.fixed_version,
        priority_score=vuln.priority_score,
        patch_count=patch_count,
        discovered_at=vuln.discovered_at.isoformat() if vuln.discovered_at else vuln.created_at.isoformat(),
        created_at=vuln.created_at.isoformat(),
        updated_at=vuln.updated_at.isoformat(),
    )


@router.get("/vulnerabilities/cve/{cve_id}", response_model=VulnerabilityResponse)
async def get_vulnerability_by_cve(
    cve_id: str,
    storage: PatchStorageService = Depends(get_storage_service),
) -> VulnerabilityResponse:
    """
    Get vulnerability by CVE ID.

    Args:
        cve_id: CVE identifier (e.g., CVE-2023-1234)
        storage: Patch storage service

    Returns:
        Vulnerability information

    Raises:
        HTTPException: If CVE not found
    """
    vuln = storage.get_vulnerability_by_cve(cve_id)

    if not vuln:
        raise HTTPException(status_code=404, detail=f"CVE {cve_id} not found")

    # Count patches
    patch_count = len(vuln.patches) if hasattr(vuln, "patches") else 0

    return VulnerabilityResponse(
        id=vuln.id,
        cve_id=vuln.cve_id,
        title=vuln.title,
        description=vuln.description,
        severity=vuln.severity,
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        status=vuln.status,
        package_name=vuln.package_name,
        vulnerable_version=vuln.vulnerable_version,
        fixed_version=vuln.fixed_version,
        priority_score=vuln.priority_score,
        patch_count=patch_count,
        discovered_at=vuln.discovered_at.isoformat() if vuln.discovered_at else vuln.created_at.isoformat(),
        created_at=vuln.created_at.isoformat(),
        updated_at=vuln.updated_at.isoformat(),
    )


@router.post("/vulnerabilities", response_model=VulnerabilityResponse, status_code=201)
async def create_vulnerability(
    request: VulnerabilityCreateRequest,
    storage: PatchStorageService = Depends(get_storage_service),
) -> VulnerabilityResponse:
    """
    Create or update a vulnerability.

    Args:
        request: Vulnerability creation request
        storage: Patch storage service

    Returns:
        Created or updated vulnerability information
    """
    # Prepare CVE data
    cve_data = {
        "cve_id": request.cve_id,
        "title": request.title or f"Vulnerability {request.cve_id}",
        "description": request.description,
        "severity": request.severity,
        "cvss_score": request.cvss_score,
        "cvss_vector": request.cvss_vector,
        "package_name": request.package_name,
        "vulnerable_version": request.vulnerable_version,
        "fixed_version": request.fixed_version,
    }

    # Create or update vulnerability
    vuln = storage.create_or_update_vulnerability(cve_data)

    # Count patches
    patch_count = len(vuln.patches) if hasattr(vuln, "patches") else 0

    return VulnerabilityResponse(
        id=vuln.id,
        cve_id=vuln.cve_id,
        title=vuln.title,
        description=vuln.description,
        severity=vuln.severity,
        cvss_score=vuln.cvss_score,
        cvss_vector=vuln.cvss_vector,
        status=vuln.status,
        package_name=vuln.package_name,
        vulnerable_version=vuln.vulnerable_version,
        fixed_version=vuln.fixed_version,
        priority_score=vuln.priority_score,
        patch_count=patch_count,
        discovered_at=vuln.discovered_at.isoformat() if vuln.discovered_at else vuln.created_at.isoformat(),
        created_at=vuln.created_at.isoformat(),
        updated_at=vuln.updated_at.isoformat(),
    )


@router.get("/vulnerabilities/stats", response_model=VulnerabilityStatisticsResponse)
async def get_vulnerability_statistics(
    db: Session = Depends(get_db_session),
) -> VulnerabilityStatisticsResponse:
    """
    Get vulnerability statistics.

    Args:
        db: Database session

    Returns:
        Vulnerability statistics including counts by severity and status
    """
    # Total count
    total = db.query(Vulnerability).count()

    # Count by severity
    critical_count = (
        db.query(Vulnerability)
        .filter(Vulnerability.severity == VulnerabilitySeverity.CRITICAL)
        .count()
    )
    high_count = (
        db.query(Vulnerability)
        .filter(Vulnerability.severity == VulnerabilitySeverity.HIGH)
        .count()
    )
    medium_count = (
        db.query(Vulnerability)
        .filter(Vulnerability.severity == VulnerabilitySeverity.MEDIUM)
        .count()
    )
    low_count = (
        db.query(Vulnerability)
        .filter(Vulnerability.severity == VulnerabilitySeverity.LOW)
        .count()
    )

    # Count by status
    by_status = {}
    for status in VulnerabilityStatus:
        count = db.query(Vulnerability).filter(Vulnerability.status == status).count()
        by_status[status.value] = count

    # Average CVSS score
    avg_cvss = (
        db.query(Vulnerability)
        .with_entities(db.func.avg(Vulnerability.cvss_score))
        .scalar()
    )

    return VulnerabilityStatisticsResponse(
        total_vulnerabilities=total,
        by_severity={
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        },
        by_status=by_status,
        average_cvss=float(avg_cvss or 0.0),
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
    )
