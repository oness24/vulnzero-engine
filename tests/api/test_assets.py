"""
Tests for asset management endpoints
"""

import pytest
from httpx import AsyncClient

from shared.models.models import Asset


@pytest.mark.asyncio
async def test_list_assets(client: AsyncClient, auth_headers: dict, sample_asset: Asset):
    """Test listing assets"""
    response = await client.get("/api/v1/assets", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1
    assert data[0]["asset_id"] == sample_asset.asset_id


@pytest.mark.asyncio
async def test_list_assets_filter_by_type(
    client: AsyncClient,
    auth_headers: dict,
    sample_asset: Asset,
):
    """Test filtering assets by type"""
    response = await client.get(
        "/api/v1/assets?asset_type=server",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    for asset in data:
        assert asset["type"] == "server"


@pytest.mark.asyncio
async def test_get_asset(client: AsyncClient, auth_headers: dict, sample_asset: Asset):
    """Test getting a specific asset"""
    response = await client.get(
        f"/api/v1/assets/{sample_asset.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == sample_asset.id
    assert data["asset_id"] == sample_asset.asset_id
    assert data["hostname"] == sample_asset.hostname


@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent asset"""
    response = await client.get("/api/v1/assets/99999", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_asset(client: AsyncClient, auth_headers: dict):
    """Test creating a new asset"""
    asset_data = {
        "asset_id": "new-asset-001",
        "type": "server",
        "hostname": "new-server",
        "ip_address": "10.0.0.2",
        "os_type": "CentOS",
        "os_version": "8",
        "criticality": 5,
        "environment": "staging",
    }

    response = await client.post(
        "/api/v1/assets",
        json=asset_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert data["asset_id"] == "new-asset-001"
    assert data["hostname"] == "new-server"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_asset(
    client: AsyncClient,
    auth_headers: dict,
    sample_asset: Asset,
):
    """Test creating an asset with duplicate asset_id"""
    asset_data = {
        "asset_id": sample_asset.asset_id,  # Duplicate!
        "type": "server",
        "hostname": "duplicate",
    }

    response = await client.post(
        "/api/v1/assets",
        json=asset_data,
        headers=auth_headers,
    )

    assert response.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_update_asset(
    client: AsyncClient,
    auth_headers: dict,
    sample_asset: Asset,
):
    """Test updating an asset"""
    update_data = {
        "hostname": "updated-hostname",
        "criticality": 9,
    }

    response = await client.patch(
        f"/api/v1/assets/{sample_asset.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["hostname"] == "updated-hostname"
    assert data["criticality"] == 9


@pytest.mark.asyncio
async def test_get_asset_vulnerabilities(
    client: AsyncClient,
    auth_headers: dict,
    sample_asset: Asset,
    sample_vulnerability,
    db_session,
):
    """Test getting vulnerabilities for a specific asset"""
    from shared.models.models import AssetVulnerability

    # Create association
    asset_vuln = AssetVulnerability(
        asset_id=sample_asset.id,
        vulnerability_id=sample_vulnerability.id,
    )
    db_session.add(asset_vuln)
    await db_session.commit()

    response = await client.get(
        f"/api/v1/assets/{sample_asset.id}/vulnerabilities",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) >= 1
    assert data[0]["vulnerability"]["cve_id"] == sample_vulnerability.cve_id
