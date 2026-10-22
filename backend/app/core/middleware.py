import time
from collections import defaultdict
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects defense-in-depth HTTP security headers into all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class InMemoryRateLimiter(BaseHTTPMiddleware):
    """
    Thread-safe, sliding-window in-memory rate limiter for security-sensitive and
    resource-intensive endpoints.
    """

    def __init__(
        self,
        app,
        auth_limit_per_minute: int = 60,
        analyze_limit_per_minute: int = 30,
        global_limit_per_minute: int = 300,
        enabled: bool = True,
    ):
        super().__init__(app)
        self.auth_limit = auth_limit_per_minute
        self.analyze_limit = analyze_limit_per_minute
        self.global_limit = global_limit_per_minute
        self.enabled = enabled
        # ip -> list of timestamps
        self._auth_records: Dict[str, List[float]] = defaultdict(list)
        self._analyze_records: Dict[str, List[float]] = defaultdict(list)
        self._global_records: Dict[str, List[float]] = defaultdict(list)

    def _is_allowed(self, records: List[float], limit: int, window: float = 60.0) -> bool:
        """Prunes timestamps older than window and returns True if request is allowed, False if exceeded."""
        now = time.time()
        valid = [t for t in records if now - t < window]
        records.clear()
        records.extend(valid)

        if len(records) >= limit:
            return False
        records.append(now)
        return True

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Allow tests to bypass rate limiting via header or config if desired
        if request.headers.get("X-Test-Bypass-Rate-Limit") == "true":
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path

        # Sensitive Auth endpoints: login / register
        if request.method == "POST" and ("/auth/login" in path or "/auth/register" in path):
            if not self._is_allowed(self._auth_records[client_ip], self.auth_limit):
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many authentication attempts. Please retry after a brief delay.",
                        "details": {"retry_after_seconds": 60},
                    },
                    headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.auth_limit)},
                )

        # Intensive analysis endpoint
        elif request.method == "POST" and "/compliance/analyze" in path:
            if not self._is_allowed(self._analyze_records[client_ip], self.analyze_limit):
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many compliance evaluations triggered. Please retry shortly.",
                        "details": {"retry_after_seconds": 60},
                    },
                    headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.analyze_limit)},
                )

        # Global endpoint limit
        if not self._is_allowed(self._global_records[client_ip], self.global_limit):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "API request rate limit exceeded. Please wait a moment.",
                    "details": {"retry_after_seconds": 60},
                },
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(self.global_limit)},
            )

        response = await call_next(request)
        return response
