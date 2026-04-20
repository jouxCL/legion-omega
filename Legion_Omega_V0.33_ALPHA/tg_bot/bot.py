import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
    ContextTypes,
)
from memory.memory_manager import MemoryManager
from agents.context_agent import ContextAgent
from orchestrator.orchestrator_agent import OrchestratorAgent
from tg_bot.handlers import (
    setup_handlers,
    cmd_start, cmd_nuevo, cmd_estado, cmd_budget, cmd_cancelar,
    handle_message, handle_document, error_handler,
)

logger = logging.getLogger(__name__)


def build_application() -> Application:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    memory = MemoryManager()
    orchestrator = OrchestratorAgent()
    context_agent = ContextAgent(memory)
    setup_handlers(orchestrator, memory, context_agent)

    app = Application.builder().token(token).build()

    # Log every incoming update (group -1 runs before all handlers)
    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message:
            user_id = update.effective_user.id if update.effective_user else "?"
            text = update.message.text[:60] if update.message.text else "[doc/media]"
            logger.info(f"[UPDATE] user={user_id} → {text}")

    app.add_handler(TypeHandler(Update, log_update), group=-1)

    # Commands
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("nuevo",   cmd_nuevo))
    app.add_handler(CommandHandler("estado",  cmd_estado))
    app.add_handler(CommandHandler("budget",  cmd_budget))
    app.add_handler(CommandHandler("cancelar",cmd_cancelar))

    # Text messages — single handler, state managed inside handle_message
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Documents (ZIP files)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.add_error_handler(error_handler)
    logger.info("Bot configured.")
    return app


def run_bot():
    app = build_application()
    logger.info("Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
