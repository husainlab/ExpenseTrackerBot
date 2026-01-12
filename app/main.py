import os
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo
from app.handlers import handle_message
from app.scheduler import send_weekly_summaries, send_monthly_insights

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

app_tg = Application.builder().token(BOT_TOKEN).build()
app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Kolkata"))

async def startup():
    await app_tg.initialize()
    await app_tg.start()
    await app_tg.bot.set_webhook(f"{RENDER_URL}{WEBHOOK_PATH}")

    scheduler.add_job(send_weekly_summaries, "cron", day_of_week="sun", hour=23, minute=59, args=[app_tg], id="weekly")
    scheduler.add_job(send_monthly_insights, "cron", day=28, hour=23, minute=59, args=[app_tg], id="monthly", replace_existing=True)
    scheduler.start()

async def shutdown():
    scheduler.shutdown(wait=False)
    await app_tg.stop()
    await app_tg.shutdown()

async def health(_):
    return PlainTextResponse("OK")

async def webhook(request):
    data = await request.json()
    await app_tg.process_update(Update.de_json(data, app_tg.bot))
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
