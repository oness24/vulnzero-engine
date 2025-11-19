"""
Response Helpers Tests

Comprehensive tests for API response helper utilities.
"""

import pytest
from pydantic import ValidationError

from shared.utils.response_helpers import (
    SuccessResponse,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    PaginatedResponse,
    ListQueryParams,
    success_response,
    error_response,
    paginated_response,
    created_response,
    deleted_response,
    no_content_response,
    calculate_offset,
    parse_sort_params,
)


class TestSuccessResponse:
    """Tests for success response helper"""

    def test_success_response_basic(self):
        """Test basic success response"""
        response = success_response(data={"id": 1, "name": "test"})

        assert response["success"] is True
        assert response["data"] == {"id": 1, "name": "test"}
        assert "message" not in response

    def test_success_response_with_message(self):
        """Test success response with message"""
        response = success_response(
            data={"id": 1},
            message="Resource retrieved successfully"
        )

        assert response["success"] is True
        assert response["data"] == {"id": 1}
        assert response["message"] == "Resource retrieved successfully"

    def test_success_response_with_list_data(self):
        """Test success response with list data"""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = success_response(data=items)

        assert response["success"] is True
        assert response["data"] == items
        assert len(response["data"]) == 3

    def test_success_response_with_null_data(self):
        """Test success response with None data"""
        response = success_response(data=None)

        assert response["success"] is True
        assert response["data"] is None

    def test_success_response_with_empty_dict(self):
        """Test success response with empty dictionary"""
        response = success_response(data={})

        assert response["success"] is True
        assert response["data"] == {}


class TestErrorResponse:
    """Tests for error response helper"""

    def test_error_response_basic(self):
        """Test basic error response"""
        response = error_response(
            code="NOT_FOUND",
            message="Resource not found"
        )

        assert response["success"] is False
        assert response["error"]["code"] == "NOT_FOUND"
        assert response["error"]["message"] == "Resource not found"
        assert response["error"]["details"] == {}

    def test_error_response_with_details(self):
        """Test error response with details"""
        response = error_response(
            code="VALIDATION_ERROR",
            message="Invalid input data",
            details={"field": "email", "reason": "invalid format"}
        )

        assert response["success"] is False
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Invalid input data"
        assert response["error"]["details"]["field"] == "email"
        assert response["error"]["details"]["reason"] == "invalid format"

    def test_error_response_common_codes(self):
        """Test error response with common error codes"""
        codes = [
            "NOT_FOUND",
            "VALIDATION_ERROR",
            "UNAUTHORIZED",
            "FORBIDDEN",
            "INTERNAL_ERROR",
            "BAD_REQUEST",
        ]

        for code in codes:
            response = error_response(code=code, message=f"Test {code}")
            assert response["error"]["code"] == code


