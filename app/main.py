# app/main.py
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
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")  # Render injects this
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Build PTB application (async)
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def set_webhook():
    url = f"{RENDER_URL}{WEBHOOK_PATH}"
    logger.info(f"Setting webhook to {url}")
    await application.bot.set_webhook(url)

async def on_startup():
    # IMPORTANT: initialize and start the PTB application
    await application.initialize()
    await application.start()
    await set_webhook()

async def on_shutdown():
    # IMPORTANT: stop & shutdown
    await application.stop()
    await application.shutdown()

# Health endpoint for Render + UptimeRobot
async def health(_: Request):
    return PlainTextResponse("OK")

# Telegram posts updates here
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    # process_update is safe now that initialize/start ran
    await application.process_update(update)
    return JSONResponse({"status": "processed"})

routes = [
    Route("/", endpoint=health, methods=["GET"]),
    Route("/health", endpoint=health, methods=["GET"]),
    Route(WEBHOOK_PATH, endpoint=webhook, methods=["POST"]),
]

app = Starlette(routes=routes, on_startup=[on_startup], on_shutdown=[on_shutdown])
