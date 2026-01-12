from telegram import ReplyParameters
from telegram.ext import ContextTypes
from telegram import Update

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or "").strip()

    # For Step 1, we simply acknowledge and show the menu.
    # IMPORTANT: Tag the message we're replying to (your requirement #11).
    await context.bot.send_message(
        chat_id=msg.chat.id,
        text=f"Received: {text}\n\n{MENU}",
        reply_parameters=ReplyParameters(message_id=msg.message_id),
    )

