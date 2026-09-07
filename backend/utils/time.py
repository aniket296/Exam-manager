from datetime import datetime, timezone, timedelta
from typing import Optional

def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Converts a datetime object to ISO 8601 string in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def parse_iso(iso_str: Optional[str]) -> Optional[datetime]:
    """Parses an ISO 8601 string into a timezone-aware UTC datetime."""
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def is_expired(deadline: Optional[datetime], grace_seconds: int = 15) -> bool:
    """
    Authoritative server-side expiration check.
    Includes a small grace period for network latency on exam submissions.
    """
    if deadline is None:
        return False
    now = utc_now()
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return now > (deadline + timedelta(seconds=grace_seconds))

