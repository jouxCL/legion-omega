"""Bridge between python-telegram-bot and the CommsAgent Crew.

Each Telegram message is converted into a one-task Crew.kickoff_async run
against the CommsAgent. Per-chat conversation history is kept in a simple
in-memory dict so the LLM can be multi-turn.

A background worker also consumes `runtime.event_queue` (pushed by the
LegionOmegaFlow) and asks the CommsAgent to narrate each event to the user.
"""
from __future__ import annotations
import asyncio
import json
import logging
from collections import defaultdict, deque
from typing import Deque
from crewai import Crew, Process
from crew.agents import build_comms
from crew.tasks import comms_task
from crew.runtime import get_runtime
from crew.tools.memory_tools import get_project_status

logger = logging.getLogger(__name__)

_HISTORY: dict[int, Deque[dict]] = defaultdict(lambda: deque(maxlen=12))


def _history_for(chat_id: int) -> list[dict]:
    return list(_HISTORY[chat_id])


async def handle_user_message(chat_id: int, text: str) -> str:
    """Run CommsAgent against a user message; return the text to send back."""
    comms = build_comms()
    task = comms_task(comms)
    crew = Crew(agents=[comms], tasks=[task], process=Process.sequential, verbose=False)
    try:
        status_raw = get_project_status.func() if hasattr(get_project_status, "func") else get_project_status()
    except Exception:
        status_raw = "{}"
    try:
        result = await crew.kickoff_async(inputs={
            "user_message": text,
            "history": json.dumps(_history_for(chat_id), ensure_ascii=False)[-2000:],
            "status": status_raw,
        })
        reply = str(result.raw).strip() or "…"
    except Exception as e:
        logger.exception("CommsAgent failed")
        reply = f"(Comms se trabó: {e})"
    _HISTORY[chat_id].append({"user": text, "ai": reply})
    return reply


async def event_narrator_loop(send_to_user):
    """Consume runtime.event_queue, let CommsAgent narrate each event, deliver via send_to_user."""
    runtime = get_runtime()
    phase_messages = {
        "init": "🚀 *Iniciando proyecto:* {app_name}",
        "plan": "📋 *Fase de planificación:* Generando arquitectura y features…",
        "build": "🛠️ *Fase de construcción:* Generando código Flutter…",
        "compile": "⚙️ *Compilando proyecto...* (Intento {attempt})",
        "fix": "🔧 *Corrigiendo errores de compilación...*",
        "done": "✅ *¡Proyecto completado con éxito!* Ubicación: {path}",
        "failed": "❌ *El proyecto ha fallado o se detuvo.*",
    }
    while True:
        evt = await runtime.event_queue.get()
        try:
            phase = evt.get("phase")
            if phase in phase_messages:
                fmt_msg = phase_messages[phase].format(**evt)
                await send_to_user(fmt_msg)
            else:
                await send_to_user(f"📢 Evento: {evt}")
        except Exception:
            logger.exception("Event narration failed")
