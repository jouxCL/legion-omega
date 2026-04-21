"""LegionOmegaFlow — CrewAI Flow that orchestrates the full pipeline.

Phases: init → plan → build → compile → (fix → compile loop) → finalize.
Each phase spins up a minimal Crew, mutates the shared ProjectState, and
appends a PhaseEvent so the CommsAgent can narrate progress.
"""
from __future__ import annotations
import asyncio
import json
import logging
import re
from typing import Any, Optional
from crewai import Crew, Process
from crewai.flow.flow import Flow, start, listen, router

from crew.state import ProjectState, ProjectPlan
from crew.agents import (
    build_planner, build_logic_agent, build_ui_agent,
    build_compiler_ops, build_fixer,
)
from crew.tasks import (
    plan_task, feature_logic_task, feature_ui_task, compile_task, fix_task,
)
from crew.runtime import get_runtime

logger = logging.getLogger(__name__)


def _parse_plan_json(raw: str) -> dict[str, Any]:
    text = str(raw).strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        text = text[a:b + 1]
    return json.loads(text)


class LegionOmegaFlow(Flow[ProjectState]):

    @start()
    def init_project(self) -> None:
        # Inputs arrive via kickoff(inputs=...); CrewAI merges them into self.state.
        self.state.phase = "init"
        self.state.budget_remaining_usd = self.state.budget_usd
        self.state.app_name = self.state.app_name or self._slugify(self.state.description[:30])
        self.state.log("init", f"Proyecto iniciado: {self.state.app_name}", level="info",
                       budget=self.state.budget_usd)
        get_runtime().publish_event({"phase": "init", "app_name": self.state.app_name})

    @listen(init_project)
    async def plan_project(self) -> None:
        self.state.phase = "plan"
        self.state.log("plan", "Analizando tu solicitud…", level="info")
        get_runtime().publish_event({"phase": "plan"})

        planner = build_planner()
        task = plan_task(planner)
        crew = Crew(agents=[planner], tasks=[task], process=Process.sequential, verbose=True)
        result = await crew.kickoff_async(inputs={
            "description": self.state.description,
            "budget_usd": self.state.budget_usd,
        })
        try:
            plan_dict = _parse_plan_json(result.raw)
            self.state.plan = ProjectPlan.model_validate(plan_dict)
            self.state.app_name = self.state.plan.app_name
            self.state.log("plan", f"Plan generado: {len(self.state.plan.features)} features",
                           level="success", features=[f.name for f in self.state.plan.features])
        except Exception as e:
            logger.exception("Plan parsing failed")
            self.state.log("plan", f"Fallo parseando plan: {e}", level="error")
            self.state.phase = "failed"

    @listen(plan_project)
    async def build_project(self) -> None:
        if self.state.phase == "failed" or self.state.plan is None:
            return
        self.state.phase = "build"
        self.state.log("build", "Creando proyecto Flutter y generando código…")
        get_runtime().publish_event({"phase": "build"})

        from flutter_builder.project_initializer import ProjectInitializer
        settings_output_dir = get_runtime().memory.get_memory().get("project", {}).get(
            "output_dir") if get_runtime().memory else "./output"
        initializer = ProjectInitializer(settings_output_dir or "./output")
        self.state.project_path = await initializer.create(self.state.plan.app_name)
        self.state.log("build", f"Scaffold listo en {self.state.project_path}", level="success")

        feature_names = [f.name for f in self.state.plan.features]
        await asyncio.gather(*(self._build_feature(name) for name in feature_names))
        self.state.log("build", f"Generación de {len(feature_names)} features finalizada",
                       level="success")

    async def _build_feature(self, feature_name: str) -> None:
        logic = build_logic_agent()
        ui = build_ui_agent()
        tasks = [feature_logic_task(logic, feature_name), feature_ui_task(ui, feature_name)]
        crew = Crew(agents=[logic, ui], tasks=tasks, process=Process.sequential, verbose=True)
        try:
            await crew.kickoff_async(inputs={"feature": feature_name})
            self.state.log("build", f"Feature '{feature_name}' lista", level="success")
        except Exception as e:
            self.state.log("build", f"Feature '{feature_name}' falló: {e}", level="error")

    @listen(build_project)
    async def compile_project(self) -> None:
        if self.state.phase == "failed":
            return
        self.state.phase = "compile"
        self.state.compile_attempts += 1
        self.state.log("compile", f"Compilando (intento {self.state.compile_attempts})…")
        get_runtime().publish_event({"phase": "compile", "attempt": self.state.compile_attempts})

        compiler_ops = build_compiler_ops()
        crew = Crew(agents=[compiler_ops], tasks=[compile_task(compiler_ops)],
                    process=Process.sequential, verbose=True)
        result = await crew.kickoff_async(inputs={})
        try:
            data = _parse_plan_json(result.raw) if "{" in str(result.raw) else {"success": False}
        except Exception:
            data = {"success": False, "errors": [{"message": str(result.raw)[:400]}]}
        if data.get("success"):
            self.state.log("compile", "Compilación OK", level="success")
            self.state.last_errors = []
        else:
            errs = data.get("errors", []) or []
            self.state.last_errors = [e.get("message", str(e)) if isinstance(e, dict) else str(e)
                                      for e in errs][:20]
            self.state.log("compile", f"Errores: {len(self.state.last_errors)}", level="warn")

    @router(compile_project)
    def decide_after_compile(self) -> str:
        if not self.state.last_errors:
            return "finalize"
        if self.state.compile_attempts >= self.state.max_compile_attempts:
            return "give_up"
        return "fix"

    @listen("fix")
    async def fix_errors(self) -> None:
        self.state.phase = "fix"
        self.state.log("fix", f"Intentando corregir {len(self.state.last_errors)} error(es)…")
        get_runtime().publish_event({"phase": "fix"})
        fixer = build_fixer()
        crew = Crew(agents=[fixer], tasks=[fix_task(fixer)], process=Process.sequential, verbose=True)
        await crew.kickoff_async(inputs={"errors": "\n".join(self.state.last_errors)})
        # Loop back into compile
        await self.compile_project()

    @listen("give_up")
    def mark_failed(self) -> None:
        self.state.phase = "failed"
        self.state.log("failed", "Se agotaron los intentos de compilación", level="error")
        get_runtime().publish_event({"phase": "failed"})

    @listen("finalize")
    def finalize(self) -> None:
        self.state.phase = "done"
        self.state.log("done", "Proyecto completado", level="success",
                       path=self.state.project_path)
        get_runtime().publish_event({"phase": "done", "path": self.state.project_path})

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s]", "", text.lower())
        slug = re.sub(r"\s+", "_", slug.strip())
        return slug or "legion_app"
