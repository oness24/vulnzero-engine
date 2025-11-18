"""
Tests for patch management endpoints
"""

import pytest
from httpx import AsyncClient

from shared.models.models import Patch, TestStatus


@pytest.mark.asyncio
async def test_list_patches(client: AsyncClient, auth_headers: dict, sample_patch: Patch):
    """Test listing patches"""
    response = await client.get("/api/v1/patches", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1
    assert data[0]["patch_id"] == sample_patch.patch_id


@pytest.mark.asyncio
async def test_list_patches_filter_by_status(
    client: AsyncClient,
    auth_headers: dict,
    sample_patch: Patch,
):
    """Test filtering patches by test status"""
    response = await client.get(
        "/api/v1/patches?test_status=passed",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for patch in data:
        assert patch["test_status"] == "passed"


@pytest.mark.asyncio
async def test_get_patch(client: AsyncClient, auth_headers: dict, sample_patch: Patch):
    """Test getting a specific patch"""
    response = await client.get(
        f"/api/v1/patches/{sample_patch.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == sample_patch.id
    assert data["patch_id"] == sample_patch.patch_id
    assert data["patch_content"] == sample_patch.patch_content


@pytest.mark.asyncio
async def test_get_patch_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent patch"""
    response = await client.get("/api/v1/patches/99999", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_patch(
    client: AsyncClient,
    auth_headers: dict,
    sample_patch: Patch,
):
    """Test approving a patch"""
    approval_data = {
        "approved_by": "admin_user",
        "notes": "Patch approved for deployment",
    }

    response = await client.post(
        f"/api/v1/patches/{sample_patch.id}/approve",
        json=approval_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["approved_by"] == "admin_user"
    assert data["approved_at"] is not None


@pytest.mark.asyncio
async def test_approve_patch_not_tested(
    client: AsyncClient,
    auth_headers: dict,
    sample_vulnerability,
    db_session,
):
    """Test that patches must pass testing before approval"""
    # Create patch that hasn't been tested
    untested_patch = Patch(
        patch_id="untested-patch",
        vulnerability_id=sample_vulnerability.id,
        patch_type="script",
        patch_content="test",
        llm_provider="openai",
        llm_model="gpt-4",
        confidence_score=0.9,
        test_status=TestStatus.PENDING,
    )
    db_session.add(untested_patch)
    await db_session.commit()
    await db_session.refresh(untested_patch)

    approval_data = {
        "approved_by": "admin_user",
        "notes": "Approving",
    }

    response = await client.post(
        f"/api/v1/patches/{untested_patch.id}/approve",
        json=approval_data,
        headers=auth_headers,
    )

    assert response.status_code == 400  # Bad request


@pytest.mark.asyncio
async def test_reject_patch(
    client: AsyncClient,
    auth_headers: dict,
    sample_patch: Patch,
):
    """Test rejecting a patch"""
    rejection_data = {
        "rejection_reason": "Patch contains errors",
        "rejected_by": "security_team",
    }

    response = await client.post(
        f"/api/v1/patches/{sample_patch.id}/reject",
        json=rejection_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["rejection_reason"] == "Patch contains errors"
    assert data["test_status"] == "failed"
