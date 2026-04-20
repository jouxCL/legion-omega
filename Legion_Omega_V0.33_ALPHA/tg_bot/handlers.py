import os
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Conflict
from orchestrator.orchestrator_agent import OrchestratorAgent
from memory.memory_manager import MemoryManager
from agents.context_agent import ContextAgent
from orchestrator.budget_manager import get_budget_report

logger = logging.getLogger(__name__)

# ── Manual state machine (same approach as V2) ──────────────────────────────
# Stored in context.user_data["state"]
S_IDLE           = "idle"
S_WAITING_DESC   = "waiting_desc"    # used by /nuevo guided flow
S_WAITING_ZIP    = "waiting_zip"
S_WAITING_BUDGET = "waiting_budget"
S_WAITING_CONFIRM= "waiting_confirm"
S_ACTIVE         = "active"

# Global orchestrator instances (set by bot.py via setup_handlers)
_orchestrator: OrchestratorAgent = None
_memory: MemoryManager = None
_context_agent: ContextAgent = None
_active_task: asyncio.Task = None


def setup_handlers(orchestrator: OrchestratorAgent,
                   memory: MemoryManager,
                   context_agent: ContextAgent):
    global _orchestrator, _memory, _context_agent
    _orchestrator = orchestrator
    _memory = memory
    _context_agent = context_agent


