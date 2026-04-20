import logging
from typing import Optional
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class FailureHandler:
    MAX_ATTEMPTS = 4

    def __init__(self, memory: MemoryManager, notify_callback=None):
        self.memory = memory
        self.notify = notify_callback  # async fn(message: str)

    async def handle_task_failure(self, task: dict, error: str, dispatcher) -> Optional[dict]:
        """
        Returns updated task if retry should happen, None if escalated to user.
        """
        attempts = task.get("attempts", 0) + 1
        task["attempts"] = attempts
        task["error"] = error

        log_entry = {
            "task_id": task["task_id"],
            "feature": task["feature"],
            "layer": task["layer"],
            "attempt": attempts,
            "error": error[:500]
        }
        self.memory.append_to_memory("errors_log", log_entry)

        if attempts <= 2:
            logger.warning(f"[FailureHandler] Task {task['task_id']} failed (attempt {attempts}). Simple retry.")
            task["input_contract"]["previous_error"] = error
            task["status"] = "pending"
            return task

        if attempts == 3:
            logger.warning(f"[FailureHandler] Task {task['task_id']} failed (attempt 3). Expanding context.")
            mem = self.memory.get_memory()
            code_map = mem.get("code_map", {})
            # Add relevant existing files as context
            feature = task.get("feature", "")
            relevant = {}
            for layer, files in code_map.items():
                for name, info in files.items():
                    if feature in name or feature in info.get("path", ""):
                        relevant[name] = info
            task["input_contract"]["expanded_context"] = relevant
            task["input_contract"]["previous_error"] = error
            task["status"] = "pending"
            return task

        if attempts == 4:
            logger.error(f"[FailureHandler] Task {task['task_id']} failed 4 times. Escalating to user.")
            task["status"] = "failed"
            if self.notify:
                await self.notify(
                    f"⚠️ *Necesito tu ayuda*\n\n"
                    f"La tarea de *{task['feature']}* ({task['layer']}) falló varias veces.\n\n"
                    f"Error resumido: {error[:200]}\n\n"
                    f"¿Qué hacemos?\n"
                    f"• Responde *SIMPLIFICAR* para intentar una versión más básica\n"
                    f"• Responde *SALTAR* para omitir esta funcionalidad\n"
                    f"• Responde *REINTENTAR* para intentar una vez más"
                )
            return None

        task["status"] = "failed"
        return None

    async def handle_compilation_error(self, errors: list, flutter_builder, dispatcher) -> list:
        """
        Creates fix tasks for each compilation error.
        Returns list of fix tasks to dispatch.
        """
        import uuid
        fix_tasks = []
        for err in errors:
            fix_task = {
                "task_id": f"fix_{str(uuid.uuid4())[:6]}",
                "type": "fix",
                "agent": "ui_agent",
                "feature": "compilation_fix",
                "layer": "fix",
                "description": f"Corregir error en {err.get('file', 'unknown')}",
                "input_contract": {
                    "error_file": err.get("file", ""),
                    "error_line": err.get("line", 0),
                    "error_message": err.get("message", ""),
                    "error_type": err.get("error_type", "compile_error"),
                    "context_files": err.get("context_files", [])
                },
                "output_contract": "archivo corregido completo en Dart",
                "dependencies": [],
                "estimated_input_tokens": 3000,
                "estimated_output_tokens": 2000,
                "status": "pending",
                "output": None,
                "error": None,
                "attempts": 0
            }
            fix_tasks.append(fix_task)
        return fix_tasks
