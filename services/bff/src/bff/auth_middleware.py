"""JWT Bearer authentication middleware for the BFF."""

from datetime import datetime, timezone

import jwt
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from bff.config import settings

logger = structlog.get_logger()

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/auth/setup-status",
    "/api/v1/auth/setup",
    "/api/v1/auth/setup-qr",
    "/api/v1/auth/login",
    "/api/v1/auth/verify-totp",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates JWT Bearer token on all /api/v1/* paths except public auth endpoints."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path

        # Skip auth for public paths and non-API paths
        if path in PUBLIC_PATHS or not path.startswith("/api/v1/"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid authorization header"})

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            request.state.user_id = payload["sub"]
            request.state.username = payload.get("username", "")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        return await call_next(request)
