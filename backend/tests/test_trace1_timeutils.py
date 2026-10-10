from app.shared import timeutils
from datetime import datetime, timezone, timedelta

def test_utc_evening_is_next_day_in_pakistan():
  assert timeutils.to_local_date(datetime(2026, 10, 31, 20, 0, tzinfo=timezone.utc)).isoformat() == "2026-11-01"

def test_midday_stays_same_day():
  assert timeutils.to_local_date(datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc)).isoformat() == "2026-10-10"

def test_naive_datetime_is_treated_as_utc():
  assert timeutils.to_local_date(datetime(2026, 10, 31, 20, 0)).isoformat() == "2026-11-01"

def test_local_tz_is_utc_plus_5():
  assert datetime(2026, 1, 1, tzinfo=timeutils.local_tz()).utcoffset() == timedelta(hours=5)