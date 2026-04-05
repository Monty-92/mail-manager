import secrets
from uuid import UUID

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from ingestion.account_repository import (
    delete_account,
    get_account,
    get_accounts_by_provider,
    list_accounts,
    save_account,
)
from ingestion.config import settings
from ingestion.converter import email_body_to_markdown
from ingestion.providers import BaseEmailProvider
from ingestion.providers.gmail import GmailProvider
from ingestion.providers.outlook import OutlookProvider
from ingestion.publisher import publish_new_email
from ingestion.repository import get_email_by_id, get_sync_state, list_emails, save_sync_state, upsert_email
from ingestion.schemas import EmailProvider as EP
from ingestion.schemas import IngestResult, OAuthTokens

logger = structlog.get_logger()

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Temporary state storage for OAuth flows (maps state -> {provider, code_verifier})
_oauth_state_map: dict[str, dict[str, str | None]] = {}


def _make_provider(provider: EP, tokens: OAuthTokens | None = None) -> BaseEmailProvider:
    if provider == EP.GMAIL:
        return GmailProvider(tokens=tokens)
    elif provider == EP.OUTLOOK:
        return OutlookProvider(tokens=tokens)
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


# ─── Schemas ───


class AuthUrlResponse(BaseModel):
    auth_url: str
    provider: str


class AuthCallbackRequest(BaseModel):
    code: str
    provider: EP
    state: str | None = None


class AuthCallbackResponse(BaseModel):
    provider: str
    email: str
    account_id: str


class AccountResponse(BaseModel):
    id: str
    provider: str
    email: str
    display_name: str
    scopes: list[str]
    created_at: str
    updated_at: str


