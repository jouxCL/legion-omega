import json
import logging
from typing import Optional, Callable, Dict, Any
from crewai import Crew, Process
from crews.agents import planner, logic_agent, ui_agent, compiler_agent, fixer_agent, comms_agent
from crews.tasks import (
    plan_project_task, init_flutter_project_task, generate_theme_task,
    generate_router_task, compile_project_task, fix_compile_errors_task,
    report_status_task
)
from memory.memory_manager import MemoryManager
from flutter_builder.project_initializer import ProjectInitializer
from flutter_builder.compiler import FlutterCompiler

logger = logging.getLogger(__name__)


class LegionOmegaCrew:
    """
    Main Crew orchestrator for LEGION OMEGA V0.34.
    Hierarchical process: Planner → Feature Builders (parallel) → Compiler → Fixer (loop)
    """

    def __init__(self, memory: MemoryManager, notify_callback: Optional[Callable] = None):
        self.memory = memory
        self.notify = notify_callback  # async fn(msg: str)
        self.project_path = None

    async def start_project(
        self,
        description: str,
        budget_usd: float,
        zip_path: Optional[str] = None,
        app_name: Optional[str] = None
    ) -> None:
        """
        Full project orchestration pipeline using CrewAI.
        """
        try:
            await self._phase_init(description, budget_usd, zip_path, app_name)
            await self._phase_plan()
            await self._phase_build()
            await self._phase_compile()
            await self._phase_finalize()
        except Exception as e:
            logger.exception(f"Crew fatal error: {e}")
            if self.notify:
                await self.notify(f"Error inesperado: {str(e)[:200]}")

    async def _phase_init(self, description: str, budget_usd: float, zip_path: Optional[str], app_name: Optional[str]):
        """Initialize project metadata in memory."""
        from datetime import datetime
        self.memory.reset()
        name = app_name or self._slugify(description[:30])
        now = datetime.utcnow().isoformat()

        self.memory.update_memory("project.name", name)
        self.memory.update_memory("project.description", description)
        self.memory.update_memory("project.created_at", now)
        self.memory.update_memory("project.status", "initializing")
        self.memory.update_memory("project.budget_usd", budget_usd)
        self.memory.update_memory("project.budget_remaining_usd", budget_usd)

        logger.info(f"[INIT] Project {name} initialized with budget ${budget_usd}")
        if self.notify:
            await self.notify("⚙️ Inicializando proyecto...")

    async def _phase_plan(self):
        """Run Planner agent to produce ProjectPlan."""
        if self.notify:
            await self.notify("🧠 Analizando tu solicitud y creando plan...")

        mem = self.memory.get_memory()
        description = mem["project"]["description"]
        brand_assets = mem.get("brand_assets", {})

        # Execute plan_project_task with Planner
        plan_crew = Crew(
            agents=[planner],
            tasks=[plan_project_task],
            process=Process.sequential,
            verbose=True
        )

        try:
            result = plan_crew.kickoff(
                inputs={
                    "description": description,
                    "budget_usd": mem["project"]["budget_usd"],
                    "brand_assets": brand_assets
                }
            )
            logger.info(f"[PLAN] Result: {result}")
            plan = self._parse_json_output(result)
            self.memory.update_memory("plan", plan)
        except Exception as e:
            logger.error(f"[PLAN] Failed: {e}")
            # Fallback minimal plan
            self.memory.update_memory("plan", {
                "app_name": self._slugify(description[:30]),
                "app_display_name": description[:40],
                "features": [{"name": "core", "description": description, "entities": ["Item"], "use_cases": ["GetItems"], "screens": ["HomeScreen"]}],
                "global_theme": {"primary_color": "#6200EE"},
                "navigation_routes": ["/home"]
            })

    async def _phase_build(self):
        """Initialize Flutter project and generate code for all features."""
        if self.notify:
            await self.notify("📱 Creando proyecto Flutter...")

        mem = self.memory.get_memory()
        plan = mem.get("plan", {})
        app_name = plan.get("app_name", "legion_app")
        output_dir = "./output"

        # Initialize Flutter project
        initializer = ProjectInitializer(output_dir)
        self.project_path = await initializer.create(app_name)
        self.memory.update_memory("flutter_project.path", self.project_path)

        if self.notify:
            await self.notify("📝 Generando código...")

        # TODO: Generate code for each feature using parallel crews
        # For now, placeholder
        self.memory.update_memory("project.status", "code_generated")

    async def _phase_compile(self):
        """Compile the Flutter project with automatic error fixing."""
        if self.notify:
            await self.notify("🔨 Compilando proyecto...")

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            compiler = FlutterCompiler(self.project_path)
            result = await compiler.full_build_cycle()

            if result["success"]:
                self.memory.update_memory("project.status", "compiled")
                if self.notify:
                    await self.notify("✅ Compilación exitosa!")
                return

            logger.warning(f"Compilation attempt {attempt} failed")
            if attempt < max_attempts:
                # Run fixer crew
                fix_crew = Crew(
                    agents=[fixer_agent],
                    tasks=[fix_compile_errors_task],
                    process=Process.sequential,
                    verbose=True
                )
                await fix_crew.kickoff(
                    inputs={"errors": result.get("errors", [])}
                )

        self.memory.update_memory("project.status", "compilation_failed")

    async def _phase_finalize(self):
        """Final status report."""
        self.memory.update_memory("project.status", "done")
        if self.notify:
            await self.notify("🎉 Proyecto completado!")

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        slug = re.sub(r"[^\w\s]", "", text.lower())
        slug = re.sub(r"\s+", "_", slug.strip())
        return slug or "legion_app"

    @staticmethod
    def _parse_json_output(text: str) -> Dict[str, Any]:
        """Extract JSON from LLM output (handles markdown, extra text, etc)."""
        import json
        text = str(text).strip()

        # Strip markdown code fences
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip() if "```" in text else text

        # Find JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON: {text[:200]}")
            return {}

    def get_status(self) -> str:
        mem = self.memory.get_memory()
        proj = mem.get("project", {})
        return f"""
*Estado del Proyecto*
Nombre: {proj.get('name', 'N/A')}
Estado: {proj.get('status', 'idle')}
Presupuesto: ${proj.get('budget_usd', 0):.2f}
Restante: ${proj.get('budget_remaining_usd', 0):.2f}
"""