class TestPaginatedResponse:
    """Tests for paginated response helper"""

    def test_paginated_response_first_page(self):
        """Test paginated response for first page"""
        items = [{"id": i} for i in range(1, 21)]  # 20 items
        response = paginated_response(
            items=items,
            total_items=100,
            page=1,
            page_size=20
        )

        assert response["success"] is True
        assert len(response["data"]) == 20
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["page_size"] == 20
        assert response["pagination"]["total_items"] == 100
        assert response["pagination"]["total_pages"] == 5
        assert response["pagination"]["has_next"] is True
        assert response["pagination"]["has_prev"] is False

    def test_paginated_response_middle_page(self):
        """Test paginated response for middle page"""
        items = [{"id": i} for i in range(21, 41)]
        response = paginated_response(
            items=items,
            total_items=100,
            page=2,
            page_size=20
        )

        assert response["pagination"]["page"] == 2
        assert response["pagination"]["has_next"] is True
        assert response["pagination"]["has_prev"] is True

    def test_paginated_response_last_page(self):
        """Test paginated response for last page"""
        items = [{"id": i} for i in range(81, 101)]
        response = paginated_response(
            items=items,
            total_items=100,
            page=5,
            page_size=20
        )

        assert response["pagination"]["page"] == 5
        assert response["pagination"]["total_pages"] == 5
        assert response["pagination"]["has_next"] is False
        assert response["pagination"]["has_prev"] is True

    def test_paginated_response_empty_results(self):
        """Test paginated response with empty results"""
        response = paginated_response(
            items=[],
            total_items=0,
            page=1,
            page_size=20
        )

        assert response["success"] is True
        assert response["data"] == []
        assert response["pagination"]["total_items"] == 0
        assert response["pagination"]["total_pages"] == 0
        assert response["pagination"]["has_next"] is False
        assert response["pagination"]["has_prev"] is False

    def test_paginated_response_partial_last_page(self):
        """Test paginated response with partial last page"""
        items = [{"id": i} for i in range(91, 98)]  # Only 7 items
        response = paginated_response(
            items=items,
            total_items=97,
            page=5,
            page_size=20
        )

        assert len(response["data"]) == 7
        assert response["pagination"]["total_pages"] == 5
        assert response["pagination"]["has_next"] is False

    def test_paginated_response_different_page_sizes(self):
        """Test paginated response with different page sizes"""
        page_sizes = [10, 20, 50, 100]

        for size in page_sizes:
            response = paginated_response(
                items=[],
                total_items=100,
                page=1,
                page_size=size
            )

            expected_pages = (100 + size - 1) // size  # Ceiling division
            assert response["pagination"]["page_size"] == size
            assert response["pagination"]["total_pages"] == expected_pages


class TestCreatedResponse:
    """Tests for created response helper"""

    def test_created_response_basic(self):
        """Test basic created response"""
        data = {"id": 123, "name": "New Resource"}
        response = created_response(data=data, resource_id=123)

        assert response["success"] is True
        assert response["data"] == data
        assert response["id"] == 123
        assert "message" not in response

    def test_created_response_with_message(self):
        """Test created response with message"""
        data = {"id": 456, "name": "Test"}
        response = created_response(
            data=data,
            resource_id=456,
            message="Resource created successfully"
        )

        assert response["success"] is True
        assert response["data"] == data
        assert response["id"] == 456
        assert response["message"] == "Resource created successfully"

    def test_created_response_with_string_id(self):
        """Test created response with string ID (UUID)"""
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        response = created_response(
            data={"name": "Test"},
            resource_id=uuid_id
        )

        assert response["id"] == uuid_id


class TestDeletedResponse:
    """Tests for deleted response helper"""

    def test_deleted_response_basic(self):
        """Test basic deleted response"""
        response = deleted_response(
            resource_type="vulnerability",
            resource_id=123
        )

        assert response["success"] is True
        assert response["message"] == "vulnerability deleted successfully"
        assert response["deleted"]["type"] == "vulnerability"
        assert response["deleted"]["id"] == 123

    def test_deleted_response_with_custom_message(self):
        """Test deleted response with custom message"""
        response = deleted_response(
            resource_type="patch",
            resource_id=456,
            message="Patch removed from system"
        )

        assert response["success"] is True
        assert response["message"] == "Patch removed from system"
        assert response["deleted"]["type"] == "patch"
        assert response["deleted"]["id"] == 456

    def test_deleted_response_different_resource_types(self):
        """Test deleted response with different resource types"""
        resource_types = ["vulnerability", "patch", "asset", "deployment"]

        for resource_type in resource_types:
            response = deleted_response(
                resource_type=resource_type,
                resource_id=1
            )

            assert response["deleted"]["type"] == resource_type
            assert resource_type in response["message"]


class TestNoContentResponse:
    """Tests for no content response helper"""

    def test_no_content_response(self):
        """Test no content response returns empty dict"""
        response = no_content_response()

        assert response == {}
        assert isinstance(response, dict)
        assert len(response) == 0


