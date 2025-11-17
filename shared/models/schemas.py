"""
Pydantic schemas for API request/response validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from shared.models.models import (
    VulnerabilityStatus,
    VulnerabilitySeverity,
    AssetType,
    TestStatus,
    DeploymentStatus,
    DeploymentMethod,
    JobStatus,
)


# Base schemas with common configuration
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(from_attributes=True)


# Vulnerability Schemas
class VulnerabilityBase(BaseSchema):
    """Base vulnerability schema"""
    cve_id: str = Field(..., description="CVE identifier")
    title: str = Field(..., description="Vulnerability title")
    description: Optional[str] = Field(None, description="Detailed description")
    severity: VulnerabilitySeverity = Field(..., description="Severity level")
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="CVSS score")
    cvss_vector: Optional[str] = Field(None, description="CVSS vector string")
    affected_package: Optional[str] = Field(None, description="Affected package name")
    vulnerable_version: Optional[str] = Field(None, description="Vulnerable version")
    fixed_version: Optional[str] = Field(None, description="Fixed version")


class VulnerabilityCreate(VulnerabilityBase):
    """Schema for creating a vulnerability"""
    scanner_source: Optional[str] = None
    raw_scanner_data: Optional[Dict[str, Any]] = None


class VulnerabilityUpdate(BaseSchema):
    """Schema for updating a vulnerability"""
    status: Optional[VulnerabilityStatus] = None
    priority_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    epss_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    exploit_available: Optional[bool] = None


class VulnerabilityResponse(VulnerabilityBase):
    """Schema for vulnerability response"""
    id: int
    status: VulnerabilityStatus
    priority_score: float
    epss_score: Optional[float] = None
    exploit_available: bool
    discovered_at: datetime
    remediated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VulnerabilityListResponse(BaseSchema):
    """Schema for paginated vulnerability list"""
    items: List[VulnerabilityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VulnerabilityStats(BaseSchema):
    """Dashboard statistics for vulnerabilities"""
    total: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    remediation_rate: float
    avg_time_to_remediate: Optional[float] = None


# Asset Schemas
class AssetBase(BaseSchema):
    """Base asset schema"""
    asset_id: str = Field(..., description="Unique asset identifier")
    type: AssetType = Field(..., description="Asset type")
    hostname: str = Field(..., description="Hostname")
    ip_address: Optional[str] = Field(None, description="IP address")
    os_type: Optional[str] = Field(None, description="Operating system type")
    os_version: Optional[str] = Field(None, description="OS version")
    os_architecture: Optional[str] = Field(None, description="Architecture (x86_64, arm64, etc.)")
    criticality: int = Field(default=5, ge=1, le=10, description="Criticality score (1-10)")
    environment: Optional[str] = Field(None, description="Environment (prod, staging, dev)")
    tags: Optional[Dict[str, Any]] = Field(None, description="Custom tags")


class AssetCreate(AssetBase):
    """Schema for creating an asset"""
    ssh_user: Optional[str] = None
    ssh_port: int = Field(default=22)


class AssetUpdate(BaseSchema):
    """Schema for updating an asset"""
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    criticality: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None
    tags: Optional[Dict[str, Any]] = None


class AssetResponse(AssetBase):
    """Schema for asset response"""
    id: int
    is_active: bool
    last_scanned: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AssetWithVulnerabilities(AssetResponse):
    """Asset with vulnerability count"""
    vulnerability_count: int = 0
    critical_count: int = 0
    high_count: int = 0


# Patch Schemas
class PatchBase(BaseSchema):
    """Base patch schema"""
    patch_type: str = Field(..., description="Patch type (script, ansible, terraform)")
    patch_content: str = Field(..., description="Patch content/script")
    rollback_content: Optional[str] = Field(None, description="Rollback script")


class PatchCreate(PatchBase):
    """Schema for creating a patch"""
    vulnerability_id: int
    llm_provider: str
    llm_model: str
    llm_prompt: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class PatchUpdate(BaseSchema):
    """Schema for updating a patch"""
    test_status: Optional[TestStatus] = None
    test_results: Optional[Dict[str, Any]] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class PatchResponse(PatchBase):
    """Schema for patch response"""
    id: int
    patch_id: str
    vulnerability_id: int
    llm_provider: str
    llm_model: str
    confidence_score: float
    validation_passed: bool
    test_status: TestStatus
    test_results: Optional[Dict[str, Any]] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class PatchApproval(BaseSchema):
    """Schema for patch approval"""
    approved_by: str = Field(..., description="User approving the patch")
    notes: Optional[str] = Field(None, description="Approval notes")


class PatchRejection(BaseSchema):
    """Schema for patch rejection"""
    rejection_reason: str = Field(..., description="Reason for rejection")
    rejected_by: str = Field(..., description="User rejecting the patch")


# Deployment Schemas
class DeploymentBase(BaseSchema):
    """Base deployment schema"""
    patch_id: int
    asset_id: int
    deployment_method: DeploymentMethod
    deployment_strategy: str = Field(..., description="Deployment strategy")


class DeploymentCreate(DeploymentBase):
    """Schema for creating a deployment"""
    scheduled_at: Optional[datetime] = None


class DeploymentUpdate(BaseSchema):
    """Schema for updating a deployment"""
    status: Optional[DeploymentStatus] = None
    execution_logs: Optional[str] = None
    error_message: Optional[str] = None


class DeploymentResponse(DeploymentBase):
    """Schema for deployment response"""
    id: int
    deployment_id: str
    status: DeploymentStatus
    execution_logs: Optional[str] = None
    error_message: Optional[str] = None
    rollback_required: bool
    rollback_reason: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeploymentWithDetails(DeploymentResponse):
    """Deployment with related patch and asset info"""
    patch: Optional[PatchResponse] = None
    asset: Optional[AssetResponse] = None


class DeploymentRollback(BaseSchema):
    """Schema for deployment rollback"""
    reason: str = Field(..., description="Reason for rollback")
    requested_by: str = Field(..., description="User requesting rollback")


# Remediation Job Schemas
class RemediationJobCreate(BaseSchema):
    """Schema for creating a remediation job"""
    job_type: str = Field(..., description="Job type")
    priority: int = Field(default=5, ge=1, le=10)
    input_data: Optional[Dict[str, Any]] = None


class RemediationJobResponse(BaseSchema):
    """Schema for remediation job response"""
    id: int
    job_id: str
    job_type: str
    status: JobStatus
    priority: int
    input_data: Optional[Dict[str, Any]] = None
    result_data: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Authentication Schemas
class Token(BaseSchema):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseSchema):
    """Token refresh request"""
    refresh_token: str


class UserLogin(BaseSchema):
    """User login request"""
    username: str
    password: str


class User(BaseSchema):
    """User response"""
    id: int
    username: str
    email: str
    is_active: bool
    role: str


# Health & System Schemas
class HealthResponse(BaseSchema):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]


class MetricsResponse(BaseSchema):
    """Metrics response"""
    vulnerabilities_scanned: int
    patches_generated: int
    deployments_completed: int
    remediation_rate: float
    avg_time_to_remediate: float


# Pagination
class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


# Filter Schemas
class VulnerabilityFilter(PaginationParams):
    """Vulnerability filter parameters"""
    severity: Optional[VulnerabilitySeverity] = None
    status: Optional[VulnerabilityStatus] = None
    min_cvss: Optional[float] = Field(None, ge=0.0, le=10.0)
    asset_id: Optional[int] = None
    has_patch: Optional[bool] = None


class AssetFilter(PaginationParams):
    """Asset filter parameters"""
    type: Optional[AssetType] = None
    is_active: Optional[bool] = None
    environment: Optional[str] = None


class DeploymentFilter(PaginationParams):
    """Deployment filter parameters"""
    status: Optional[DeploymentStatus] = None
    asset_id: Optional[int] = None
    patch_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Error Schemas
class ErrorResponse(BaseSchema):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
