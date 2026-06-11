"""Tools exclusive to the conversational CommsAgent (Telegram).

These let the comms LLM initiate, cancel, and query projects on behalf of the
user. The LLM decides which tool to call instead of a hand-written state machine.

NOTE: CrewAI runs tools in a ThreadPoolExecutor — there is no asyncio event
loop in those threads. All coroutine scheduling goes through
`runtime.schedule(coro)` which uses run_coroutine_threadsafe() against the
main loop stored at bot startup.
"""
from __future__ import annotations
import json
from crewai.tools import tool
from crew.runtime import get_runtime


@tool("start_project")
def start_project(description: str, budget_usd: float = 0.5) -> str:
    """Kick off a new Flutter project generation.

    Args:
        description: what the user wants the app to do (free-form Spanish/English).
        budget_usd: max USD to spend on LLM calls (default 0.5).

    Returns confirmation JSON. The Flow runs in the background; progress is
    delivered via `notify_user`.
    """
    runtime = get_runtime()
    if runtime.state is not None and runtime.state.phase not in ("idle", "done", "failed"):
        return json.dumps({"success": False, "error": f"Ya hay un proyecto en curso (fase={runtime.state.phase})"})
    try:
        # Build a fresh Flow for each project — CrewAI Flow instances are not reusable.
        from crew.flow import LegionOmegaFlow
        runtime.flow = LegionOmegaFlow()
        runtime.schedule(runtime.flow.kickoff_async(inputs={
            "description": description,
            "budget_usd": float(budget_usd),
        }))
        return json.dumps({"success": True, "message": "Proyecto iniciado", "budget_usd": float(budget_usd)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool("cancel_project")
def cancel_project() -> str:
    """Request cancellation of the active project (best-effort)."""
    runtime = get_runtime()
    if runtime.state is None:
        return json.dumps({"success": False, "error": "No hay proyecto activo"})
    runtime.state.phase = "failed"
    runtime.state.log("failed", "Cancelled by user", level="warn")
    return json.dumps({"success": True})


@tool("notify_user")
def notify_user(message: str) -> str:
    """Send a free-form message directly to the user over Telegram."""
    runtime = get_runtime()
    if runtime.notify is None:
        return json.dumps({"success": False, "error": "Notify channel not wired"})
    try:
        runtime.schedule(runtime.notify(message))
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
