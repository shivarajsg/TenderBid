import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Verify root status endpoint returns valid response."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["api_version"] == "v1"


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    """Verify liveness probe reports healthy status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_readiness(client: AsyncClient):
    """Verify readiness probe checks database connectivity."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code in [200, 503]
    body = response.json()
    if response.status_code == 200:
        assert body["success"] is True
        assert body["data"]["database"] == "connected"
