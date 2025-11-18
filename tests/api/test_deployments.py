"""
Tests for deployment management endpoints
"""

import pytest
from httpx import AsyncClient

from shared.models.models import Deployment, DeploymentStatus


@pytest.mark.asyncio
async def test_list_deployments(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
):
    """Test listing deployments"""
    response = await client.get("/api/v1/deployments", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1
    assert data[0]["deployment_id"] == sample_deployment.deployment_id


@pytest.mark.asyncio
async def test_list_deployments_filter_by_status(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
):
    """Test filtering deployments by status"""
    response = await client.get(
        "/api/v1/deployments?status=pending",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for deployment in data:
        assert deployment["status"] == "pending"


@pytest.mark.asyncio
async def test_list_deployments_filter_by_asset(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
    sample_asset,
):
    """Test filtering deployments by asset"""
    response = await client.get(
        f"/api/v1/deployments?asset_id={sample_asset.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for deployment in data:
        assert deployment["asset_id"] == sample_asset.id


@pytest.mark.asyncio
async def test_get_deployment(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
):
    """Test getting a specific deployment"""
    response = await client.get(
        f"/api/v1/deployments/{sample_deployment.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == sample_deployment.id
    assert data["deployment_id"] == sample_deployment.deployment_id
    assert "patch" in data
    assert "asset" in data


@pytest.mark.asyncio
async def test_get_deployment_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent deployment"""
    response = await client.get("/api/v1/deployments/99999", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rollback_deployment_success(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
    db_session,
):
    """Test rolling back a successful deployment"""
    # Update deployment to success status
    sample_deployment.status = DeploymentStatus.SUCCESS
    await db_session.commit()
    await db_session.refresh(sample_deployment)

    rollback_data = {
        "reason": "Service errors after deployment",
        "requested_by": "ops_engineer",
    }

    response = await client.post(
        f"/api/v1/deployments/{sample_deployment.id}/rollback",
        json=rollback_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["rollback_required"] is True
    assert data["rollback_reason"] == "Service errors after deployment"
    assert data["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_rollback_deployment_invalid_status(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
):
    """Test that rollback fails for deployments in invalid status"""
    # Deployment is in PENDING status - can't rollback
    rollback_data = {
        "reason": "Test rollback",
        "requested_by": "admin",
    }

    response = await client.post(
        f"/api/v1/deployments/{sample_deployment.id}/rollback",
        json=rollback_data,
        headers=auth_headers,
    )

    assert response.status_code == 400  # Bad request


@pytest.mark.asyncio
async def test_rollback_already_rolled_back(
    client: AsyncClient,
    auth_headers: dict,
    sample_deployment: Deployment,
    db_session,
):
    """Test that already rolled back deployments cannot be rolled back again"""
    # Set to rolled back status
    sample_deployment.status = DeploymentStatus.ROLLED_BACK
    await db_session.commit()
    await db_session.refresh(sample_deployment)

    rollback_data = {
        "reason": "Test",
        "requested_by": "admin",
    }

    response = await client.post(
        f"/api/v1/deployments/{sample_deployment.id}/rollback",
        json=rollback_data,
        headers=auth_headers,
    )

    assert response.status_code == 400