class TestCalculateOffset:
    """Tests for calculate_offset utility"""

    def test_calculate_offset_first_page(self):
        """Test offset for first page"""
        offset = calculate_offset(page=1, page_size=20)
        assert offset == 0

    def test_calculate_offset_second_page(self):
        """Test offset for second page"""
        offset = calculate_offset(page=2, page_size=20)
        assert offset == 20

    def test_calculate_offset_third_page(self):
        """Test offset for third page"""
        offset = calculate_offset(page=3, page_size=20)
        assert offset == 40

    def test_calculate_offset_different_page_sizes(self):
        """Test offset calculation with different page sizes"""
        test_cases = [
            (1, 10, 0),
            (2, 10, 10),
            (1, 50, 0),
            (3, 50, 100),
            (1, 100, 0),
            (5, 25, 100),
        ]

        for page, page_size, expected_offset in test_cases:
            offset = calculate_offset(page, page_size)
            assert offset == expected_offset, \
                f"Page {page} with size {page_size} should have offset {expected_offset}"

    def test_calculate_offset_large_pages(self):
        """Test offset calculation for large page numbers"""
        offset = calculate_offset(page=100, page_size=20)
        assert offset == 1980


class TestParseSortParams:
    """Tests for parse_sort_params utility"""

    def test_parse_sort_params_ascending(self):
        """Test parsing ascending sort"""
        field, order = parse_sort_params("created_at", "asc")

        assert field == "created_at"
        assert order == "asc"

    def test_parse_sort_params_descending(self):
        """Test parsing descending sort"""
        field, order = parse_sort_params("updated_at", "desc")

        assert field == "updated_at"
        assert order == "desc"

    def test_parse_sort_params_default_order(self):
        """Test parsing with default order"""
        field, order = parse_sort_params("name")

        assert field == "name"
        assert order == "desc"

    def test_parse_sort_params_case_insensitive(self):
        """Test that sort order is case insensitive"""
        test_cases = [
            ("ASC", "asc"),
            ("DESC", "desc"),
            ("Asc", "asc"),
            ("Desc", "desc"),
        ]

        for input_order, expected_order in test_cases:
            field, order = parse_sort_params("name", input_order)
            assert order == expected_order

    def test_parse_sort_params_invalid_order(self):
        """Test that invalid sort order defaults to desc"""
        field, order = parse_sort_params("name", "invalid")

        assert field == "name"
        assert order == "desc"

    def test_parse_sort_params_none_field(self):
        """Test parsing with None sort field"""
        field, order = parse_sort_params(None, "asc")

        assert field is None
        assert order == "asc"


class TestListQueryParams:
    """Tests for ListQueryParams model"""

    def test_list_query_params_defaults(self):
        """Test ListQueryParams with default values"""
        params = ListQueryParams()

        assert params.page == 1
        assert params.page_size == 50
        assert params.sort_by is None
        assert params.sort_order == "desc"
        assert params.search is None

    def test_list_query_params_custom_values(self):
        """Test ListQueryParams with custom values"""
        params = ListQueryParams(
            page=2,
            page_size=20,
            sort_by="created_at",
            sort_order="asc",
            search="sql injection"
        )

        assert params.page == 2
        assert params.page_size == 20
        assert params.sort_by == "created_at"
        assert params.sort_order == "asc"
        assert params.search == "sql injection"

    def test_list_query_params_page_validation(self):
        """Test that page must be >= 1"""
        with pytest.raises(ValidationError):
            ListQueryParams(page=0)

        with pytest.raises(ValidationError):
            ListQueryParams(page=-1)

    def test_list_query_params_page_size_validation(self):
        """Test that page_size must be between 1 and 100"""
        # Valid values
        ListQueryParams(page_size=1)
        ListQueryParams(page_size=50)
        ListQueryParams(page_size=100)

        # Invalid values
        with pytest.raises(ValidationError):
            ListQueryParams(page_size=0)

        with pytest.raises(ValidationError):
            ListQueryParams(page_size=101)

    def test_list_query_params_sort_order_validation(self):
        """Test that sort_order must be 'asc' or 'desc'"""
        # Valid values
        ListQueryParams(sort_order="asc")
        ListQueryParams(sort_order="desc")

        # Invalid values
        with pytest.raises(ValidationError):
            ListQueryParams(sort_order="invalid")

        with pytest.raises(ValidationError):
            ListQueryParams(sort_order="ascending")


