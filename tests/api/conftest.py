"""
Shared fixtures for API tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
async def api_db(db_session):
    """Database session for API tests"""
    return db_session
