
# app/utils_time.py
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# IST timezone (Asia/Kolkata)
IST = ZoneInfo("Asia/Kolkata")

def now_ist() -> datetime:
    """Return current time in IST (timezone-aware)."""
    return datetime.now(IST)

def month_key(dt: datetime) -> str:
    """Return YYYY_MM string for the month, e.g., 2026_01."""
    return dt.strftime("%Y_%m")

def week_index_in_month(dt: datetime) -> int:
    """
    Return week index 1..5 within the calendar month with your rule:
      - Week 1 starts on the first calendar day and ends on that Sunday's end.
      - Subsequent weeks are Monday–Sunday blocks.
      - Cap at 5 (some months partially fill Week 5).
    """
    first_day = dt.replace(day=1)

    # Week 1: from first calendar day to first Sunday
    # Python weekday: Monday=0 .. Sunday=6
    first_sunday_offset = (6 - first_day.weekday()) % 7
    week1_end = first_day + timedelta(days=first_sunday_offset)

    if dt.date() <= week1_end.date():
        return 1

    # First Monday after Week 1
    first_monday = week1_end + timedelta(days=1)
    while first_monday.weekday() != 0:
        first_monday += timedelta(days=1)

    # Count full Mon–Sun blocks after first_monday
    delta_days = (dt.date() - first_monday.date()).days
    idx = 2 + (delta_days // 7)

    # Cap at 5
    return min(idx, 5)
