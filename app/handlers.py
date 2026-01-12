
# app/handlers.py
import re
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telegram import ReplyParameters, Update
from telegram.ext import ContextTypes
from app.storage_git import ensure_user_dir, write_expense, git_commit_push, DATA_DIR
from app.reports import load_expenses_between, summarize_by_category

IST = ZoneInfo("Asia/Kolkata")

MENU = (
    "Index Menu:\n"
    "1. expensethisweek\n"
    "2. expenselastweek\n"
    "3. expensethismonth\n"
    "4. expenselastmonth\n"
    "5. budgetstatus\n"
    "6. delete all my data\n"
    "7. help\n\n"
    "Send only a number after I show this menu.\n"
    "Or send expense in format: amount category (e.g., 200 food)"
)

EXPENSE_RE = re.compile(r"^\s*(\d+(?:\.\d{1,2})?)\s+([A-Za-z][\w\- ]{0,30})\s*$")
NUMBER_RE = re.compile(r"^\s*(\d{1,2})\s*$")

def _month_bounds_ist(dt: datetime):
    first = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(IST)
    # last day of month: go to next month first day minus 1s
    if dt.month == 12:
        next_first = dt.replace(year=dt.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        next_first = dt.replace(month=dt.month+1, day=1, hour=0, minute=0, second=0, microsecond=0)
    last = (next_first - timedelta(seconds=1)).astimezone(IST)
    return first, last

def _week_bounds_ist(dt: datetime):
    today = dt.astimezone(IST)
    monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = (monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)
    return monday, sunday

async def _send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.message.chat.id,
        text=MENU,
        reply_parameters=ReplyParameters(message_id=update.message.message_id),
    )

async def _handle_number(username: str, n: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    now = datetime.now(IST)

    if n == 1:  # this week
        start, end = _week_bounds_ist(now)
        df = load_expenses_between(username, start, end)
        text = f"*This Week (Mon–Sun)*\n{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n{summarize_by_category(df)}"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 2:  # last week
        start, end = _week_bounds_ist(now - timedelta(days=7))
        df = load_expenses_between(username, start, end)
        text = f"*Last Week (Mon–Sun)*\n{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n{summarize_by_category(df)}"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 3:  # this month
        start, end = _month_bounds_ist(now)
        df = load_expenses_between(username, start, end)
        text = f"*This Month*\n{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n{summarize_by_category(df)}"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 4:  # last month
        # Go to the 1st of current month, then subtract 1 day and get that month bounds
        first_this, _ = _month_bounds_ist(now)
        last_prev_day = first_this - timedelta(days=1)
        start, end = _month_bounds_ist(last_prev_day)
        df = load_expenses_between(username, start, end)
        text = f"*Last Month*\n{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n{summarize_by_category(df)}"
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown",
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 5:  # budgetstatus – will be implemented in Step 4
        await context.bot.send_message(chat_id=chat_id,
                                       text="Budget status will be available in the next step.",
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 6:  # delete all my data
        user_dir = DATA_DIR / username
        if user_dir.exists():
            shutil.rmtree(user_dir)
            git_commit_push(f"Delete all data for {username}")
            await context.bot.send_message(chat_id=chat_id,
                                           text="Your data has been deleted.",
                                           reply_parameters=ReplyParameters(message_id=update.message.message_id))
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text="No data found to delete.",
                                           reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    if n == 7:  # help
        await context.bot.send_message(chat_id=chat_id, text=MENU,
                                       reply_parameters=ReplyParameters(message_id=update.message.message_id))
        return

    # Any other number → show menu again
    await _send_menu(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or "").strip()
    username = msg.from_user.username or f"user_{msg.from_user.id}"

    ok = ensure_user_dir(username, msg.chat.id)
    if not ok:
        await context.bot.send_message(
            chat_id=msg.chat.id,
            text="Sorry, this bot is not accepting more users (>5).",
            reply_parameters=ReplyParameters(message_id=msg.message_id),
        )
        return

    # Expense format
    m = EXPENSE_RE.match(text)
    if m:
        amount = float(m.group(1))
        category = m.group(2).strip().lower()
        write_expense(username, amount, category)
        git_commit_push(f"Add expense: {amount} {category} by {username}")

        await context.bot.send_message(
            chat_id=msg.chat.id,
            text=f"Saved ₹{amount:.2f} in '{category}'.",
            reply_parameters=ReplyParameters(message_id=msg.message_id),
        )
        return

    # Numeric choice after menu
    n = NUMBER_RE.match(text)
    if n:
        await _handle_number(username, int(n.group(1)), update, context)
        return

    # Anything else → show menu
    await _send_menu(update, context)
