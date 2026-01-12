from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def now_ist() -> datetime:
    return datetime.now(IST)

def month_key(dt: datetime) -> str:
    dt = dt.astimezone(IST)
    return dt.strftime("%Y_%m")

def month_bounds(dt: datetime):
    dt = dt.astimezone(IST)
    first = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if dt.month == 12:
        next_first = first.replace(year=dt.year + 1, month=1)
    else:
        next_first = first.replace(month=dt.month + 1)
    last = next_first - timedelta(seconds=1)
    return first, last

def week_bounds(dt: datetime):
    dt = dt.astimezone(IST)
    monday = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday

def week_index_in_month(dt: datetime) -> int:
    dt = dt.astimezone(IST)
    first_day = dt.replace(day=1)
    first_sunday = first_day + timedelta(days=(6 - first_day.weekday()) % 7)
    if dt.date() <= first_sunday.date():
        return 1
    delta = (dt.date() - (first_sunday + timedelta(days=1)).date()).days
    return min(2 + delta // 7, 5)
