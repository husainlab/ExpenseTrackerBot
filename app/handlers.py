
# app/handlers.py
import re
from telegram import ReplyParameters, Update
from telegram.ext import ContextTypes
from app.storage_git import ensure_user_dir, write_expense, git_commit_push

MENU = (
    "Index Menu:\n"
    "1. expensethisweek\n"
    "2. expenselastweek\n"
    "3. expensethismonth\n"
    "4. expenselastmonth\n"
    "5. budgetstatus\n"
    "6. delete all my data\n"
    "7. help\n"
    "\n"
    "Send only a number after I show this menu.\n"
    "Or send expense in format: amount category (e.g., 200 food)"
)

# amount category (allow decimals & hyphen/spaces in category)
EXPENSE_RE = re.compile(r"^\s*(\d+(?:\.\d{1,2})?)\s+([A-Za-z][\w\- ]{0,30})\s*$")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or "").strip()
    username = msg.from_user.username or f"user_{msg.from_user.id}"

    # Enforce max 5 users
    ok = ensure_user_dir(username, msg.chat.id)
    if not ok:
        await context.bot.send_message(
            chat_id=msg.chat.id,
            text="Sorry, this bot is not accepting more users (>5).",
            reply_parameters=ReplyParameters(message_id=msg.message_id),
        )
        return

    # Parse "amount category"
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

    # Non-expense → show menu
    await context.bot.send_message(
        chat_id=msg.chat.id,
        text=MENU,
        reply_parameters=ReplyParameters(message_id=msg.message_id),
    )
