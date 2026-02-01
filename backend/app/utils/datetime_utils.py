"""
DateTime utility functions for consistent timezone handling
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Get current UTC datetime with timezone awareness

    Returns:
        datetime: Current UTC datetime with timezone set to UTC
    """
    return datetime.now(timezone.utc)


def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """
    Serialize datetime to ISO format with timezone

    Ensures that timezone-aware datetimes are properly serialized.
    If datetime is None, returns None.
    If datetime is timezone-naive, treats it as UTC and adds timezone info.

    Args:
        dt: Datetime object (can be None, timezone-aware, or timezone-naive)

    Returns:
        ISO format string with timezone offset, or None if dt is None
    """
    if dt is None:
        return None

    # If timezone-naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat()


def serialize_datetime_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    Serialize datetime to ISO format with 'Z' suffix for UTC

    This format is commonly used in APIs (e.g., "2026-01-31T10:00:00Z").
    If datetime is None, returns None.
    If datetime is timezone-naive, treats it as UTC.

    Args:
        dt: Datetime object (can be None, timezone-aware, or timezone-naive)

    Returns:
        ISO format string with 'Z' suffix, or None if dt is None
    """
    if dt is None:
        return None

    # If timezone-naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to UTC if timezone-aware
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace('+00:00', 'Z')


def parse_datetime_iso(iso_string: str) -> datetime:
    """
    Parse ISO format datetime string to timezone-aware datetime

    Handles strings with or without timezone info. If no timezone,
    assumes UTC.

    Args:
        iso_string: ISO format datetime string

    Returns:
        Timezone-aware datetime (UTC)
    """
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))

    # If timezone-naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt
