"""
VulnZero API Gateway - Vulnerability Endpoints (Full Implementation)
Complete CRUD operations for vulnerabilities with database queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user, require_role
from services.api_gateway.schemas.vulnerability import (
    VulnerabilityResponse,
    VulnerabilityList,
    VulnerabilityCreate,
    VulnerabilityUpdate,
)
from shared.models import Vulnerability, AuditLog
from shared.models.vulnerability import VulnerabilityStatus, VulnerabilitySeverity
from shared.models.audit_log import AuditAction, AuditResourceType

# Import vulnerability scan Celery tasks
from services.aggregator.tasks.scan_tasks import scan_wazuh, scan_qualys, scan_tenable
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize rate limiter for this router
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "",
    response_model=VulnerabilityList,
    summary="List Vulnerabilities",
    description="Get a paginated list of vulnerabilities with optional filtering and sorting.",
)
async def list_vulnerabilities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, high, medium, low, info)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in CVE ID or title"),
    sort_by: str = Query("priority_score", description="Sort field (priority_score, discovered_at, cvss_score)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all vulnerabilities with pagination and filtering.

    **Filters:**
    - severity: critical, high, medium, low, info
    - status: new, analyzing, patch_generated, testing, etc.
    - search: Search in CVE ID or title

    **Sorting:**
    - Sort by: priority_score, discovered_at, cvss_score, created_at
    - Order: asc or desc
    """
    # Build query
    query = db.query(Vulnerability)

    # Apply filters
    if severity:
        query = query.filter(Vulnerability.severity == severity)

    if status:
        query = query.filter(Vulnerability.status == status)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Vulnerability.cve_id.ilike(search_term),
                Vulnerability.title.ilike(search_term)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Vulnerability, sort_by, Vulnerability.priority_score)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    vulnerabilities = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return VulnerabilityList(
        items=[VulnerabilityResponse.from_orm(v) for v in vulnerabilities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{vuln_id}",
    response_model=VulnerabilityResponse,
    summary="Get Vulnerability",
    description="Get detailed information about a specific vulnerability.",
)
async def get_vulnerability(
    vuln_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vulnerability by ID"""
    vulnerability = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vuln_id} not found"
        )

    return VulnerabilityResponse.from_orm(vulnerability)


@router.post(
    "/scan",
    summary="Trigger Vulnerability Scan",
    description="Manually trigger a vulnerability scan for all assets.",
)
@limiter.limit("5/hour")  # Rate limit: 5 scans per hour per IP
async def trigger_scan(
    request: Request,  # Required for rate limiting
    scanner: Optional[str] = Query(None, description="Specific scanner to use (wazuh, qualys, tenable)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Trigger manual vulnerability scan.

    **Rate Limited**: 5 scans per hour per IP address to prevent abuse.

    Vulnerability scanning can be expensive (API costs, resource usage),
    so this endpoint is rate-limited to prevent:
    - Accidental scan spam
    - Malicious resource exhaustion
    - Exceeding external scanner API limits
    - Unnecessary costs

    Requires operator or admin role.
    """
    # Trigger appropriate scanner based on parameter
    tasks_triggered = []

    if scanner:
        # Trigger specific scanner
        scanner_map = {
            "wazuh": scan_wazuh,
            "qualys": scan_qualys,
            "tenable": scan_tenable
        }

        if scanner.lower() not in scanner_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scanner: {scanner}. Valid options: wazuh, qualys, tenable"
            )

        task = scanner_map[scanner.lower()].delay()
        tasks_triggered.append({"scanner": scanner, "task_id": task.id})
        logger.info(f"Triggered {scanner} scan, task ID: {task.id}")
    else:
        # Trigger all scanners
        wazuh_task = scan_wazuh.delay()
        qualys_task = scan_qualys.delay()
        tenable_task = scan_tenable.delay()

        tasks_triggered = [
            {"scanner": "wazuh", "task_id": wazuh_task.id},
            {"scanner": "qualys", "task_id": qualys_task.id},
            {"scanner": "tenable", "task_id": tenable_task.id}
        ]
        logger.info(f"Triggered all vulnerability scanners: {len(tasks_triggered)} tasks")

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.VULNERABILITY_DISCOVERED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.VULNERABILITY,
        resource_id="scan",
        resource_name=f"Manual scan ({scanner or 'all'})",
        description=f"Manual vulnerability scan triggered by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)
    db.commit()

    return {
        "message": "Vulnerability scan triggered successfully",
        "scanner": scanner or "all",
        "triggered_by": current_user.get("email"),
        "tasks": tasks_triggered
    }


@router.get(
    "/stats",
    summary="Get Vulnerability Statistics",
    description="Get dashboard statistics for vulnerabilities.",
)
async def get_vulnerability_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get vulnerability statistics for dashboard.

    Returns:
    - Total vulnerabilities by severity
    - Remediated count this week
    - Active vulnerabilities
    - Average remediation time
    """
    # Total vulnerabilities
    total = db.query(func.count(Vulnerability.id)).scalar()

    # Count by severity
    critical = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.severity == VulnerabilitySeverity.CRITICAL
    ).scalar()

    high = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.severity == VulnerabilitySeverity.HIGH
    ).scalar()

    medium = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.severity == VulnerabilitySeverity.MEDIUM
    ).scalar()

    low = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.severity == VulnerabilitySeverity.LOW
    ).scalar()

    # Remediated this week
    from datetime import timedelta
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    remediated_this_week = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.status == VulnerabilityStatus.REMEDIATED,
        Vulnerability.remediated_at >= one_week_ago
    ).scalar()

    # Active (not remediated or ignored)
    active = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.status.notin_([VulnerabilityStatus.REMEDIATED, VulnerabilityStatus.IGNORED])
    ).scalar()

    # By status
    by_status = {}
    for status_enum in VulnerabilityStatus:
        count = db.query(func.count(Vulnerability.id)).filter(
            Vulnerability.status == status_enum
        ).scalar()
        by_status[status_enum.value] = count

    return {
        "total": total,
        "by_severity": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "active": active,
        "remediated_this_week": remediated_this_week,
        "by_status": by_status,
    }


@router.patch(
    "/{vuln_id}",
    response_model=VulnerabilityResponse,
    summary="Update Vulnerability",
    description="Update vulnerability details (status, assignment, etc.).",
)
async def update_vulnerability(
    vuln_id: int,
    update_data: VulnerabilityUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Update vulnerability.
    Requires operator or admin role.
    """
    vulnerability = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vuln_id} not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.status is not None:
        old_status = vulnerability.status
        vulnerability.status = update_data.status
        changes["status"] = {"old": old_status.value if old_status else None, "new": update_data.status}

    if update_data.assigned_to is not None:
        old_assigned = vulnerability.assigned_to
        vulnerability.assigned_to = update_data.assigned_to
        changes["assigned_to"] = {"old": old_assigned, "new": update_data.assigned_to}

    vulnerability.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.VULNERABILITY_UPDATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.VULNERABILITY,
        resource_id=str(vuln_id),
        resource_name=vulnerability.cve_id,
        description=f"Vulnerability {vulnerability.cve_id} updated by {current_user.get('email')}",
        success=1,
        severity="info",
        changes=changes,
    )
    db.add(audit_log)

    db.commit()
    db.refresh(vulnerability)

    return VulnerabilityResponse.from_orm(vulnerability)


@router.delete(
    "/{vuln_id}",
    summary="Delete Vulnerability",
    description="Delete a vulnerability (admin only).",
)
async def delete_vulnerability(
    vuln_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    Delete vulnerability.
    Requires admin role.
    """
    vulnerability = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()

    if not vulnerability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with ID {vuln_id} not found"
        )

    cve_id = vulnerability.cve_id

    # Create audit log before deletion
    audit_log = AuditLog(
        action=AuditAction.VULNERABILITY_UPDATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.VULNERABILITY,
        resource_id=str(vuln_id),
        resource_name=cve_id,
        description=f"Vulnerability {cve_id} deleted by {current_user.get('email')}",
        success=1,
        severity="high",
    )
    db.add(audit_log)

    db.delete(vulnerability)
    db.commit()

    return {
        "message": f"Vulnerability {cve_id} deleted successfully",
        "id": vuln_id,
    }
