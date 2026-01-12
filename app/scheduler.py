
# app/scheduler.py
from __future__ import annotations
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram.constants import ParseMode
from app.reports import load_expenses_between, summarize_by_category

logger = logging.getLogger(__name__)

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
    now = datetime.now(IST)
    start, end = week_bounds_ist(now)

    if not DATA_DIR.exists():
        logger.warning("DATA_DIR missing: %s", DATA_DIR)
        return

    users = [p for p in DATA_DIR.iterdir() if p.is_dir()]
    logger.info("Weekly summary: %d user dirs in %s", len(users), DATA_DIR)

    for user_dir in users:
        username = user_dir.name
        cfg_file = user_dir / "config.json"
        if not cfg_file.exists():
            logger.warning("No config.json for user '%s'", username)
            continue

        try:
            cfg = json.load(cfg_file.open())
        except Exception as e:
            logger.exception("Failed to load config.json for '%s': %s", username, e)
            continue

        chat_id = cfg.get("chat_id")
        if chat_id is None:
            logger.warning("Missing chat_id for '%s'", username)
            continue
        if isinstance(chat_id, str) and chat_id.isdigit():
            chat_id = int(chat_id)

        df = load_expenses_between(username, start, end)
        rows = 0 if df is None else len(df)
        logger.info("User '%s': weekly rows=%d, chat_id=%s", username, rows, chat_id)

        text = (
            f"*Weekly Summary (Mon–Sun)*\n"
            f"Period: {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n"
            f"{summarize_by_category(df)}"
        )

        try:
            await application.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
            logger.info("Sent weekly summary to '%s' (chat_id=%s)", username, chat_id)
        except Exception as e:
            logger.exception("Failed to send summary to '%s' (chat_id=%s): %s", username, chat_id, e)