class DeviceFlowStartResponse(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None = None
    expires_in: int
    interval: int


class DeviceFlowPollResponse(BaseModel):
    status: str  # "pending" | "complete" | "expired"
    account_id: str | None = None
    email: str | None = None


# ─── OAuth Redirect Flow ───


@router.get("/auth/url/{provider}")
async def get_auth_url(provider: EP) -> AuthUrlResponse:
    """Get the OAuth authorization URL for a provider. Includes state for CSRF protection."""
    state = secrets.token_urlsafe(32)

    adapter = _make_provider(provider)
    url, code_verifier = adapter.get_auth_url(state=state)

    _oauth_state_map[state] = {"provider": provider.value, "code_verifier": code_verifier}

    return AuthUrlResponse(auth_url=url, provider=provider.value)


@router.post("/auth/callback")
async def auth_callback(req: AuthCallbackRequest, background_tasks: BackgroundTasks) -> AuthCallbackResponse:
    """Exchange an OAuth authorization code for tokens and save the account."""
    adapter = _make_provider(req.provider)

    # Retrieve the code_verifier stored during auth URL generation
    code_verifier: str | None = None
    state_key = req.state
    if state_key and state_key in _oauth_state_map:
        state_data = _oauth_state_map.pop(state_key)
        code_verifier = state_data.get("code_verifier")
    else:
        # Fallback: find by provider (handles missing state)
        for key, data in list(_oauth_state_map.items()):
            if data["provider"] == req.provider.value:
                code_verifier = data.get("code_verifier")
                del _oauth_state_map[key]
                break

    tokens = await adapter.authenticate(auth_code=req.code, code_verifier=code_verifier)

    # Fetch user email/profile from the provider
    email, display_name = await _fetch_user_profile(req.provider, tokens.access_token)

    # Determine scopes
    from ingestion.providers.gmail import SCOPES as GMAIL_SCOPES
    from ingestion.providers.outlook import SCOPES as OUTLOOK_SCOPES

    scopes = GMAIL_SCOPES if req.provider == EP.GMAIL else OUTLOOK_SCOPES

    account = await save_account(
        provider=req.provider.value,
        email=email,
        display_name=display_name,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_expiry=tokens.token_expiry,
        scopes=scopes,
    )

    logger.info("account connected", provider=req.provider.value, email=email)

    # Trigger an initial email sync in the background
    background_tasks.add_task(_run_sync_for_provider, req.provider)

    return AuthCallbackResponse(provider=req.provider.value, email=email, account_id=str(account["id"]))


async def _run_sync_for_provider(provider: EP) -> IngestResult:
    """Run an incremental sync for all accounts of a provider. Shared logic for endpoints and background tasks."""
    accounts = await get_accounts_by_provider(provider.value)
    if not accounts:
        logger.warning("sync skipped: no accounts", provider=provider.value)
        return IngestResult(provider=provider)

    result = IngestResult(provider=provider)

    for acct in accounts:
        tokens = OAuthTokens(
            access_token=acct["access_token"],
            refresh_token=acct["refresh_token"],
            token_expiry=acct["token_expiry"],
        )
        adapter = _make_provider(provider, tokens)
        await adapter.authenticate()

        state = await get_sync_state(provider)
        since_token = state.get("history_id") if provider == EP.GMAIL else state.get("delta_link")
        raw_emails, new_sync_token = await adapter.fetch_new_emails(since_token=since_token)
        result.total_fetched += len(raw_emails)

        for raw in raw_emails:
            markdown_body = email_body_to_markdown(raw.html_body, raw.text_body)
            stored = await upsert_email(raw, markdown_body)
            if stored:
                result.new_stored += 1
                await publish_new_email(stored)
            else:
                result.duplicates_skipped += 1

        if new_sync_token:
            if provider == EP.GMAIL:
                await save_sync_state(provider, history_id=new_sync_token)
            else:
                await save_sync_state(provider, delta_link=new_sync_token)

    logger.info(
        "sync completed",
        provider=provider.value,
        fetched=result.total_fetched,
        new=result.new_stored,
        duplicates=result.duplicates_skipped,
    )
    return result


# ─── Device Authorization Flow ───


@router.post("/auth/device/{provider}")
async def start_device_flow(provider: EP) -> DeviceFlowStartResponse:
    """Start the OAuth device authorization flow for a provider."""
    if provider == EP.GMAIL:
        from ingestion.providers.gmail import SCOPES as GMAIL_SCOPES

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/device/code",
                data={"client_id": settings.google_client_id, "scope": " ".join(GMAIL_SCOPES)},
            )
            if resp.status_code != 200:
                detail = resp.json().get("error_description", resp.text)
                raise HTTPException(status_code=400, detail=f"Google device flow not available: {detail}")
            data = resp.json()

        return DeviceFlowStartResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_url"],
            verification_uri_complete=data.get("verification_url"),
            expires_in=data.get("expires_in", 1800),
            interval=data.get("interval", 5),
        )

    elif provider == EP.OUTLOOK:
        from ingestion.providers.outlook import SCOPES as OUTLOOK_SCOPES

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/devicecode",
                data={"client_id": settings.ms_client_id, "scope": " ".join(OUTLOOK_SCOPES)},
            )
            if resp.status_code != 200:
                detail = resp.json().get("error_description", resp.text)
                raise HTTPException(status_code=400, detail=f"Microsoft device flow not available: {detail}")
            data = resp.json()

        return DeviceFlowStartResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            verification_uri_complete=data.get("verification_uri_complete"),
            expires_in=data.get("expires_in", 900),
            interval=data.get("interval", 5),
        )

    raise HTTPException(status_code=400, detail=f"Device flow not supported for {provider}")


@router.post("/auth/device/{provider}/poll")
async def poll_device_flow(provider: EP, device_code: str) -> DeviceFlowPollResponse:
    """Poll the device authorization flow to check if the user has authorized."""
    if provider == EP.GMAIL:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
        data = resp.json()
        if "error" in data:
            if data["error"] in ("authorization_pending", "slow_down"):
                return DeviceFlowPollResponse(status="pending")
            if data["error"] == "expired_token":
                return DeviceFlowPollResponse(status="expired")
            raise HTTPException(status_code=400, detail=data.get("error_description", data["error"]))

        access_token = data["access_token"]
        refresh_token = data.get("refresh_token")
        from datetime import datetime, timezone

        token_expiry = datetime.now(tz=timezone.utc).replace(
            second=datetime.now(tz=timezone.utc).second + data.get("expires_in", 3600)
        )

    elif provider == EP.OUTLOOK:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": settings.ms_client_id,
                    "client_secret": settings.ms_client_secret,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
        data = resp.json()
        if "error" in data:
            if data["error"] in ("authorization_pending", "slow_down"):
                return DeviceFlowPollResponse(status="pending")
            if data["error"] == "expired_token":
                return DeviceFlowPollResponse(status="expired")
            raise HTTPException(status_code=400, detail=data.get("error_description", data["error"]))

        access_token = data["access_token"]
        refresh_token = data.get("refresh_token")
        from datetime import datetime, timezone

        token_expiry = datetime.now(tz=timezone.utc).replace(
            second=datetime.now(tz=timezone.utc).second + data.get("expires_in", 3600)
        )
    else:
        raise HTTPException(status_code=400, detail=f"Device flow not supported for {provider}")

    email, display_name = await _fetch_user_profile(provider, access_token)

    from ingestion.providers.gmail import SCOPES as GMAIL_SCOPES
    from ingestion.providers.outlook import SCOPES as OUTLOOK_SCOPES

    scopes = GMAIL_SCOPES if provider == EP.GMAIL else OUTLOOK_SCOPES

    account = await save_account(
        provider=provider.value,
        email=email,
        display_name=display_name,
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=token_expiry,
        scopes=scopes,
    )

    logger.info("account connected via device flow", provider=provider.value, email=email)
    return DeviceFlowPollResponse(status="complete", account_id=str(account["id"]), email=email)


