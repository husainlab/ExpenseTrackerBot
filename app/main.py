import os
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

from app.handlers import handle_message, handle_callback
from app.scheduler import send_weekly_summaries, send_monthly_insights

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

tg_app = Application.builder().token(BOT_TOKEN).build()
tg_app.add_handler(CallbackQueryHandler(handle_callback))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Kolkata"))

async def startup():
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(f"{RENDER_URL}{WEBHOOK_PATH}")
    await tg_app.bot.set_my_commands([]) #remove this line once '/' menu disappears
    scheduler.add_job(
        send_weekly_summaries,
        "cron",
        day_of_week="sun",
        hour=23,
        minute=59,
        args=[tg_app],
        id="weekly",
        replace_existing=True,
    )

    scheduler.add_job(
        send_monthly_insights,
        "cron",
        day=28,
        hour=23,
        minute=59,
        args=[tg_app],
        id="monthly",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()

async def shutdown():
    scheduler.shutdown(wait=False)
    await tg_app.stop()
    await tg_app.shutdown()

async def health(_):
    return PlainTextResponse("OK")

async def webhook(request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return JSONResponse({"ok": True})

app = Starlette(
    routes=[
        Route("/", health),
        Route("/health", health),
        Route(WEBHOOK_PATH, webhook, methods=["POST"]),
    ],
    on_startup=[startup],
    on_shutdown=[shutdown],
)
