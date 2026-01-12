import json
from datetime import datetime
from pathlib import Path
from telegram.constants import ParseMode
from app.utils_time import now_ist, week_bounds, month_bounds
from app.reports import load_expenses_between, summarize_by_category
from app.storage_git import load_config

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

async def send_weekly_summaries(app):
    now = now_ist()
    start, end = week_bounds(now)
    for user in DATA_DIR.iterdir():
        if not user.is_dir():
            continue
        cfg = load_config(user.name)
        df = load_expenses_between(user.name, start, end)
        text = f"*Weekly Summary*\n{summarize_by_category(df)}"
        await app.bot.send_message(cfg["chat_id"], text, parse_mode=ParseMode.MARKDOWN)

async def send_monthly_insights(app):
    now = now_ist()
    start, end = month_bounds(now)
    prev_start, prev_end = month_bounds(start.replace(day=1) - timedelta(days=1))

    for user in DATA_DIR.iterdir():
        if not user.is_dir():
            continue
        cfg = load_config(user.name)
        df = load_expenses_between(user.name, start, end)
        prev = load_expenses_between(user.name, prev_start, prev_end)

        total = df["amount"].sum() if not df.empty else 0
        text = f"*Monthly Insight*\nTotal: ₹{total:.0f}\n\n"
        text += summarize_by_category(df)

        if not prev.empty:
            diff = total - prev["amount"].sum()
            text += f"\n\nChange vs last month: ₹{diff:.0f}"

        await app.bot.send_message(cfg["chat_id"], text, parse_mode=ParseMode.MARKDOWN)
