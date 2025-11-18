"""
Asset management routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from shared.models.database import get_db
from shared.models.models import Asset, AssetType, AssetVulnerability
from shared.models.schemas import AssetResponse, AssetCreate, AssetUpdate, AssetWithVulnerabilities
from services.api_gateway.auth import get_current_active_user, require_operator

router = APIRouter()


@router.get("", response_model=list[AssetWithVulnerabilities])
async def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    asset_type: AssetType | None = None,
    is_active: bool | None = None,
    environment: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    List all assets with filtering and pagination
    """
    query = select(Asset)

    # Apply filters
    if asset_type:
        query = query.where(Asset.type == asset_type)
    if is_active is not None:
        query = query.where(Asset.is_active == is_active)
    if environment:
        query = query.where(Asset.environment == environment)

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Asset.created_at.desc())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    assets = result.scalars().all()

    # Get vulnerability counts for each asset
    assets_with_vulns = []
    for asset in assets:
        # Count total vulnerabilities
        vuln_count_query = select(func.count()).select_from(AssetVulnerability).where(
            AssetVulnerability.asset_id == asset.id,
            AssetVulnerability.resolved_at.is_(None)
        )
        result = await db.execute(vuln_count_query)
        vuln_count = result.scalar() or 0

        # Count vulnerabilities by severity
        from shared.models.models import VulnerabilitySeverity

        severity_count_query = select(
            Vulnerability.severity,
            func.count(Vulnerability.id)
        ).select_from(
            AssetVulnerability
        ).join(
            Vulnerability,
            AssetVulnerability.vulnerability_id == Vulnerability.id
        ).where(
            AssetVulnerability.asset_id == asset.id,
            AssetVulnerability.resolved_at.is_(None)
        ).group_by(Vulnerability.severity)

        result = await db.execute(severity_count_query)
        severity_counts = {str(severity): count for severity, count in result.all()}

        asset_dict = {
            **asset.__dict__,
            "vulnerability_count": vuln_count,
            "critical_count": severity_counts.get(VulnerabilitySeverity.CRITICAL.value, 0),
            "high_count": severity_counts.get(VulnerabilitySeverity.HIGH.value, 0),
            "medium_count": severity_counts.get(VulnerabilitySeverity.MEDIUM.value, 0),
            "low_count": severity_counts.get(VulnerabilitySeverity.LOW.value, 0),
        }
        assets_with_vulns.append(asset_dict)

    return assets_with_vulns


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get a specific asset by ID
    """
    query = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found",
        )

    return asset


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Register a new asset
    """
    # Check if asset with same asset_id already exists
    query = select(Asset).where(Asset.asset_id == asset_data.asset_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with asset_id {asset_data.asset_id} already exists",
        )

    # Create new asset
    asset = Asset(**asset_data.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: int,
    update_data: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_operator),
):
    """
    Update an asset
    """
    query = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)

    return asset


@router.get("/{asset_id}/vulnerabilities")
async def get_asset_vulnerabilities(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """
    Get all vulnerabilities affecting a specific asset
    """
    # Verify asset exists
    query = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found",
        )

    # Get asset vulnerabilities
    query = (
        select(AssetVulnerability)
        .where(AssetVulnerability.asset_id == asset_id)
        .options(selectinload(AssetVulnerability.vulnerability))
    )
    result = await db.execute(query)
    asset_vulns = result.scalars().all()

    return [
        {
            "vulnerability": av.vulnerability,
            "detected_at": av.detected_at,
            "resolved_at": av.resolved_at,
        }
        for av in asset_vulns
    ]
