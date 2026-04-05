"""BFF router for authentication: setup, login, and user info."""

import io
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
import pyotp
import qrcode
import qrcode.constants
import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
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


class LoginResponse(BaseModel):
    requires_totp: bool = True
    challenge_token: str


class TotpVerifyRequest(BaseModel):
    challenge_token: str
    totp_code: str = Field(min_length=6, max_length=6)


class TotpVerifyResponse(BaseModel):
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

    password_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
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
    """Step 1: Validate username + password. Returns a short-lived challenge token for TOTP."""
    user = await get_user_by_username(req.username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("totp_secret"):
        raise HTTPException(status_code=401, detail="TOTP not configured")

    # Issue a short-lived challenge token (5 min) that only grants TOTP verification
    now = datetime.now(tz=timezone.utc)
    challenge_payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "purpose": "totp_challenge",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    challenge_token = jwt.encode(challenge_payload, settings.jwt_secret, algorithm="HS256")
    logger.info("credentials verified, totp challenge issued", username=req.username)

    return LoginResponse(requires_totp=True, challenge_token=challenge_token)


@router.post("/verify-totp")
async def verify_totp(req: TotpVerifyRequest) -> TotpVerifyResponse:
    """Step 2: Verify TOTP code using the challenge token. Returns a full session JWT."""
    try:
        payload = jwt.decode(req.challenge_token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Challenge expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid challenge token")

    if payload.get("purpose") != "totp_challenge":
        raise HTTPException(status_code=401, detail="Invalid challenge token")

    user = await get_user_by_username(payload["username"])
    if user is None or not user.get("totp_secret"):
        raise HTTPException(status_code=401, detail="Invalid challenge token")

    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(req.totp_code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    now = datetime.now(tz=timezone.utc)
    session_payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    token = jwt.encode(session_payload, settings.jwt_secret, algorithm="HS256")
    logger.info("user logged in", username=payload["username"])

    return TotpVerifyResponse(token=token, username=user["username"])


@router.get("/me")
async def me(request: Request) -> MeResponse:
    """Return the current user's info from the JWT."""
    user_id = getattr(request.state, "user_id", None)
    username = getattr(request.state, "username", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return MeResponse(user_id=user_id, username=username)
