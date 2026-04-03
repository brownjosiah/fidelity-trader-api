"""API key authentication middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from service.auth.api_key import hash_api_key

# Paths that never require API key auth
EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Check Authorization: Bearer <key> on all non-exempt routes."""

    async def dispatch(self, request: Request, call_next):
        settings = request.app.state.settings

        # Skip auth entirely when not required
        if not settings.api_key_required:
            return await call_next(request)

        # Skip for exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Extract bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "data": None,
                    "error": {
                        "code": "API_KEY_INVALID",
                        "message": "Missing or invalid API key",
                        "details": None,
                    },
                },
            )

        token = auth_header[7:]  # strip "Bearer "
        key_hash = hash_api_key(token)
        store = request.app.state.store

        is_valid = await store.validate_api_key(key_hash)
        if not is_valid:
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "data": None,
                    "error": {
                        "code": "API_KEY_INVALID",
                        "message": "Missing or invalid API key",
                        "details": None,
                    },
                },
            )

        return await call_next(request)
