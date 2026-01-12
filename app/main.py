import os
import logging
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.requests import Request
from starlette.routing import Route
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from app.handlers import handle_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render provides the external URL for webhook
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Build PTB Application (async)
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def set_webhook():
    # Telegram requires HTTPS webhook URL
    url = f"{RENDER_URL}{WEBHOOK_PATH}"
    logger.info(f"Setting webhook to {url}")
    await application.bot.set_webhook(url)

async def on_startup():
    await set_webhook()

async def on_shutdown():
    await application.bot.delete_webhook()

# Endpoints
async def health(_: Request):
    return PlainTextResponse("OK")  # used by Render health checks & UptimeRobot pings

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

