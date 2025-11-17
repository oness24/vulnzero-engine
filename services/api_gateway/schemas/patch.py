"""
VulnZero API Gateway - Patch Schemas
Pydantic models for patch endpoints
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PatchBase(BaseModel):
    """Base patch schema"""
    title: str = Field(..., description="Patch title")
    patch_type: str = Field(..., description="Patch type")


class PatchCreate(PatchBase):
    """Schema for creating patch"""
    vulnerability_id: int


class PatchUpdate(BaseModel):
    """Schema for updating patch"""
    status: Optional[str] = None


class PatchResponse(PatchBase):
    """Schema for patch response"""
    id: int
    vulnerability_id: int
    status: str
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class PatchList(BaseModel):
    """Schema for paginated patch list"""
    items: List[PatchResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