def _get_state(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("state", S_IDLE)


def _set_state(context: ContextTypes.DEFAULT_TYPE, state: str):
    context.user_data["state"] = state
    logger.info(f"[STATE] → {state}")


# ── /start ───────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _set_state(context, S_IDLE)
    await update.message.reply_text(
        "👋 ¡Hola! Soy *LEGION OMEGA*, tu asistente para crear apps Flutter.\n\n"
        "🚀 *Para empezar:* Describe tu app directamente, incluye el presupuesto.\n"
        "_Ejemplo: Quiero una app de Pomodoro. Presupuesto $1.50_\n\n"
        "📋 *Comandos:*\n"
        "• /nuevo — Flujo guiado paso a paso\n"
        "• /estado — Estado del proyecto actual\n"
        "• /budget — Reporte de presupuesto\n"
        "• /cancelar — Cancelar el proyecto activo",
        parse_mode="Markdown"
    )


# ── /nuevo (guided flow) ─────────────────────────────────────────────────────

async def cmd_nuevo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _set_state(context, S_WAITING_DESC)
    await update.message.reply_text(
        "✏️ *Nuevo proyecto*\n\n"
        "Describe la app que quieres crear.\n"
        "¿Para quién es? ¿Qué hace? ¿Qué problemas resuelve?",
        parse_mode="Markdown"
    )


# ── /estado ──────────────────────────────────────────────────────────────────

async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = _orchestrator.get_status()
    await update.message.reply_text(status, parse_mode="Markdown")


# ── /budget ──────────────────────────────────────────────────────────────────

async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mem = _memory.get_memory()
    report = get_budget_report(mem)
    await update.message.reply_text(report, parse_mode="Markdown")


# ── /cancelar ────────────────────────────────────────────────────────────────

async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_task
    if _active_task and not _active_task.done():
        _active_task.cancel()
        _memory.update_memory("project.status", "cancelled")
        await update.message.reply_text("🛑 Proyecto cancelado.")
    else:
        await update.message.reply_text("No hay ningún proyecto activo.")
    _set_state(context, S_IDLE)


# ── Main text handler (single entry point for all text messages) ──────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Single handler for all text messages.
    Routes based on context.user_data["state"] — same pattern as V2.
    """
    global _active_task
    text = (update.message.text or "").strip()
    state = _get_state(context)
    user_id = update.effective_user.id if update.effective_user else "unknown"
    logger.info(f"[MSG] user={user_id} state={state} text='{text[:60]}'")

    # ── Guided flow: waiting for description ────────────────────────────────
    if state == S_WAITING_DESC:
        context.user_data["description"] = text
        context.user_data["zip_path"] = None
        _set_state(context, S_WAITING_ZIP)
        await update.message.reply_text(
            "📦 ¿Tienes archivos de marca (logo, colores, fuentes)?\n\n"
            "Envía un archivo *.zip* o escribe *no* para continuar.",
            parse_mode="Markdown"
        )
        return

    # ── Waiting for budget ───────────────────────────────────────────────────
    if state == S_WAITING_BUDGET:
        try:
            budget = float(text.replace(",", "."))
            if budget <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ Escribe solo un número positivo. Ejemplo: *1.5*",
                parse_mode="Markdown"
            )
            return
        context.user_data["budget"] = budget
        description = context.user_data.get("description", "")
        has_zip = bool(context.user_data.get("zip_path"))
        _set_state(context, S_WAITING_CONFIRM)
        await update.message.reply_text(
            f"📋 *Resumen del proyecto*\n\n"
            f"*Descripción:* {description[:200]}\n"
            f"*Presupuesto:* ${budget:.2f} USD\n"
            f"*Assets de marca:* {'Sí ✅' if has_zip else 'No'}\n\n"
            "¿Empezamos? Responde *SI* o *NO*.",
            parse_mode="Markdown"
        )
        return

    # ── Waiting for confirmation ─────────────────────────────────────────────
    if state == S_WAITING_CONFIRM:
        if text.upper() in ("SI", "SÍ", "YES", "S", "Y"):
            await _launch_project(update, context)
        else:
            _set_state(context, S_IDLE)
            await update.message.reply_text(
                "❌ Proyecto cancelado. Describe otra app cuando quieras."
            )
        return

    # ── Project running — forward messages to orchestrator ──────────────────
    if state == S_ACTIVE:
        await _orchestrator.handle_user_response(text)
        mem = _memory.get_memory()
        reply = await _context_agent.handle_user_message(text, mem)
        await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # ── IDLE / default: treat the message as the project description ─────────
    # (V2-style: user just describes the app without any command)
    context.user_data["description"] = text
    context.user_data["zip_path"] = None
    _set_state(context, S_WAITING_BUDGET)
    await update.message.reply_text(
        "💰 *¿Cuál es tu presupuesto máximo en dólares?*\n\n"
        "Para una app simple recomiendo entre *$0.50 y $2.00*.\n"
        "Escribe solo el número (ejemplo: *1.5*)",
        parse_mode="Markdown"
    )


# ── Document handler (ZIP files) ─────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = _get_state(context)
    if state != S_WAITING_ZIP:
        await update.message.reply_text(
            "Primero describe tu app para que pueda procesar el ZIP. 🙂"
        )
        return

    doc = update.message.document
    if not doc.file_name.endswith(".zip"):
        await update.message.reply_text(
            "⚠️ Solo acepto archivos *.zip*. Envía un .zip o escribe *no*.",
            parse_mode="Markdown"
        )
        return

    output_dir = os.path.join(os.getenv("OUTPUT_DIR", "./output"), "brand_zips")
    os.makedirs(output_dir, exist_ok=True)
    zip_path = os.path.join(output_dir, doc.file_name)
    file = await doc.get_file()
    await file.download_to_drive(zip_path)
    context.user_data["zip_path"] = zip_path

    _set_state(context, S_WAITING_BUDGET)
    await update.message.reply_text(
        "✅ ZIP recibido.\n\n"
        "💰 *¿Cuál es tu presupuesto máximo en dólares?*\n"
        "Ejemplo: *1.5*",
        parse_mode="Markdown"
    )


# ── Internal: launch the project ─────────────────────────────────────────────

async def _launch_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _active_task
    description = context.user_data.get("description", "")
    budget      = context.user_data.get("budget", 0.5)
    zip_path    = context.user_data.get("zip_path")

    _set_state(context, S_ACTIVE)
    await update.message.reply_text(
        "🚀 *¡Arrancamos!* Construyendo tu app...\n"
        "Te mantendré informado del progreso. Esto puede tomar varios minutos.",
        parse_mode="Markdown"
    )

    async def notify(msg: str):
        try:
            # Try Markdown first; fall back to plain text on parse errors
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            try:
                # Strip markdown symbols and send as plain text
                plain = msg.replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")
                await update.message.reply_text(plain)
            except Exception as e2:
                logger.warning(f"notify failed entirely: {e2}")

    _orchestrator.notify = notify
    _active_task = asyncio.create_task(
        _orchestrator.start_project(description, budget, zip_path)
    )


# ── Error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, Conflict):
        logger.error(
            "Telegram Conflict: otra instancia del bot está corriendo. "
            "Asegúrate de que solo un proceso 'python main.py' esté activo."
        )
        raise context.error
    logger.error(f"Telegram error: {context.error}", exc_info=context.error)
