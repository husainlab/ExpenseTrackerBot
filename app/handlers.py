import re
from telegram import Update, ReplyParameters
from telegram.ext import ContextTypes
from app.storage_git import (
    ensure_user_dir, write_expense, delete_user_data,
    git_commit_push, load_config, save_config
)
from app.reports import load_expenses_between, summarize_by_category
from app.utils_time import now_ist, week_bounds, month_bounds

MENU = """Index Menu:
1. expense this week
2. expense last week
3. expense this month
4. expense last month
5. budget status
6. delete all my data
7. help
8. expense today
9. expense yesterday
10. categories this month
11. export this month
12. AI insights
"""

EXPENSE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s+(\w+)(?:\s+(.*))?$")

PENDING_DELETE = set()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user = msg.from_user
    user_id = str(user.id)

    if not ensure_user_dir(user_id, msg.chat.id, user.username or ""):
        await msg.reply_text("User limit reached.")
        return

    if text == "DELETE" and user_id in PENDING_DELETE:
        delete_user_data(user_id)
        git_commit_push(f"Delete data for {user_id}")
        PENDING_DELETE.remove(user_id)
        await msg.reply_text("Your data has been deleted.")
        return

    m = EXPENSE_RE.match(text)
    if m:
        amount = float(m.group(1))
        category = m.group(2).lower()
        note = m.group(3) or ""
        write_expense(user_id, amount, category, note)
        git_commit_push("Add expense")
        await msg.reply_text(f"Saved ₹{amount:.2f} in {category}")
        return

    if text == "6":
        PENDING_DELETE.add(user_id)
        await msg.reply_text("⚠️ Type DELETE to confirm.")
        return

    if text == "7":
        await msg.reply_text(MENU)
        return

    await msg.reply_text(MENU)
