"""Timezone-aware UTC timestamps for ORM defaults and persistence."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return naive UTC — matches SQLite DateTime storage and legacy rows."""
    return datetime.now(UTC).replace(tzinfo=None)
