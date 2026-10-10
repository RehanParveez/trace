from __future__ import annotations
from datetime import tzinfo, datetime, date, timedelta, timezone
from functools import lru_cache

_FALLBACK_TZ = timezone(timedelta(hours=5), "PKT")

@lru_cache(maxsize=1)
def local_tz() -> tzinfo:
  try:
    from zoneinfo import ZoneInfo
    from app.core.config import settings
    return ZoneInfo(settings.default_timezone)
  except Exception:
    return _FALLBACK_TZ

def now_local() -> datetime:
  return datetime.now(local_tz())

def today_local() -> date:
  return now_local().date()

def to_local_date(value: datetime) -> date:
  if value.tzinfo is None:
    value = value.replace(tzinfo=timezone.utc)
  return value.astimezone(local_tz()).date()