import base64
from datetime import datetime, timezone
from email.utils import parseaddr

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from ingestion.config import settings
from ingestion.providers import BaseEmailProvider
from ingestion.schemas import EmailProvider, OAuthTokens, RawEmail

logger = structlog.get_logger()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]


class GmailProvider(BaseEmailProvider):
    """Gmail API email provider adapter."""

    def __init__(self, tokens: OAuthTokens | None = None) -> None:
        self._tokens = tokens
        self._credentials: Credentials | None = None
        self._service = None

    @property
    def provider(self) -> EmailProvider:
        return EmailProvider.GMAIL

    def _get_flow(self) -> Flow:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=settings.google_redirect_uri,
        )
        return flow

    def get_auth_url(self, state: str | None = None) -> tuple[str, str | None]:
        """Return (auth_url, code_verifier) tuple. code_verifier must be stored for token exchange."""
        flow = self._get_flow()
        kwargs: dict = {"prompt": "consent", "access_type": "offline"}
        if state:
            kwargs["state"] = state
        auth_url, _ = flow.authorization_url(**kwargs)
        return auth_url, flow.code_verifier

    async def authenticate(self, auth_code: str | None = None, code_verifier: str | None = None) -> OAuthTokens:
        if auth_code:
            flow = self._get_flow()
            flow.code_verifier = code_verifier
            flow.fetch_token(code=auth_code)
            self._credentials = flow.credentials
        elif self._tokens:
            self._credentials = Credentials(
                token=self._tokens.access_token,
                refresh_token=self._tokens.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
            )
            if self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
        else:
            raise ValueError("Either auth_code or existing tokens must be provided")

        self._service = build("gmail", "v1", credentials=self._credentials)
        logger.info("gmail authenticated")

        return OAuthTokens(
            access_token=self._credentials.token,
            refresh_token=self._credentials.refresh_token,
            token_expiry=self._credentials.expiry.replace(tzinfo=timezone.utc) if self._credentials.expiry else None,
        )

    def _ensure_service(self) -> None:
        if self._service is None:
            raise RuntimeError("Gmail provider not authenticated. Call authenticate() first.")

    def _fetch_label_map(self) -> dict[str, str]:
        """Fetch Gmail label ID→name mapping. Returns dict of {id: name}."""
        self._ensure_service()
        try:
            result = self._service.users().labels().list(userId="me").execute()
            return {lbl["id"]: lbl["name"] for lbl in result.get("labels", [])}
        except Exception:
            logger.warning("failed to fetch gmail label map")
            return {}

    async def fetch_emails(self, *, max_results: int = 100, page_token: str | None = None) -> list[RawEmail]:
        self._ensure_service()
        label_map = self._fetch_label_map()
        kwargs: dict = {"userId": "me", "maxResults": max_results}
        if page_token:
            kwargs["pageToken"] = page_token

        result = self._service.users().messages().list(**kwargs).execute()
        message_ids = [m["id"] for m in result.get("messages", [])]

        emails: list[RawEmail] = []
        for msg_id in message_ids:
            raw = await self._fetch_single_message(msg_id, label_map)
            if raw:
                emails.append(raw)

        logger.info("gmail batch fetched", count=len(emails), page_token=page_token)
        return emails

    async def fetch_new_emails(self, since_token: str | None = None) -> tuple[list[RawEmail], str | None]:
        self._ensure_service()
        label_map = self._fetch_label_map()

        if since_token is None:
            # First sync — get current history ID and fetch last batch
            profile = self._service.users().getProfile(userId="me").execute()
            new_history_id = str(profile.get("historyId", ""))
            emails = await self.fetch_emails(max_results=100)
            return emails, new_history_id

        # Incremental sync via history API
        try:
            history_result = self._service.users().history().list(
                userId="me",
                startHistoryId=since_token,
                historyTypes=["messageAdded"],
            ).execute()
        except Exception:
            logger.warning("gmail history sync failed, falling back to full fetch", history_id=since_token)
            profile = self._service.users().getProfile(userId="me").execute()
            new_history_id = str(profile.get("historyId", ""))
            emails = await self.fetch_emails(max_results=50)
            return emails, new_history_id

        new_history_id = str(history_result.get("historyId", since_token))
        message_ids: list[str] = []
        for record in history_result.get("history", []):
            for added in record.get("messagesAdded", []):
                message_ids.append(added["message"]["id"])

        emails: list[RawEmail] = []
        for msg_id in message_ids:
            raw = await self._fetch_single_message(msg_id, label_map)
            if raw:
                emails.append(raw)

        logger.info("gmail incremental fetch", count=len(emails), old_history_id=since_token)
        return emails, new_history_id

    async def _fetch_single_message(self, message_id: str, label_map: dict[str, str] | None = None) -> RawEmail | None:
        """Fetch and parse a single Gmail message."""
        try:
            msg = self._service.users().messages().get(userId="me", id=message_id, format="full").execute()
        except Exception:
            logger.warning("failed to fetch gmail message", message_id=message_id)
            return None

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")
        recipients = _parse_recipients(headers)
        subject = headers.get("subject", "")
        received_at = _parse_gmail_timestamp(msg.get("internalDate", "0"))
        raw_labels = msg.get("labelIds", [])
        labels = [label_map.get(lbl, lbl) if label_map else lbl for lbl in raw_labels]
        thread_id = msg.get("threadId")

        html_body, text_body = _extract_body_parts(msg.get("payload", {}))

        return RawEmail(
            provider=EmailProvider.GMAIL,
            external_id=message_id,
            thread_id=thread_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            received_at=received_at,
            labels=labels,
            html_body=html_body,
            text_body=text_body,
        )


def _parse_recipients(headers: dict[str, str]) -> list[str]:
    """Extract recipient email addresses from To, Cc, Bcc headers."""
    recipients: list[str] = []
    for field in ("to", "cc", "bcc"):
        value = headers.get(field, "")
        if value:
            for part in value.split(","):
                _, addr = parseaddr(part.strip())
                if addr:
                    recipients.append(addr)
    return recipients


def _parse_gmail_timestamp(internal_date: str) -> datetime:
    """Convert Gmail internalDate (epoch millis string) to datetime."""
    try:
        epoch_ms = int(internal_date)
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        return datetime.now(tz=timezone.utc)


def _extract_body_parts(payload: dict) -> tuple[str, str]:
    """Recursively extract HTML and plain text body from a Gmail message payload."""
    html_body = ""
    text_body = ""

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/html" and body_data:
        html_body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
    elif mime_type == "text/plain" and body_data:
        text_body = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        h, t = _extract_body_parts(part)
        if h:
            html_body = h
        if t:
            text_body = t

    return html_body, text_body
