"""
AI Workspace API — HTTP Middleware

Request correlation and structured request logging.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.rate_limit import rate_limiter

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and log one structured line per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        client = request.client.host if request.client else "-"
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "client": client,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client": client,
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-client limits to auth, upload, and general API routes."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path == "/health":
            return await call_next(request)

        rule = self._rule_for(request.url.path)
        if rule is None:
            return await call_next(request)

        name, limit = rule
        client = request.client.host if request.client else "unknown"
        if not rate_limiter.allow(
            f"{name}:{client}", limit, settings.rate_limit_window_seconds
        ):
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={
                    "Retry-After": str(settings.rate_limit_window_seconds),
                },
            )

        return await call_next(request)

    def _rule_for(self, path: str) -> tuple[str, int] | None:
        if path.startswith("/api/auth/login"):
            return "auth", settings.rate_limit_auth
        if path.startswith("/api/documents/upload"):
            return "upload", settings.rate_limit_upload
        if path.startswith("/api/"):
            return "api", settings.rate_limit_api
        return None