class TestPydanticModels:
    """Tests for Pydantic response models"""

    def test_success_response_model(self):
        """Test SuccessResponse model"""
        response = SuccessResponse(data={"id": 1, "name": "test"})

        assert response.success is True
        assert response.data == {"id": 1, "name": "test"}
        assert response.message is None

    def test_success_response_model_with_message(self):
        """Test SuccessResponse model with message"""
        response = SuccessResponse(
            data={"id": 1},
            message="Success!"
        )

        assert response.message == "Success!"

    def test_error_detail_model(self):
        """Test ErrorDetail model"""
        error = ErrorDetail(
            code="NOT_FOUND",
            message="Resource not found"
        )

        assert error.code == "NOT_FOUND"
        assert error.message == "Resource not found"
        assert error.details is None

    def test_error_response_model(self):
        """Test ErrorResponse model"""
        error_detail = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid input"
        )
        response = ErrorResponse(error=error_detail)

        assert response.success is False
        assert response.error.code == "VALIDATION_ERROR"

    def test_pagination_meta_model(self):
        """Test PaginationMeta model"""
        meta = PaginationMeta(
            page=2,
            page_size=20,
            total_items=100,
            total_pages=5,
            has_next=True,
            has_prev=True
        )

        assert meta.page == 2
        assert meta.total_pages == 5
        assert meta.has_next is True

    def test_pagination_meta_validation(self):
        """Test PaginationMeta validation"""
        # Page must be >= 1
        with pytest.raises(ValidationError):
            PaginationMeta(
                page=0,
                page_size=20,
                total_items=100,
                total_pages=5,
                has_next=True,
                has_prev=False
            )

        # Total items must be >= 0
        with pytest.raises(ValidationError):
            PaginationMeta(
                page=1,
                page_size=20,
                total_items=-1,
                total_pages=0,
                has_next=False,
                has_prev=False
            )

    def test_paginated_response_model(self):
        """Test PaginatedResponse model"""
        items = [{"id": 1}, {"id": 2}]
        meta = PaginationMeta(
            page=1,
            page_size=2,
            total_items=2,
            total_pages=1,
            has_next=False,
            has_prev=False
        )
        response = PaginatedResponse(data=items, pagination=meta)

        assert response.success is True
        assert len(response.data) == 2
        assert response.pagination.page == 1


class TestEdgeCases:
    """Edge case tests for response helpers"""

    def test_pagination_with_zero_page_size(self):
        """Test pagination with zero page size (edge case)"""
        # Should not crash, total_pages should be 0
        response = paginated_response(
            items=[],
            total_items=100,
            page=1,
            page_size=0
        )

        assert response["pagination"]["total_pages"] == 0

    def test_pagination_with_more_items_than_total(self):
        """Test pagination when items list is larger than expected"""
        # This shouldn't normally happen, but test it anyway
        items = [{"id": i} for i in range(1, 31)]  # 30 items
        response = paginated_response(
            items=items,
            total_items=10,  # Says only 10 total
            page=1,
            page_size=20
        )

        # Should still work, data contains what was passed
        assert len(response["data"]) == 30

    def test_success_response_with_complex_nested_data(self):
        """Test success response with complex nested structure"""
        complex_data = {
            "vulnerability": {
                "id": 1,
                "cve_id": "CVE-2024-1234",
                "assets": [
                    {"id": 1, "name": "server1"},
                    {"id": 2, "name": "server2"}
                ],
                "patches": [
                    {
                        "id": 1,
                        "version": "1.0.0",
                        "changes": ["fix1", "fix2"]
                    }
                ]
            }
        }

        response = success_response(data=complex_data)

        assert response["data"]["vulnerability"]["id"] == 1
        assert len(response["data"]["vulnerability"]["assets"]) == 2

    def test_error_response_with_nested_details(self):
        """Test error response with nested details"""
        details = {
            "validation_errors": [
                {"field": "email", "message": "Invalid format"},
                {"field": "password", "message": "Too short"}
            ]
        }

        response = error_response(
            code="VALIDATION_ERROR",
            message="Multiple validation errors",
            details=details
        )

        assert len(response["error"]["details"]["validation_errors"]) == 2
