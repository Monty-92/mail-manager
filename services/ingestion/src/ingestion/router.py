import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ingestion.config import settings
from ingestion.converter import email_body_to_markdown
from ingestion.providers import BaseEmailProvider
from ingestion.providers.gmail import GmailProvider
from ingestion.providers.outlook import OutlookProvider
from ingestion.publisher import publish_new_email
from ingestion.repository import get_sync_state, save_sync_state, upsert_email
from ingestion.schemas import EmailProvider as EP
from ingestion.schemas import IngestResult, OAuthTokens

logger = structlog.get_logger()

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# In-memory token store (production would use encrypted DB storage)
_token_store: dict[str, OAuthTokens] = {}


def _get_provider(provider: EP) -> BaseEmailProvider:
    tokens = _token_store.get(provider.value)
    if provider == EP.GMAIL:
        return GmailProvider(tokens=tokens)
    elif provider == EP.OUTLOOK:
        return OutlookProvider(tokens=tokens)
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


class AuthUrlResponse(BaseModel):
    auth_url: str
    provider: str


class AuthCallbackRequest(BaseModel):
    code: str
    provider: EP


class AuthCallbackResponse(BaseModel):
    provider: str
    authenticated: bool


@router.get("/auth/url/{provider}")
async def get_auth_url(provider: EP) -> AuthUrlResponse:
    """Get the OAuth authorization URL for a provider."""
    adapter = _get_provider(provider)
    url = adapter.get_auth_url()
    return AuthUrlResponse(auth_url=url, provider=provider.value)


@router.post("/auth/callback")
async def auth_callback(req: AuthCallbackRequest) -> AuthCallbackResponse:
    """Exchange an OAuth authorization code for tokens."""
    adapter = _get_provider(req.provider)
    tokens = await adapter.authenticate(auth_code=req.code)
    _token_store[req.provider.value] = tokens
    logger.info("oauth tokens stored", provider=req.provider.value)
    return AuthCallbackResponse(provider=req.provider.value, authenticated=True)


@router.post("/sync/{provider}")
async def sync_emails(provider: EP, max_results: int = Query(100, ge=1, le=500)) -> IngestResult:
    """Run an incremental sync for a provider. Falls back to full fetch on first run."""
    if provider.value not in _token_store:
        raise HTTPException(status_code=401, detail=f"Not authenticated with {provider.value}. Call /auth first.")

    adapter = _get_provider(provider)
    await adapter.authenticate()  # Refresh tokens if needed

    # Get sync state
    state = await get_sync_state(provider)
    since_token = state.get("history_id") if provider == EP.GMAIL else state.get("delta_link")

    # Fetch emails
    raw_emails, new_sync_token = await adapter.fetch_new_emails(since_token=since_token)

    # Convert and store
    result = IngestResult(provider=provider)
    result.total_fetched = len(raw_emails)

    for raw in raw_emails:
        markdown_body = email_body_to_markdown(raw.html_body, raw.text_body)
        stored = await upsert_email(raw, markdown_body)
        if stored:
            result.new_stored += 1
            await publish_new_email(stored)
        else:
            result.duplicates_skipped += 1

    # Save sync state
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


@router.post("/fetch/{provider}")
async def fetch_emails(
    provider: EP,
    max_results: int = Query(100, ge=1, le=500),
    page_token: str | None = Query(None),
) -> IngestResult:
    """Fetch a batch of emails (full history crawl, not incremental)."""
    if provider.value not in _token_store:
        raise HTTPException(status_code=401, detail=f"Not authenticated with {provider.value}. Call /auth first.")

    adapter = _get_provider(provider)
    await adapter.authenticate()

    raw_emails = await adapter.fetch_emails(max_results=max_results, page_token=page_token)

    result = IngestResult(provider=provider)
    result.total_fetched = len(raw_emails)

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
