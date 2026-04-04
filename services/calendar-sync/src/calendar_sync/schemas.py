"""Pydantic schemas for the calendar-sync service."""

from datetime import datetime

from pydantic import BaseModel


class CalendarEventResponse(BaseModel):
    id: str
    provider: str
    external_id: str
    calendar_id: str
    title: str
    description: str
    start_at: str
    end_at: str
    all_day: bool
    location: str
    status: str
    organizer: str | None
    attendees: list[dict]
    created_at: str
    updated_at: str


class CalendarSourceResponse(BaseModel):
    id: str
    provider: str
    account_email: str
    calendar_name: str
    color: str
    enabled: bool


class SyncCalendarRequest(BaseModel):
    account_id: str | None = None


class SyncCalendarResponse(BaseModel):
    synced: int
    provider: str
    account_email: str


class CreateEventRequest(BaseModel):
    title: str
    description: str = ""
    start_at: str
    end_at: str
    all_day: bool = False
    location: str = ""


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    all_day: bool | None = None
    location: str | None = None
