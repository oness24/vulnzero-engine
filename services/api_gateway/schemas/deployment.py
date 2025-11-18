"""
VulnZero API Gateway - Deployment Schemas
Pydantic models for deployment endpoints
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DeploymentBase(BaseModel):
    """Base deployment schema"""
    patch_id: int = Field(..., description="Patch ID")
    asset_id: int = Field(..., description="Asset ID")
    strategy: str = Field(..., description="Deployment strategy")


class DeploymentCreate(DeploymentBase):
    """Schema for creating deployment"""
    pass


class DeploymentUpdate(BaseModel):
    """Schema for updating deployment"""
    status: Optional[str] = None


class DeploymentResponse(DeploymentBase):
    """Schema for deployment response"""
    id: int
    deployment_id: str
    status: str
    deployment_method: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DeploymentList(BaseModel):
    """Schema for paginated deployment list"""
    items: List[DeploymentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
