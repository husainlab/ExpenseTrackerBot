
# app/utils_time.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def now_ist() -> datetime:
    return datetime.now(IST)

def month_key(dt: datetime) -> str:
    """e.g., 2026_01 for January 2026"""
    return dt.strftime("%Y_%m")

def week_index_in_month(dt: datetime) -> int:
    """
    Return week index 1..5 within the calendar month.
    Rule:
      - Week 1 starts on the *first day of the month* and ends on that Sunday's end.
      - Subsequent weeks are Monday–Sunday blocks.
      - Cap at 5 (some months partially fill Week 5).
    """
    first = dt.replace(day=1)
    # Week1 ends on the first Sunday of the month
    first_sunday_offset = (6 - first.weekday()) % 7  # Monday=0..Sunday=6
    week1_end = first + timedelta(days=first_sunday_offset)

    if dt.date() <= week1_end.date():
        return 1

    # First Monday after week1_end
    first_monday = week1_end + timedelta(days=1)
    while first_monday.weekday() != 0:
        first_monday += timedelta(days=1)

    delta_days = (dt.date() - first_monday.date()).days
    idx = 2 + (delta_days // 7)
    return min(idx, 5)
``
