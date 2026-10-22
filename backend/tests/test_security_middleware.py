import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_present_on_responses():
    """Verify defense-in-depth security headers are present on API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_in_memory_rate_limiter_enforcement():
    """Verify rate limiter blocks requests exceeding configured threshold with HTTP 429."""
    from app.core.middleware import InMemoryRateLimiter
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def dummy_endpoint(request):
        return JSONResponse({"status": "ok"})

    test_app = Starlette(routes=[Route("/auth/login", dummy_endpoint, methods=["POST"])])
    # Set limit to 3 requests per minute for testing
    test_app.add_middleware(InMemoryRateLimiter, auth_limit_per_minute=3, enabled=True)

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First 3 requests should pass
        for _ in range(3):
            res = await client.post("/auth/login")
            assert res.status_code == 200

        # 4th request must be blocked with HTTP 429
        blocked_res = await client.post("/auth/login")
        assert blocked_res.status_code == 429
        body = blocked_res.json()
        assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in blocked_res.headers
