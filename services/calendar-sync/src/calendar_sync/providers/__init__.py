"""Abstract base class for calendar providers."""

from abc import ABC, abstractmethod
from datetime import datetime


class BaseCalendarProvider(ABC):
    """Abstract calendar provider for syncing events."""

    @abstractmethod
    async def list_calendars(self) -> list[dict]:
        """List all calendars for this account. Returns list of normalized calendar dicts."""
        ...

    @abstractmethod
    async def fetch_events(
        self, calendar_id: str = "primary", time_min: datetime | None = None, time_max: datetime | None = None
    ) -> list[dict]:
        """Fetch events from the provider. Returns list of normalized event dicts."""
        ...

    @abstractmethod
    async def create_event(self, calendar_id: str, event_data: dict) -> dict:
        """Create a new event. Returns normalized event dict."""
        ...

    @abstractmethod
    async def update_event(self, calendar_id: str, event_id: str, event_data: dict) -> dict:
        """Update an existing event. Returns normalized event dict."""
        ...
