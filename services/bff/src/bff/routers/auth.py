"""BFF router for authentication: setup, login, and user info."""

import io
from datetime import datetime, timezone, timedelta

import jwt
import pyotp
import qrcode
import qrcode.constants
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from passlib.hash import bcrypt
from pydantic import BaseModel, Field

from bff.auth_repository import create_user, get_user_by_username, get_user_count
from bff.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ─── Schemas ───


class SetupStatusResponse(BaseModel):
    is_setup_complete: bool


class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class SetupResponse(BaseModel):
    username: str
    totp_uri: str


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str = Field(min_length=6, max_length=6)


class LoginResponse(BaseModel):
    token: str
    username: str


class MeResponse(BaseModel):
    user_id: str
    username: str


# ─── Endpoints ───


@router.get("/setup-status")
async def setup_status() -> SetupStatusResponse:
    """Check whether initial setup has been completed."""
    count = await get_user_count()
    return SetupStatusResponse(is_setup_complete=count > 0)


@router.post("/setup")
async def setup(req: SetupRequest) -> SetupResponse:
    """Create the first user account with TOTP 2FA. Only works once."""
    count = await get_user_count()
    if count > 0:
        raise HTTPException(status_code=409, detail="Setup already completed")

    password_hash = bcrypt.hash(req.password)
    totp_secret = pyotp.random_base32()
    totp_uri = pyotp.TOTP(totp_secret).provisioning_uri(name=req.username, issuer_name="mail-manager")

    await create_user(req.username, password_hash, totp_secret)
    logger.info("user created via setup", username=req.username)

    return SetupResponse(username=req.username, totp_uri=totp_uri)


@router.get("/setup-qr")
async def setup_qr(username: str, secret: str) -> StreamingResponse:
    """Generate a QR code image for the TOTP setup URI."""
    totp_uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="mail-manager")
    img = qrcode.make(totp_uri, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/login")
async def login(req: LoginRequest) -> LoginResponse:
    """Authenticate with username, password, and TOTP code. Returns a JWT."""
    user = await get_user_by_username(req.username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("totp_secret"):
        raise HTTPException(status_code=401, detail="TOTP not configured")

    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(req.totp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    logger.info("user logged in", username=req.username)

    return LoginResponse(token=token, username=user["username"])


@router.get("/me")
async def me(request: Request) -> MeResponse:
    """Return the current user's info from the JWT."""
    user_id = getattr(request.state, "user_id", None)
    username = getattr(request.state, "username", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return MeResponse(user_id=user_id, username=username)
