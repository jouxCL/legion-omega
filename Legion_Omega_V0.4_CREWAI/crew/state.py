"""Shared state for LegionOmegaFlow.

`ProjectState` is the Flow state (Pydantic); `PhaseEvent` is a log entry the
CommsAgent reads to narrate progress to the user.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

Phase = Literal["idle", "init", "plan", "build", "compile", "fix", "finalize", "done", "failed"]


class PhaseEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    phase: Phase
    level: Literal["info", "warn", "error", "success"] = "info"
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class FeaturePlan(BaseModel):
    name: str
    description: str
    entities: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    screens: list[str] = Field(default_factory=list)


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
