from abc import ABC, abstractmethod

from ingestion.schemas import EmailProvider, OAuthTokens, RawEmail


class BaseEmailProvider(ABC):
    """Abstract base class for email provider adapters."""

    @property
    @abstractmethod
    def provider(self) -> EmailProvider:
        """Return the provider identifier."""
        ...

    @abstractmethod
    async def authenticate(self, auth_code: str | None = None, code_verifier: str | None = None) -> OAuthTokens:
        """Authenticate with the provider. If auth_code is provided, exchange it for tokens.
        Otherwise, attempt to use stored refresh token.
        """
        ...

    @abstractmethod
    async def fetch_emails(self, *, max_results: int = 100, page_token: str | None = None) -> list[RawEmail]:
        """Fetch a batch of emails from the provider.

        Args:
            max_results: Maximum number of emails to fetch in this batch.
            page_token: Provider-specific pagination token for fetching next page.

        Returns:
            List of raw email objects.
        """
        ...

    @abstractmethod
    async def fetch_new_emails(self, since_token: str | None = None) -> tuple[list[RawEmail], str | None]:
        """Fetch only new/changed emails since the last sync point.

        Args:
            since_token: Provider-specific incremental sync token
                         (Gmail history ID or Outlook delta link).

        Returns:
            Tuple of (emails, new_sync_token).
        """
        ...

    @abstractmethod
    def get_auth_url(self, state: str | None = None) -> tuple[str, str | None]:
        """Return (auth_url, code_verifier) tuple for the OAuth authorization flow."""
        ...
