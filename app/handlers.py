import re
from datetime import timedelta
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyParameters,
)
from telegram.ext import ContextTypes
from app.storage_git import (
    ensure_user_dir,
    write_expense,
    delete_user_data,
    git_commit_push,
    load_config,
)
from app.reports import load_expenses_between, summarize_by_category
from app.utils_time import now_ist, week_bounds, month_bounds

# -----------------------------
# Menu UI
# -----------------------------

MENU_TEXT = """👋 *Welcome to Expense Tracker Bot*

What would you like to do?

💸 *Expenses*
• This week
• Last week
• This month
• Last month
• Today
• Yesterday

📊 *Analysis*
• Budget status
• Category breakdown (this month)
• Export this month

🧠 *Insights*
• Monthly insights
• AI insights (coming soon)

⚙️ *Account*
• Delete all my data
• Help

━━━━━━━━━━━━━━
✍️ *Add an expense anytime*:
`200 food lunch`

⬇️ *Tap a button below*
"""

def build_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("This week", callback_data="WEEK_THIS"),
            InlineKeyboardButton("Last week", callback_data="WEEK_LAST"),
        ],
        [
            InlineKeyboardButton("This month", callback_data="MONTH_THIS"),
            InlineKeyboardButton("Last month", callback_data="MONTH_LAST"),
        ],
        [
            InlineKeyboardButton("Today", callback_data="DAY_TODAY"),
            InlineKeyboardButton("Yesterday", callback_data="DAY_YESTERDAY"),
        ],
        [
            InlineKeyboardButton("Budget status", callback_data="BUDGET_STATUS"),
        ],
        [
            InlineKeyboardButton("Categories (month)", callback_data="CATEGORIES_MONTH"),
        ],
        [
            InlineKeyboardButton("Export this month", callback_data="EXPORT_MONTH"),
        ],
        [
            InlineKeyboardButton("Monthly insights", callback_data="INSIGHT_MONTH"),
            InlineKeyboardButton("AI insights", callback_data="INSIGHT_AI"),
        ],
        [
            InlineKeyboardButton("Delete my data", callback_data="DELETE_INIT"),
            InlineKeyboardButton("Help", callback_data="HELP"),
        ],
    ])

def build_delete_confirm_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Cancel", callback_data="DELETE_CANCEL"),
            InlineKeyboardButton("✅ CONFIRM DELETE", callback_data="DELETE_CONFIRM"),
        ]
    ])

# -----------------------------
# Parsing
# -----------------------------

EXPENSE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s+(\w+)(?:\s+(.*))?$")

# -----------------------------
# Helpers
# -----------------------------

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=MENU_TEXT,
        parse_mode="Markdown",
        reply_markup=build_menu_keyboard(),
    )

# -----------------------------
# Callback handler
# -----------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = str(user.id)
    chat_id = update.effective_chat.id
    now = now_ist()

    # 🔑 CRITICAL: ensure user context for button taps
    ok = ensure_user_dir(user_id, chat_id, user.username or "")
    if not ok:
        await context.bot.send_message(chat_id=chat_id, text="User limit reached.")
        return

    try:
        if query.data == "HELP":
            await send_menu(update, context)
            return

        if query.data == "DELETE_INIT":
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ *This will permanently delete all your data.*\nAre you sure?",
                parse_mode="Markdown",
                reply_markup=build_delete_confirm_keyboard(),
            )
            return

        if query.data == "DELETE_CANCEL":
            await send_menu(update, context)
            return

        if query.data == "DELETE_CONFIRM":
            delete_user_data(user_id)
            git_commit_push(f"Delete data for {user_id}")
            await context.bot.send_message(chat_id=chat_id, text="✅ Your data has been deleted.")
            await send_menu(update, context)
            return

        # ---- Time-based queries ----
        if query.data == "WEEK_THIS":
            start, end = week_bounds(now)
        elif query.data == "WEEK_LAST":
            start, end = week_bounds(now - timedelta(days=7))
        elif query.data == "MONTH_THIS":
            start, end = month_bounds(now)
        elif query.data == "MONTH_LAST":
            prev = now.replace(day=1) - timedelta(days=1)
            start, end = month_bounds(prev)
        elif query.data == "DAY_TODAY":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif query.data == "DAY_YESTERDAY":
            y = now - timedelta(days=1)
            start = y.replace(hour=0, minute=0, second=0, microsecond=0)
            end = y.replace(hour=23, minute=59, second=59)
        else:
            await context.bot.send_message(chat_id=chat_id, text="ℹ️ Feature coming soon.")
            return

        df = load_expenses_between(user_id, start, end)
        text = (
            f"*Summary*\n"
            f"{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}\n\n"
            f"{summarize_by_category(df)}"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
        )

    except Exception as e:
        # 🔍 NEVER fail silently on callbacks
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Something went wrong while processing your request.",
        )
        raise


# -----------------------------
# Text handler (fallback)
# -----------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.strip()
    user = msg.from_user
    user_id = str(user.id)

    if not ensure_user_dir(user_id, msg.chat.id, user.username or ""):
        await msg.reply_text("Sorry, this bot is not accepting more users right now.")
        return

    # Expense entry
    m = EXPENSE_RE.match(text)
    if m:
        amount = float(m.group(1))
        category = m.group(2).lower()
        note = m.group(3) or ""
        write_expense(user_id, amount, category, note)
        git_commit_push("Add expense")
        await msg.reply_text(f"✅ Saved ₹{amount:.2f} in *{category}*", parse_mode="Markdown")
        return

    # Menu triggers
    if text.lower() in {"hi", "hello", "start", "/start", "menu"}:
        await send_menu(update, context)
        return

    # Fallback
    await send_menu(update, context)
