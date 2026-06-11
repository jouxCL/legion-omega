"""Thin Telegram bot: every message is routed to the CommsAgent.

No hand-written state machine — the LLM decides what tool to call.

Lifecycle (python-telegram-bot 21+):
  post_init  → loop already running, NO messages yet → wire main_loop + notify here
  start()    → polling begins, messages can arrive
  post_start → tasks that need the app fully started (narrator loop)
"""
from __future__ import annotations
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters,
)
from config.settings import get_settings
from crew.runtime import get_runtime
from tg_bot.comms_bridge import handle_user_message, event_narrator_loop

logger = logging.getLogger(__name__)


def _authorized(update: Update, allowed_id: int) -> bool:
    user = update.effective_user
    return user is not None and user.id == allowed_id


async def _on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    if not _authorized(update, settings.TELEGRAM_ALLOWED_USER_ID):
        return
    reply = await handle_user_message(update.effective_chat.id, "/start")
    await update.message.reply_text(reply)


async def _on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    if not _authorized(update, settings.TELEGRAM_ALLOWED_USER_ID):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    await ctx.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = await handle_user_message(update.effective_chat.id, text)
    await update.message.reply_text(reply)


def build_application() -> Application:
    settings = get_settings()
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", _on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_text))
    return app


async def _post_init(app: Application) -> None:
    """Called BEFORE polling starts — safe place to wire the main_loop and notify."""
    settings = get_settings()
    runtime = get_runtime()

    # Store the running loop NOW, before any message can arrive.
    runtime.main_loop = asyncio.get_running_loop()

    async def _send(msg: str) -> None:
        try:
            await app.bot.send_message(chat_id=settings.TELEGRAM_ALLOWED_USER_ID, text=msg)
        except Exception:
            logger.exception("send_message failed")

    runtime.notify = _send
    logger.info("Runtime wired: main_loop set, notify ready")


async def _post_start(app: Application) -> None:
    """Called AFTER polling starts — safe to create long-running asyncio tasks."""
    asyncio.create_task(event_narrator_loop(get_runtime().notify))
    logger.info("Event narrator loop started")


def run_bot() -> None:
    app = build_application()
    app.post_init = _post_init
    app.post_start = _post_start
    logger.info("Starting Telegram bot (V0.4 CREWAI)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
