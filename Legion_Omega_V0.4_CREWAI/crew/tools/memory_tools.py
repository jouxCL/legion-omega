"""Memory / persistent-state tools for CrewAI agents."""
from __future__ import annotations
import json
import os
from crewai.tools import tool
from crew.runtime import get_runtime


@tool("get_project_status")
def get_project_status() -> str:
    """Return a JSON snapshot of the current project's phase, plan summary, budget and last events."""
    runtime = get_runtime()
    state = runtime.state
    if state is None:
        return json.dumps({"phase": "idle", "message": "No project running"})
    plan = state.plan.model_dump() if state.plan else None
    return json.dumps({
        "phase": state.phase,
        "app_name": state.app_name or (plan.get("app_name") if plan else None),
        "description": state.description,
        "budget_usd": state.budget_usd,
        "budget_remaining_usd": state.budget_remaining_usd,
        "project_path": state.project_path,
        "compile_attempts": state.compile_attempts,
        "last_errors": state.last_errors[-5:],
        "plan_summary": {
            "features": [f["name"] for f in plan["features"]] if plan else [],
        } if plan else None,
    })


@tool("get_last_events")
def get_last_events(limit: int = 10) -> str:
    """Return the last N PhaseEvents from the active Flow, as JSON."""
    runtime = get_runtime()
    if runtime.state is None:
        return json.dumps([])
    n = max(1, min(int(limit), 50))
    return json.dumps([e.model_dump() for e in runtime.state.events[-n:]])


@tool("list_artifacts")
def list_artifacts() -> str:
    """List generated files under the active Flutter project's lib/ directory."""
    runtime = get_runtime()
    if runtime.state is None or not runtime.state.project_path:
        return json.dumps([])
    lib_dir = os.path.join(runtime.state.project_path, "lib")
    out: list[str] = []
    if os.path.isdir(lib_dir):
        for root, _, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".dart"):
                    out.append(os.path.relpath(os.path.join(root, f), runtime.state.project_path))
    return json.dumps(out[:200])
