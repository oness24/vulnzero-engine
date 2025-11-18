"""
VulnZero API Gateway - Common Schemas
Shared Pydantic models for API requests/responses
"""

from typing import Optional, List, Any, Generic, TypeVar
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input data",
                "details": {"field": "email", "issue": "Invalid email format"},
                "request_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": 123, "status": "completed"}
            }
        }


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }
