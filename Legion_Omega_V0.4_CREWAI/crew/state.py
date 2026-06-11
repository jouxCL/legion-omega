"""Shared state for LegionOmegaFlow.

`ProjectState` is the Flow state (Pydantic); `PhaseEvent` is a log entry the
CommsAgent reads to narrate progress to the user.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator

Phase = Literal["idle", "init", "plan", "build", "compile", "fix", "finalize", "done", "failed"]


def _to_name_list(value: Any) -> list[str]:
    """Coerce a list that may contain strings or dicts with 'name' into list[str].

    Gemini planner tends to return richer dicts like {name, properties} — accept them.
    """
    if value is None:
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(str(item.get("name") or item.get("id") or next(iter(item.values()), "item")))
        else:
            out.append(str(item))
    return out


class PhaseEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    phase: Phase
    level: Literal["info", "warn", "error", "success"] = "info"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class FeaturePlan(BaseModel):
    name: str
    description: str = ""
    entities: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    screens: list[str] = Field(default_factory=list)

    @field_validator("entities", "use_cases", "screens", mode="before")
    @classmethod
    def _coerce_strings(cls, v):
        return _to_name_list(v)


class ProjectPlan(BaseModel):
    app_name: str
    app_display_name: str
    features: list[FeaturePlan] = Field(default_factory=list)
    global_theme: dict[str, Any] = Field(default_factory=dict)
    navigation_routes: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    description: str = ""
    budget_usd: float = 0.5
    budget_remaining_usd: float = 0.5
    brand_zip_path: Optional[str] = None
    app_name: Optional[str] = None

    phase: Phase = "idle"
    plan: Optional[ProjectPlan] = None
    project_path: Optional[str] = None

    compile_attempts: int = 0
    max_compile_attempts: int = 3
    last_errors: list[str] = Field(default_factory=list)

    events: list[PhaseEvent] = Field(default_factory=list)

    def log(self, phase: Phase, message: str, *, level: str = "info", **data: Any) -> PhaseEvent:
        evt = PhaseEvent(phase=phase, level=level, message=message, data=data)
        self.events.append(evt)
        return evt
