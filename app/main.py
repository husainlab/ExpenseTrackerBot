
import os
import logging
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.requests import Request
from starlette.routing import Route

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

from app.handlers import handle_message
from app.scheduler import send_weekly_summaries

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env vars from Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render provides your external URL
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Build PTB Application
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# APScheduler (runs in the asyncio event loop)
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Kolkata"))

async def set_webhook():
    """Register HTTPS webhook with Telegram to your public Render URL."""
    url = f"{RENDER_URL}{WEBHOOK_PATH}"
    logger.info(f"Setting webhook to {url}")
    await application.bot.set_webhook(url)

async def on_startup():
    """Startup hook: initialize/start bot, set webhook, start scheduler."""
    await application.initialize()
    await application.start()
    await set_webhook()

    # ---- TEMP: fire every 2 minutes to verify summaries ----
    scheduler.add_job(

    send_weekly_summaries,
    "cron",
    day_of_week="sun",
    hour=21,
    minute=59,
    args=[application],
    id="weekly_summaries",
    replace_existing=True,

    )
    scheduler.start()
    logger.info("Scheduler started (2-minute test job active).")

async def on_shutdown():
    """Shutdown hook: stop scheduler and bot cleanly."""
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass
    await application.stop()
    await application.shutdown()

# Health endpoint (Render & UptimeRobot)
async def health(_: Request):
    return PlainTextResponse("OK")

# Telegram posts updates here
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return JSONResponse({"status": "processed"})

routes = [
    Route("/", endpoint=health, methods=["GET"]),
    Route("/health", endpoint=health, methods=["GET"]),
    Route(WEBHOOK_PATH, endpoint=webhook, methods=["POST"]),
]

app = Starlette(routes=routes, on_startup=[on_startup], on_shutdown=[on_shutdown])