# ─── Account Management ───


@router.get("/accounts")
async def get_accounts() -> list[AccountResponse]:
    """List all connected accounts."""
    accounts = await list_accounts()
    return [
        AccountResponse(
            id=str(a["id"]),
            provider=a["provider"],
            email=a["email"],
            display_name=a["display_name"],
            scopes=list(a["scopes"]),
            created_at=a["created_at"].isoformat(),
            updated_at=a["updated_at"].isoformat(),
        )
        for a in accounts
    ]


@router.delete("/accounts/{account_id}")
async def disconnect_account(account_id: UUID) -> dict:
    """Disconnect (delete) a connected account."""
    deleted = await delete_account(str(account_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
    logger.info("account disconnected", account_id=str(account_id))
    return {"detail": "Account disconnected"}


# ─── Email Sync (now multi-account) ───


@router.post("/sync/{provider}")
async def sync_emails(provider: EP, max_results: int = Query(100, ge=1, le=500)) -> IngestResult:
    """Run an incremental sync for all accounts of a provider."""
    accounts = await get_accounts_by_provider(provider.value)
    if not accounts:
        raise HTTPException(status_code=401, detail=f"No accounts connected for {provider.value}. Connect an account first.")
    return await _run_sync_for_provider(provider)


@router.post("/fetch/{provider}")
async def fetch_emails(
    provider: EP,
    max_results: int = Query(100, ge=1, le=500),
    page_token: str | None = Query(None),
) -> IngestResult:
    """Fetch a batch of emails from all accounts of a provider."""
    accounts = await get_accounts_by_provider(provider.value)
    if not accounts:
        raise HTTPException(status_code=401, detail=f"No accounts connected for {provider.value}. Connect an account first.")

    result = IngestResult(provider=provider)

    for acct in accounts:
        tokens = OAuthTokens(
            access_token=acct["access_token"],
            refresh_token=acct["refresh_token"],
            token_expiry=acct["token_expiry"],
        )
        adapter = _make_provider(provider, tokens)
        await adapter.authenticate()

        raw_emails = await adapter.fetch_emails(max_results=max_results, page_token=page_token)
        result.total_fetched += len(raw_emails)

        for raw in raw_emails:
            markdown_body = email_body_to_markdown(raw.html_body, raw.text_body)
            stored = await upsert_email(raw, markdown_body)
            if stored:
                result.new_stored += 1
                await publish_new_email(stored)
            else:
                result.duplicates_skipped += 1

    logger.info(
        "batch fetch completed",
        provider=provider.value,
        fetched=result.total_fetched,
        new=result.new_stored,
        duplicates=result.duplicates_skipped,
    )
    return result


# ─── Email Browsing ───


class EmailListResponse(BaseModel):
    emails: list[dict]
    total: int
    limit: int
    offset: int


@router.get("/emails")
async def get_emails(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: str | None = Query(None),
    search: str | None = Query(None),
) -> EmailListResponse:
    """List stored emails with pagination, optional provider filter, and text search."""
    emails, total = await list_emails(limit=limit, offset=offset, provider=provider, search=search)
    return EmailListResponse(
        emails=[e.model_dump(mode="json") for e in emails],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/emails/{email_id}")
async def get_email(email_id: str) -> dict:
    """Get a single email by ID."""
    email = await get_email_by_id(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email.model_dump(mode="json")


# ─── Helpers ───


async def _fetch_user_profile(provider: EP, access_token: str) -> tuple[str, str]:
    """Fetch the user's email and display name from the provider."""
    if provider == EP.GMAIL:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("email", ""), data.get("name", "")
    elif provider == EP.OUTLOOK:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("mail", data.get("userPrincipalName", "")), data.get("displayName", "")
    return "", ""
