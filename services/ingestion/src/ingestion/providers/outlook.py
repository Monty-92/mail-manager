import json
from datetime import datetime, timezone
from email.utils import parseaddr

import httpx
import msal
import structlog

from ingestion.config import settings
from ingestion.providers import BaseEmailProvider
from ingestion.schemas import EmailProvider, OAuthTokens, RawEmail

logger = structlog.get_logger()

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read", "User.Read", "Calendars.ReadWrite"]


class OutlookProvider(BaseEmailProvider):
    """Microsoft Graph API email provider adapter for Outlook (personal accounts)."""

    def __init__(self, tokens: OAuthTokens | None = None) -> None:
        self._tokens = tokens
        self._msal_app = msal.ConfidentialClientApplication(
            client_id=settings.ms_client_id,
            client_credential=settings.ms_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
        )

    @property
    def provider(self) -> EmailProvider:
        return EmailProvider.OUTLOOK

    def get_auth_url(self, state: str | None = None) -> tuple[str, str | None]:
        """Return (auth_url, serialized_auth_code_flow) tuple.

        Uses MSAL's initiate_auth_code_flow() which manages PKCE internally.
        The serialized auth_code_flow must be passed back to authenticate() on callback.
        """
        kwargs: dict = {
            "scopes": SCOPES,
            "redirect_uri": settings.ms_redirect_uri,
        }
        if state:
            kwargs["state"] = state
        auth_code_flow = self._msal_app.initiate_auth_code_flow(**kwargs)
        return auth_code_flow["auth_uri"], json.dumps(auth_code_flow)

    async def authenticate(self, auth_code: str | None = None, code_verifier: str | None = None) -> OAuthTokens:
        if auth_code:
            # code_verifier holds the JSON-serialized auth_code_flow from initiate_auth_code_flow()
            if code_verifier:
                try:
                    auth_code_flow = json.loads(code_verifier)
                    # auth_response must include the echoed state for CSRF validation
                    auth_response = {"code": auth_code, "state": auth_code_flow.get("state", "")}
                    result = self._msal_app.acquire_token_by_auth_code_flow(auth_code_flow, auth_response)
                except (json.JSONDecodeError, TypeError):
                    # Fallback for legacy callers that don't pass the flow dict
                    result = self._msal_app.acquire_token_by_authorization_code(
                        code=auth_code,
                        scopes=SCOPES,
                        redirect_uri=settings.ms_redirect_uri,
                    )
            else:
                result = self._msal_app.acquire_token_by_authorization_code(
                    code=auth_code,
                    scopes=SCOPES,
                    redirect_uri=settings.ms_redirect_uri,
                )
        elif self._tokens and self._tokens.refresh_token:
            result = self._msal_app.acquire_token_by_refresh_token(
                refresh_token=self._tokens.refresh_token,
                scopes=SCOPES,
            )
        else:
            raise ValueError("Either auth_code or existing tokens with refresh_token must be provided")

        if "error" in result:
            raise RuntimeError(f"MSAL auth error: {result.get('error_description', result.get('error'))}")

        access_token = result["access_token"]
        refresh_token = result.get("refresh_token")
        expires_in = result.get("expires_in", 3600)
        expiry = datetime.now(tz=timezone.utc).replace(microsecond=0)
        expiry = expiry.replace(second=expiry.second + expires_in)

        self._tokens = OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=expiry,
        )
        logger.info("outlook authenticated")
        return self._tokens

    def _auth_headers(self) -> dict[str, str]:
        if self._tokens is None:
            raise RuntimeError("Outlook provider not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self._tokens.access_token}"}

    async def fetch_emails(self, *, max_results: int = 100, page_token: str | None = None) -> list[RawEmail]:
        url = page_token or (
            f"{GRAPH_BASE_URL}/me/messages"
            f"?$top={max_results}&$orderby=receivedDateTime desc"
            f"&$select=id,conversationId,from,toRecipients,ccRecipients,bccRecipients,"
            f"subject,receivedDateTime,categories,body"
        )

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._auth_headers(), timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

        emails: list[RawEmail] = []
        for msg in data.get("value", []):
            raw = _parse_graph_message(msg)
            if raw:
                emails.append(raw)

        logger.info("outlook batch fetched", count=len(emails))
        return emails

    async def fetch_new_emails(self, since_token: str | None = None) -> tuple[list[RawEmail], str | None]:
        if since_token is None:
            # First sync — use delta query to get initial state
            url = (
                f"{GRAPH_BASE_URL}/me/mailFolders/inbox/messages/delta"
                f"?$top=100&$select=id,conversationId,from,toRecipients,ccRecipients,"
                f"bccRecipients,subject,receivedDateTime,categories,body"
            )
        else:
            url = since_token  # Delta link from previous sync

        all_emails: list[RawEmail] = []
        new_delta_link: str | None = None

        async with httpx.AsyncClient() as client:
            while url:
                resp = await client.get(url, headers=self._auth_headers(), timeout=30.0)
                resp.raise_for_status()
                data = resp.json()

                for msg in data.get("value", []):
                    # Skip deleted items (they have @removed)
                    if "@removed" in msg:
                        continue
                    raw = _parse_graph_message(msg)
                    if raw:
                        all_emails.append(raw)

                # Follow @odata.nextLink for pagination, or grab deltaLink when done
                url = data.get("@odata.nextLink")
                if not url:
                    new_delta_link = data.get("@odata.deltaLink")

        logger.info("outlook delta fetch", count=len(all_emails), had_previous_delta=since_token is not None)
        return all_emails, new_delta_link


def _parse_graph_message(msg: dict) -> RawEmail | None:
    """Parse a Microsoft Graph message object into a RawEmail."""
    try:
        sender_data = msg.get("from", {}).get("emailAddress", {})
        sender = sender_data.get("address", "")

        recipients: list[str] = []
        for field in ("toRecipients", "ccRecipients", "bccRecipients"):
            for r in msg.get(field, []):
                addr = r.get("emailAddress", {}).get("address", "")
                if addr:
                    recipients.append(addr)

        body = msg.get("body", {})
        content_type = body.get("contentType", "text")
        content = body.get("content", "")

        html_body = content if content_type == "html" else ""
        text_body = content if content_type == "text" else ""

        received_str = msg.get("receivedDateTime", "")
        if received_str:
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        else:
            received_at = datetime.now(tz=timezone.utc)

        return RawEmail(
            provider=EmailProvider.OUTLOOK,
            external_id=msg["id"],
            thread_id=msg.get("conversationId"),
            sender=sender,
            recipients=recipients,
            subject=msg.get("subject", ""),
            received_at=received_at,
            labels=msg.get("categories", []),
            html_body=html_body,
            text_body=text_body,
        )
    except (KeyError, TypeError):
        logger.warning("failed to parse outlook message", message_id=msg.get("id"))
        return None
