"""
VulnZero API Gateway - Asset Endpoints (Full Implementation)
Complete CRUD operations for infrastructure assets with database queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from datetime import datetime

from services.api_gateway.core.dependencies import get_db
from services.api_gateway.core.security import get_current_user, require_role
from services.api_gateway.schemas.asset import (
    AssetResponse,
    AssetList,
    AssetCreate,
    AssetUpdate,
)
from services.api_gateway.schemas.vulnerability import VulnerabilityResponse, VulnerabilityList
from shared.models import Asset, Vulnerability, AuditLog
from shared.models.asset import AssetType, AssetStatus
from shared.models.audit_log import AuditAction, AuditResourceType

router = APIRouter()


@router.get(
    "",
    response_model=AssetList,
    summary="List Assets",
    description="Get a paginated list of infrastructure assets with optional filtering and sorting.",
)
async def list_assets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (server, container, cloud_resource, database)"),
    environment: Optional[str] = Query(None, description="Filter by environment (production, staging, development)"),
    status: Optional[str] = Query(None, description="Filter by status (active, inactive, decommissioned)"),
    search: Optional[str] = Query(None, description="Search in asset ID, name, hostname, or IP"),
    min_criticality: Optional[int] = Query(None, ge=1, le=5, description="Minimum criticality level (1-5)"),
    sort_by: str = Query("vulnerability_count", description="Sort field (vulnerability_count, criticality, created_at)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all infrastructure assets with pagination and filtering.

    **Filters:**
    - asset_type: server, container, cloud_resource, database
    - environment: production, staging, development
    - status: active, inactive, decommissioned
    - min_criticality: Minimum criticality level (1-5)
    - search: Search in asset ID, name, hostname, or IP

    **Sorting:**
    - Sort by: vulnerability_count, criticality, created_at, risk_score
    - Order: asc or desc
    """
    # Build query
    query = db.query(Asset)

    # Apply filters
    if asset_type:
        query = query.filter(Asset.type == asset_type)

    if environment:
        query = query.filter(Asset.environment == environment)

    if status:
        query = query.filter(Asset.status == status)

    if min_criticality:
        query = query.filter(Asset.criticality >= min_criticality)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Asset.asset_id.ilike(search_term),
                Asset.name.ilike(search_term),
                Asset.hostname.ilike(search_term),
                Asset.ip_address.ilike(search_term)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Asset, sort_by, Asset.vulnerability_count)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    assets = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return AssetList(
        items=[AssetResponse.from_orm(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Asset",
    description="Register a new infrastructure asset in the inventory.",
)
async def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Register a new asset in the inventory.
    Requires operator or admin role.
    """
    # Check if asset_id already exists
    existing_asset = db.query(Asset).filter(Asset.asset_id == asset_data.asset_id).first()
    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with ID '{asset_data.asset_id}' already exists"
        )

    # Create new asset
    new_asset = Asset(
        asset_id=asset_data.asset_id,
        name=asset_data.name,
        type=asset_data.type,
        status=AssetStatus.ACTIVE,
        vulnerability_count=0,
        criticality=3,  # Default to medium criticality
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_asset)

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.ASSET_DISCOVERED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.ASSET,
        resource_id=asset_data.asset_id,
        resource_name=asset_data.name,
        description=f"Asset '{asset_data.name}' registered by {current_user.get('email')}",
        success=1,
        severity="info",
    )
    db.add(audit_log)

    db.commit()
    db.refresh(new_asset)

    return AssetResponse.from_orm(new_asset)


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get Asset",
    description="Get detailed information about a specific asset.",
)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get asset by ID with vulnerability count"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    return AssetResponse.from_orm(asset)


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update Asset",
    description="Update asset details (status, criticality, etc.).",
)
async def update_asset(
    asset_id: int,
    update_data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("operator")),
):
    """
    Update asset information.
    Requires operator or admin role.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    # Track changes for audit log
    changes = {}

    # Update fields
    if update_data.status is not None:
        old_status = asset.status
        asset.status = update_data.status
        changes["status"] = {"old": old_status.value if old_status else None, "new": update_data.status}

    if update_data.criticality is not None:
        old_criticality = asset.criticality
        asset.criticality = update_data.criticality
        changes["criticality"] = {"old": old_criticality, "new": update_data.criticality}

    asset.updated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        action=AuditAction.ASSET_UPDATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.ASSET,
        resource_id=str(asset_id),
        resource_name=asset.name,
        description=f"Asset '{asset.name}' updated by {current_user.get('email')}",
        success=1,
        severity="info",
        changes=changes,
    )
    db.add(audit_log)

    db.commit()
    db.refresh(asset)

    return AssetResponse.from_orm(asset)


@router.delete(
    "/{asset_id}",
    summary="Delete Asset",
    description="Delete an asset from inventory (admin only).",
)
async def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """
    Delete asset from inventory.
    Requires admin role.
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    asset_name = asset.name
    asset_identifier = asset.asset_id

    # Check if asset has active vulnerabilities
    active_vulns = db.query(func.count(Vulnerability.id)).filter(
        Vulnerability.asset_id == asset_id,
        Vulnerability.status != "remediated"
    ).scalar()

    if active_vulns > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete asset with {active_vulns} active vulnerabilities. Remediate or reassign them first."
        )

    # Create audit log before deletion
    audit_log = AuditLog(
        action=AuditAction.ASSET_UPDATED,
        timestamp=datetime.utcnow(),
        actor_type="user",
        actor_id=current_user["id"],
        actor_name=current_user.get("email", "Unknown"),
        resource_type=AuditResourceType.ASSET,
        resource_id=str(asset_id),
        resource_name=asset_name,
        description=f"Asset '{asset_name}' ({asset_identifier}) deleted by {current_user.get('email')}",
        success=1,
        severity="high",
    )
    db.add(audit_log)

    db.delete(asset)
    db.commit()

    return {
        "message": f"Asset '{asset_name}' deleted successfully",
        "id": asset_id,
        "asset_id": asset_identifier,
    }


@router.get(
    "/{asset_id}/vulnerabilities",
    response_model=VulnerabilityList,
    summary="Get Asset Vulnerabilities",
    description="Get all vulnerabilities affecting this asset.",
)
async def get_asset_vulnerabilities(
    asset_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all vulnerabilities affecting a specific asset.

    Supports pagination and filtering by severity/status.
    """
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    # Build query for vulnerabilities
    query = db.query(Vulnerability).filter(Vulnerability.asset_id == asset_id)

    # Apply filters
    if severity:
        query = query.filter(Vulnerability.severity == severity)

    if status:
        query = query.filter(Vulnerability.status == status)

    # Get total count
    total = query.count()

    # Apply pagination and sorting (by priority score by default)
    offset = (page - 1) * page_size
    vulnerabilities = query.order_by(Vulnerability.priority_score.desc()).offset(offset).limit(page_size).all()

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
    "/stats",
    summary="Get Asset Statistics",
    description="Get dashboard statistics for assets.",
)
async def get_asset_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get asset statistics for dashboard.

    Returns:
    - Total assets
    - Assets by type
    - Assets by environment
    - Assets by status
    - High-risk assets (criticality >= 4)
    """
    # Total assets
    total = db.query(func.count(Asset.id)).scalar()

    # Count by type
    by_type = {}
    for asset_type in AssetType:
        count = db.query(func.count(Asset.id)).filter(
            Asset.type == asset_type
        ).scalar()
        by_type[asset_type.value] = count

    # Count by status
    by_status = {}
    for asset_status in AssetStatus:
        count = db.query(func.count(Asset.id)).filter(
            Asset.status == asset_status
        ).scalar()
        by_status[asset_status.value] = count

    # Count by environment
    environments = db.query(Asset.environment, func.count(Asset.id)).group_by(Asset.environment).all()
    by_environment = {env[0]: env[1] for env in environments if env[0]}

    # High-risk assets (criticality >= 4)
    high_risk = db.query(func.count(Asset.id)).filter(
        Asset.criticality >= 4
    ).scalar()

    # Active assets
    active = db.query(func.count(Asset.id)).filter(
        Asset.status == AssetStatus.ACTIVE
    ).scalar()

    # Assets with vulnerabilities
    with_vulnerabilities = db.query(func.count(Asset.id)).filter(
        Asset.vulnerability_count > 0
    ).scalar()

    return {
        "total": total,
        "active": active,
        "by_type": by_type,
        "by_status": by_status,
        "by_environment": by_environment,
        "high_risk": high_risk,
        "with_vulnerabilities": with_vulnerabilities,
    }
