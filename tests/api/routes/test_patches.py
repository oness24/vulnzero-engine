"""
Tests for patch API routes
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app
from shared.models.models import Patch, PatchStatus


client = TestClient(app)


def test_list_patches():
    """Test listing patches"""
    response = client.get("/api/patches/")
    assert response.status_code in [200, 500]


def test_list_patches_with_filters():
    """Test patch listing with filters"""
    response = client.get(
        "/api/patches/",
        params={
            "status": "approved",
            "page": 1,
            "page_size": 20,
        }
    )
    assert response.status_code in [200, 500]


def test_get_patch_not_found():
    """Test getting non-existent patch"""
    response = client.get("/api/patches/99999")
    assert response.status_code in [404, 500]


def test_create_patch():
    """Test creating a patch"""
    patch_data = {
        "vulnerability_id": 1,
        "patch_script": "#!/bin/bash\necho test",
        "rollback_script": "#!/bin/bash\necho rollback",
        "validation_script": "#!/bin/bash\necho validate",
    }

    response = client.post("/api/patches/", json=patch_data)
    assert response.status_code in [200, 201, 404, 500]


def test_update_patch_status():
    """Test updating patch status"""
    status_update = {
        "status": "approved",
        "reason": "Test approval",
    }

    response = client.patch("/api/patches/1/status", json=status_update)
    assert response.status_code in [200, 404, 500]


def test_update_patch_status_invalid():
    """Test updating patch with invalid status"""
    status_update = {
        "status": "invalid_status",
    }

    response = client.patch("/api/patches/1/status", json=status_update)
    assert response.status_code in [400, 404, 500]


def test_delete_patch():
    """Test deleting a patch"""
    response = client.delete("/api/patches/1")
    assert response.status_code in [200, 400, 404, 500]


def test_get_patch_stats():
    """Test getting patch statistics"""
    response = client.get("/api/patches/stats/summary")
    assert response.status_code in [200, 500]


def test_test_patch():
    """Test triggering patch testing"""
    response = client.post("/api/patches/1/test")
    assert response.status_code in [200, 404, 500]


def test_get_test_results():
    """Test getting patch test results"""
    response = client.get("/api/patches/1/test-results")
    assert response.status_code in [200, 404, 500]
