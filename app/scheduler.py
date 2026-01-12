
# app/scheduler.py
from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path
from telegram.constants import ParseMode
from app.reports import load_expenses_between, summarize_by_category

IST = ZoneInfo("Asia/Kolkata")
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def week_bounds_ist(dt: datetime) -> tuple[datetime, datetime]:
    """Return Monday 00:00 to Sunday 23:59:59 bounds around dt (IST)."""
    today = dt.astimezone(IST)
    monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = (monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
    return monday, sunday

async def send_weekly_summaries(application):
    """
    Iterate through users; compute Mon–Sun for *this* week (ending Sunday today)
    and send per-category totals.
    """
    now = datetime.now(IST)
    start, end = week_bounds_ist(now)
    if not DATA_DIR.exists():
        return

    for user_dir in DATA_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        # chat_id from config.json
        cfg_file = user_dir / "config.json"
        if not cfg_file.exists():
            continue
        try:
            cfg = json.load(cfg_file.open())
        except Exception:
            continue
        chat_id = cfg.get("chat_id")
        username = user_dir.name

        df = load_expenses_between(username, start, end)
        text = f"*Weekly Summary (Mon–Sun)*\nPeriod: {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n"
        text += summarize_by_category(df)

        if chat_id:
            await application.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
