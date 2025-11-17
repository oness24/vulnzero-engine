"""
VulnZero API Gateway - Asset Schemas
Pydantic models for asset endpoints
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """Base asset schema"""
    asset_id: str = Field(..., description="Unique asset identifier")
    name: str = Field(..., description="Asset name")
    type: str = Field(..., description="Asset type")


class AssetCreate(AssetBase):
    """Schema for creating asset"""
    pass


class AssetUpdate(BaseModel):
    """Schema for updating asset"""
    status: Optional[str] = None
    criticality: Optional[int] = None


class AssetResponse(AssetBase):
    """Schema for asset response"""
    id: int
    status: str
    hostname: Optional[str]
    ip_address: Optional[str]
    environment: Optional[str]
    vulnerability_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class AssetList(BaseModel):
    """Schema for paginated asset list"""
    items: List[AssetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
