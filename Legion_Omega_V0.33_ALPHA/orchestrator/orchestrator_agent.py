import os
import json
import asyncio
import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
import google.generativeai as genai
from datetime import datetime
from typing import Optional, Callable

from memory.memory_manager import MemoryManager
from orchestrator.dag_builder import build_dag_from_plan
from orchestrator.budget_manager import allocate_budget_for_project, get_budget_report, can_afford
from orchestrator.task_dispatcher import TaskDispatcher
from orchestrator.failure_handler import FailureHandler
from agents.logic_agent import LogicAgent
from agents.ui_agent import UIAgent
from agents.context_agent import ContextAgent
from flutter_builder.project_initializer import ProjectInitializer
from flutter_builder.file_writer import FileWriter
from flutter_builder.compiler import FlutterCompiler
from flutter_builder.zip_processor import process_brand_zip

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "orchestrator_system.txt")


class OrchestratorAgent:
    MODEL = "gemini-2.5-pro"
    MAX_COMPILATION_ATTEMPTS = 5

    def __init__(self, notify_telegram: Callable = None):
        self.memory = MemoryManager()
        self.notify = notify_telegram  # async fn(str) → sends message to Telegram user
        self._setup_gemini()
        self._pending_user_response: Optional[asyncio.Future] = None
        self._user_response_context: Optional[str] = None

    def _setup_gemini(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        self.model = genai.GenerativeModel(
            model_name=self.MODEL,
            system_instruction=system_prompt
        )

    # ─────────────────────────────────────────────
    # PUBLIC: Start a new project
    # ─────────────────────────────────────────────

    async def start_project(self, description: str, budget_usd: float,
                             zip_path: Optional[str] = None,
                             app_name: Optional[str] = None) -> None:
        """Full project orchestration pipeline."""
        try:
            await self._phase_init(description, budget_usd, zip_path, app_name)
            await self._phase_build_dag()
            await self._phase_execute_dag()
            await self._phase_compile()
            await self._phase_finalize()
        except Exception as e:
            logger.exception(f"Orchestrator fatal error: {e}")
            if self.notify:
                await self.notify(
                    f"⚠️ *Error inesperado*\n\nOcurrió un problema grave: {str(e)[:300]}\n\n"
                    "El sistema ha guardado el progreso. Puedes usar /estado para ver el avance."
                )

    # ─────────────────────────────────────────────
    # PHASE 1: Initialize project
    # ─────────────────────────────────────────────

    async def _phase_init(self, description: str, budget_usd: float,
                           zip_path: Optional[str], app_name: Optional[str]):
        if self.notify:
            await self.notify("⚙️ Inicializando proyecto LEGION OMEGA...")

        self.memory.reset()
        name = app_name or self._slugify(description[:30])
        now = datetime.utcnow().isoformat()

        self.memory.update_memory("project.name", name)
        self.memory.update_memory("project.description", description)
        self.memory.update_memory("project.created_at", now)
        self.memory.update_memory("project.status", "initializing")
        self.memory.update_memory("project.budget_usd", budget_usd)
        self.memory.update_memory("project.budget_remaining_usd", budget_usd)

        # Distribute budget
        allocation = allocate_budget_for_project(budget_usd)
        logger.info(f"Budget allocation: {json.dumps(allocation, indent=2)}")

        # Process brand assets
        if zip_path and os.path.exists(zip_path):
            output_dir = os.path.join(os.getenv("OUTPUT_DIR", "./output"), name)
            brand = process_brand_zip(zip_path, output_dir)
            self.memory.update_memory("brand_assets", brand)
            if self.notify:
                await self.notify(f"🎨 Assets de marca procesados: {len(brand['raw_files'])} archivos encontrados.")

        # Create Flutter project
        output_dir = os.getenv("OUTPUT_DIR", "./output")
        initializer = ProjectInitializer(output_dir)
        if self.notify:
            await self.notify("📱 Creando estructura del proyecto Flutter...")
        project_path = await initializer.create(name)
        self.memory.update_memory("flutter_project.path", project_path)
        self.memory.update_memory("flutter_project.package_name", f"com.legomega.{name}")

        self._project_path = project_path
        self._project_name = name

    # ─────────────────────────────────────────────
    # PHASE 2: Build DAG
    # ─────────────────────────────────────────────

    async def _phase_build_dag(self):
        mem = self.memory.get_memory()
        description = mem["project"]["description"]
        brand_assets = mem.get("brand_assets", {})

        if self.notify:
            await self.notify("🧠 Analizando tu solicitud y planificando el proyecto...")

        plan = await self._call_gemini_plan(description, brand_assets)
        tasks = build_dag_from_plan(plan)

        self.memory.update_memory("dag.tasks", tasks)
        self.memory.update_memory("dag.pending", [t["task_id"] for t in tasks])
        self.memory.update_memory("project.status", "dag_ready")

        summary = self._format_dag_summary(tasks, plan)
        if self.notify:
            await self.notify(summary)

    async def _call_gemini_plan(self, description: str, brand_assets: dict) -> dict:
        """Ask Gemini 2.5 Pro to analyze the request and produce a structured plan."""
        prompt = f"""Analiza esta solicitud de app Flutter y produce un plan estructurado.

SOLICITUD DEL USUARIO:
{description}

ASSETS DE MARCA DISPONIBLES:
{json.dumps(brand_assets, ensure_ascii=False)}

Devuelve SOLO un JSON con esta estructura:
{{
  "app_name": "nombre_en_snake_case",
  "app_display_name": "Nombre Legible",
  "features": [
    {{
      "name": "feature_name",
      "description": "qué hace este feature",
      "entities": ["NombreEntidad1"],
      "use_cases": ["GetItems", "CreateItem"],
      "screens": ["ListScreen", "DetailScreen"]
    }}
  ],
  "global_theme": {{
    "primary_color": "#hex o descripción",
    "style": "Material3 / descripción del estilo visual"
  }},
  "navigation_routes": ["/home", "/detail/:id"],
  "brand_assets": {json.dumps(brand_assets, ensure_ascii=False)}
}}

IMPORTANTE: Divide el trabajo en features pequeños y manejables. Cada feature = un dominio de negocio.
"""
        import asyncio
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.3
            )
        )
        usage = response.usage_metadata
        self.memory.log_token_usage("orchestrator", usage.prompt_token_count, usage.candidates_token_count)

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()
        return json.loads(text)

    def _format_dag_summary(self, tasks: list, plan: dict) -> str:
        total = len(tasks)
        logic_count = sum(1 for t in tasks if t["agent"] == "logic_agent")
        ui_count = sum(1 for t in tasks if t["agent"] == "ui_agent")
        features = [f["name"] for f in plan.get("features", [])]
        return (
            f"📋 *Plan generado*\n\n"
            f"*App:* {plan.get('app_display_name', 'Tu App')}\n"
            f"*Features:* {', '.join(features)}\n"
            f"*Tareas totales:* {total} ({logic_count} lógica, {ui_count} UI)\n\n"
            f"¿Empezamos? Responde *SI* para confirmar o *NO* para cancelar."
        )

    # ─────────────────────────────────────────────
    # PHASE 3: Execute DAG
    # ─────────────────────────────────────────────

    async def _phase_execute_dag(self):
        mem = self.memory.get_memory()
        tasks = mem["dag"]["tasks"]

        logic_agent = LogicAgent(self.memory)
        ui_agent = UIAgent(self.memory)
        context_agent = ContextAgent(self.memory)

        failure_handler = FailureHandler(self.memory, notify_callback=self.notify)
        dispatcher = TaskDispatcher(
            self.memory,
            {"logic_agent": logic_agent, "ui_agent": ui_agent},
            failure_handler
        )

        self.memory.update_memory("project.status", "executing")
        completed_count = [0]

        async def on_task_done(task: dict):
            completed_count[0] += 1
            # Write the Dart file
            if task.get("output"):
                writer = FileWriter(self._project_path, self.memory)
                try:
                    writer.write_task_output(task)
                except Exception as e:
                    logger.error(f"Failed to write file for task {task['task_id']}: {e}")

            # Notify every 3 tasks to avoid spam
            if completed_count[0] % 3 == 0 and self.notify:
                msg = await context_agent.translate_status(
                    "task_completed",
                    {"completed": completed_count[0], "total": len(tasks), "feature": task["feature"]}
                )
                await self.notify(msg)

        await dispatcher.dispatch_all(tasks, on_task_done)
        self.memory.update_memory("project.status", "dag_completed")

    # ─────────────────────────────────────────────
    # PHASE 4: Compile and fix
    # ─────────────────────────────────────────────

    async def _phase_compile(self):
        compiler = FlutterCompiler(self._project_path)
        failure_handler = FailureHandler(self.memory, notify_callback=self.notify)
        ui_agent = UIAgent(self.memory)

        if self.notify:
            await self.notify("🔨 Compilando el proyecto. Esto puede tomar unos minutos...")

        for attempt in range(1, self.MAX_COMPILATION_ATTEMPTS + 1):
            self.memory.update_memory("compilation_attempts", attempt)
            result = await compiler.full_build_cycle()

            if result["success"]:
                self.memory.update_memory("project.status", "compiled")
                if self.notify:
                    await self.notify("✅ *¡Compilación exitosa!* Tu app está lista.")
                return

            errors = result["errors"]
            logger.warning(f"Compilation attempt {attempt} failed with {len(errors)} error(s)")

            if attempt >= self.MAX_COMPILATION_ATTEMPTS:
                self.memory.update_memory("project.status", "compilation_failed")
                if self.notify:
                    await self.notify(
                        f"⚠️ No se pudo compilar después de {self.MAX_COMPILATION_ATTEMPTS} intentos.\n"
                        "Puedes usar /estado para ver los errores o contactar soporte."
                    )
                return

            # Create fix tasks
            fix_tasks = await failure_handler.handle_compilation_error(errors, None, None)
            for fix_task in fix_tasks:
                try:
                    output = await ui_agent.execute(fix_task)
                    if output and "filename" in output:
                        writer = FileWriter(self._project_path, self.memory)
                        writer.write_dart_file(output["filename"], output["content"])
                except Exception as e:
                    logger.error(f"Fix task failed: {e}")

            if self.notify:
                await self.notify(f"🔧 Aplicando correcciones (intento {attempt}/{self.MAX_COMPILATION_ATTEMPTS})...")

    # ─────────────────────────────────────────────
    # PHASE 5: Finalize
    # ─────────────────────────────────────────────

    async def _phase_finalize(self):
        mem = self.memory.get_memory()
        report = get_budget_report(mem)
        self.memory.update_memory("project.status", "done")
        if self.notify:
            await self.notify(
                f"🎉 *¡Proyecto completado!*\n\n"
                f"Tu app Flutter está en:\n`{self._project_path}`\n\n"
                f"{report}"
            )

    # ─────────────────────────────────────────────
    # USER INPUT HANDLING
    # ─────────────────────────────────────────────

    async def handle_user_response(self, text: str):
        """Called when user sends a message during an active project."""
        if self._pending_user_response and not self._pending_user_response.done():
            self._pending_user_response.set_result(text.strip().upper())

    async def _wait_for_user_input(self, context: str, timeout: float = 300) -> str:
        """Pauses orchestration and waits for user Telegram reply."""
        self._pending_user_response = asyncio.get_event_loop().create_future()
        self._user_response_context = context
        try:
            return await asyncio.wait_for(self._pending_user_response, timeout=timeout)
        except asyncio.TimeoutError:
            return "TIMEOUT"

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        slug = re.sub(r"[^\w\s]", "", text.lower())
        slug = re.sub(r"\s+", "_", slug.strip())
        return slug or "legion_app"

    def get_status(self) -> str:
        mem = self.memory.get_memory()
        proj = mem.get("project", {})
        dag = mem.get("dag", {})
        total = len(dag.get("tasks", []))
        done = len(dag.get("completed", []))
        failed = len(dag.get("failed", []))
        return (
            f"*Estado del proyecto*\n\n"
            f"*Nombre:* {proj.get('name', 'N/A')}\n"
            f"*Estado:* {proj.get('status', 'idle')}\n"
            f"*Progreso:* {done}/{total} tareas completadas\n"
            f"*Fallos:* {failed}\n"
            f"*Intentos compilación:* {mem.get('compilation_attempts', 0)}\n"
            f"*Presupuesto restante:* ${proj.get('budget_remaining_usd', 0):.4f}"
        )
