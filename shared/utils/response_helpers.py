"""
API response helper utilities

Provides standardized response formats for consistency across all API endpoints:
- Success responses
- Error responses
- Pagination helpers
- Response models
"""

from typing import Any, Optional, List, TypeVar, Generic
from pydantic import BaseModel, Field
from math import ceil


T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper"""

    success: bool = Field(True, description="Indicates successful response")
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Optional success message")


class ErrorDetail(BaseModel):
    """Error detail model"""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response wrapper"""

    success: bool = Field(False, description="Indicates error response")
    error: ErrorDetail = Field(..., description="Error details")


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response"""

    success: bool = Field(True, description="Indicates successful response")
    data: List[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


def success_response(
    data: Any,
    message: Optional[str] = None
) -> dict:
    """
    Create standardized success response

    Args:
        data: Response data (any JSON-serializable type)
        message: Optional success message

    Returns:
        Standardized success response dictionary

    Example:
        return success_response(
            data={"vulnerability": vuln_dict},
            message="Vulnerability retrieved successfully"
        )
    """
    response = {
        "success": True,
        "data": data
    }

    if message:
        response["message"] = message

    return response


def error_response(
    code: str,
    message: str,
    details: Optional[dict] = None
) -> dict:
    """
    Create standardized error response

    Args:
        code: Error code (e.g., "VALIDATION_ERROR")
        message: Human-readable error message
        details: Optional additional error details

    Returns:
        Standardized error response dictionary

    Example:
        return error_response(
            code="NOT_FOUND",
            message="Vulnerability not found",
            details={"vulnerability_id": 123}
        )
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }


def paginated_response(
    items: List[Any],
    total_items: int,
    page: int,
    page_size: int
) -> dict:
    """
    Create standardized paginated response

    Args:
        items: List of items for current page
        total_items: Total number of items across all pages
        page: Current page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Standardized paginated response dictionary

    Example:
        vulnerabilities, total = await get_vulnerabilities_paginated(page=1, page_size=20)
        return paginated_response(
            items=vulnerabilities,
            total_items=total,
            page=1,
            page_size=20
        )
    """
    total_pages = ceil(total_items / page_size) if page_size > 0 else 0

    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


def created_response(
    data: Any,
    resource_id: Any,
    message: Optional[str] = None
) -> dict:
    """
    Create standardized 201 Created response

    Args:
        data: Created resource data
        resource_id: ID of the created resource
        message: Optional success message

    Returns:
        Standardized created response dictionary

    Example:
        new_vulnerability = await create_vulnerability(data)
        return created_response(
            data=new_vulnerability,
            resource_id=new_vulnerability.id,
            message="Vulnerability created successfully"
        )
    """
    response = {
        "success": True,
        "data": data,
        "id": resource_id
    }

    if message:
        response["message"] = message

    return response


def deleted_response(
    resource_type: str,
    resource_id: Any,
    message: Optional[str] = None
) -> dict:
    """
    Create standardized 200 OK delete response

    Args:
        resource_type: Type of resource deleted (e.g., "vulnerability")
        resource_id: ID of the deleted resource
        message: Optional success message

    Returns:
        Standardized delete response dictionary

    Example:
        await delete_vulnerability(vuln_id)
        return deleted_response(
            resource_type="vulnerability",
            resource_id=vuln_id,
            message="Vulnerability deleted successfully"
        )
    """
    return {
        "success": True,
        "message": message or f"{resource_type} deleted successfully",
        "deleted": {
            "type": resource_type,
            "id": resource_id
        }
    }


def no_content_response() -> dict:
    """
    Create standardized 204 No Content response

    Returns:
        Empty dictionary (FastAPI will return 204)

    Example:
        await update_vulnerability(vuln_id, data)
        return Response(status_code=204)
    """
    return {}


class ListQueryParams(BaseModel):
    """Standard query parameters for list endpoints"""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")
    search: Optional[str] = Field(None, description="Search query")

    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc",
                "search": "sql injection"
            }
        }


def calculate_offset(page: int, page_size: int) -> int:
    """
    Calculate SQL offset from page number

    Args:
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        SQL offset value

    Example:
        offset = calculate_offset(page=3, page_size=20)  # Returns 40
    """
    return (page - 1) * page_size


def parse_sort_params(sort_by: Optional[str], sort_order: str = "desc") -> tuple[Optional[str], str]:
    """
    Parse and validate sort parameters

    Args:
        sort_by: Field name to sort by
        sort_order: Sort order (asc or desc)

    Returns:
        Tuple of (validated_sort_by, validated_sort_order)

    Example:
        field, order = parse_sort_params("created_at", "asc")
    """
    valid_sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "desc"
    return (sort_by, valid_sort_order)
