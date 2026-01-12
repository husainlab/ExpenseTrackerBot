from datetime import timedelta
from collections import defaultdict

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import ContextTypes

from app.storage_git import (
    ensure_user_dir,
    write_expense,
    delete_user_data,
    git_commit_push,
    load_config,
    save_config,
)
from app.reports import load_expenses_between, summarize_by_category
from app.utils_time import now_ist, week_bounds, month_bounds

# =====================================================
# MENU TEXT
# =====================================================

MENU_TEXT = """👋 *Welcome to Expense Tracker Bot*

Everything here works using *buttons only* 👇

💸 *Expenses*
• Add new expense
• View summaries

📊 *Budgets*
• View budget status
• Set / update budgets

🧠 *Insights*
• Monthly insights
• AI insights (coming soon)

⚙️ *Account*
• Delete all my data
• Help

━━━━━━━━━━━━━━
⬇️ Tap a button below
"""

# =====================================================
# KEYBOARDS
# =====================================================

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add expense", callback_data="ADD_EXPENSE")],
        [
            InlineKeyboardButton("📅 This week", callback_data="WEEK_THIS"),
            InlineKeyboardButton("📆 This month", callback_data="MONTH_THIS"),
        ],
        [InlineKeyboardButton("📊 Budget status", callback_data="BUDGET_STATUS")],
        [InlineKeyboardButton("📈 Monthly insights", callback_data="INSIGHT_MONTH")],
        [
            InlineKeyboardButton("🗑 Delete my data", callback_data="DELETE_INIT"),
            InlineKeyboardButton("❓ Help", callback_data="HELP"),
        ],
    ])

def confirm_delete_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❌ Cancel", callback_data="DELETE_CANCEL"),
            InlineKeyboardButton("✅ CONFIRM DELETE", callback_data="DELETE_CONFIRM"),
        ]
    ])

def expense_amount_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("₹100", callback_data="AMT_100"),
            InlineKeyboardButton("₹200", callback_data="AMT_200"),
            InlineKeyboardButton("₹500", callback_data="AMT_500"),
        ],
        [
            InlineKeyboardButton("₹1000", callback_data="AMT_1000"),
            InlineKeyboardButton("₹2000", callback_data="AMT_2000"),
        ],
        [InlineKeyboardButton("⬅ Back", callback_data="MENU")],
    ])

def expense_category_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍔 Food", callback_data="CAT_food"),
            InlineKeyboardButton("🚕 Travel", callback_data="CAT_travel"),
        ],
        [
            InlineKeyboardButton("🛒 Shopping", callback_data="CAT_shopping"),
            InlineKeyboardButton("🏠 Rent", callback_data="CAT_rent"),
        ],
        [
            InlineKeyboardButton("💡 Bills", callback_data="CAT_bills"),
            InlineKeyboardButton("📦 Other", callback_data="CAT_other"),
        ],
        [InlineKeyboardButton("⬅ Back", callback_data="ADD_EXPENSE")],
    ])

# =====================================================
# IN-MEMORY FLOW STATE
# =====================================================

PENDING_EXPENSE = {}   # user_id → {"amount": float}

# =====================================================
# MENU SENDER
# =====================================================

async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=MENU_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )

# =====================================================
# CALLBACK HANDLER (ONLY ENTRY POINT)
# =====================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = str(user.id)
    chat_id = update.effective_chat.id
    now = now_ist()

    # Ensure user directory ALWAYS
    if not ensure_user_dir(user_id, chat_id, user.username or ""):
        await context.bot.send_message(chat_id, "User limit reached.")
        return

    data = query.data

    # ---------------- MENU ----------------
    if data in {"MENU", "HELP"}:
        await send_menu(update, context)
        return

    # ---------------- DELETE FLOW ----------------
    if data == "DELETE_INIT":
        await context.bot.send_message(
            chat_id,
            "⚠️ *This will permanently delete all your data.*\nAre you sure?",
            parse_mode="Markdown",
            reply_markup=confirm_delete_kb(),
        )
        return

    if data == "DELETE_CANCEL":
        await send_menu(update, context)
        return

    if data == "DELETE_CONFIRM":
        delete_user_data(user_id)
        git_commit_push(f"Delete data for {user_id}")
        await context.bot.send_message(chat_id, "✅ Your data has been deleted.")
        await send_menu(update, context)
        return

    # ---------------- ADD EXPENSE FLOW ----------------
    if data == "ADD_EXPENSE":
        await context.bot.send_message(
            chat_id,
            "💸 *Select amount*",
            parse_mode="Markdown",
            reply_markup=expense_amount_kb(),
        )
        return

    if data.startswith("AMT_"):
        amount = float(data.split("_")[1])
        PENDING_EXPENSE[user_id] = {"amount": amount}

        await context.bot.send_message(
            chat_id,
            f"Amount selected: ₹{amount:.0f}\n\n🏷 *Select category*",
            parse_mode="Markdown",
            reply_markup=expense_category_kb(),
        )
        return

    if data.startswith("CAT_"):
        if user_id not in PENDING_EXPENSE:
            await send_menu(update, context)
            return

        category = data.replace("CAT_", "")
        amount = PENDING_EXPENSE[user_id]["amount"]

        write_expense(user_id, amount, category, "")
        git_commit_push("Add expense")

        del PENDING_EXPENSE[user_id]

        await context.bot.send_message(
            chat_id,
            f"✅ *Expense saved*\n₹{amount:.0f} in *{category}*",
            parse_mode="Markdown",
        )
        await send_menu(update, context)
        return

    # ---------------- SUMMARIES ----------------
    if data == "WEEK_THIS":
        start, end = week_bounds(now)
    elif data == "MONTH_THIS":
        start, end = month_bounds(now)
    else:
        start = end = None

    if start and end:
        df = load_expenses_between(user_id, start, end)
        text = f"*Summary*\n{summarize_by_category(df)}"
        await context.bot.send_message(chat_id, text, parse_mode="Markdown")
        return

    # ---------------- BUDGET STATUS ----------------
    if data == "BUDGET_STATUS":
        cfg = load_config(user_id)
        budgets = cfg.get("budgets", {})

        if not budgets:
            await context.bot.send_message(
                chat_id,
                "📊 No budgets set yet.\n\nBudget setup via buttons coming next.",
            )
            return

        start, end = month_bounds(now)
        df = load_expenses_between(user_id, start, end)

        spent = defaultdict(float)
        for _, r in df.iterrows():
            spent[r["category"]] += float(r["amount"])

        lines = ["📊 *Budget Status*\n"]
        for cat, limit in budgets.items():
            used = spent.get(cat, 0)
            status = "❌ Over" if used > limit else "✅ OK"
            lines.append(f"*{cat}*: ₹{used:.0f} / ₹{limit:.0f} {status}")

        await context.bot.send_message(chat_id, "\n".join(lines), parse_mode="Markdown")
        return

    # ---------------- INSIGHTS ----------------
    if data == "INSIGHT_MONTH":
        await context.bot.send_message(
            chat_id,
            "📈 Monthly insights are automatically sent at month end.",
        )
        return

    # ---------------- FALLBACK ----------------
    await send_menu(update, context)

# =====================================================
# TEXT HANDLER (DISABLED)
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore all text; always show menu
    await send_menu(update, context)
