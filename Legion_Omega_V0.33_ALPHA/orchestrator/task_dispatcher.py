import asyncio
import logging
from typing import List, Callable, Awaitable
from memory.memory_manager import MemoryManager
from orchestrator.budget_manager import can_afford

logger = logging.getLogger(__name__)


class TaskDispatcher:
    def __init__(self, memory: MemoryManager, agent_registry: dict, failure_handler):
        """
        agent_registry: {"logic_agent": LogicAgent(), "ui_agent": UIAgent(), ...}
        """
        self.memory = memory
        self.agents = agent_registry
        self.failure_handler = failure_handler

    def _get_executable_tasks(self, tasks: List[dict]) -> List[dict]:
        """Returns tasks whose dependencies are all completed."""
        completed_ids = {t["task_id"] for t in tasks if t["status"] == "completed"}
        return [
            t for t in tasks
            if t["status"] == "pending"
            and all(dep in completed_ids for dep in t.get("dependencies", []))
        ]

    async def dispatch_all(self, tasks: List[dict], on_task_done: Callable = None) -> List[dict]:
        """
        Executes the full DAG respecting dependencies.
        Tasks without inter-dependencies run in parallel.
        """
        while True:
            executable = self._get_executable_tasks(tasks)
            if not executable:
                pending = [t for t in tasks if t["status"] == "pending"]
                if pending:
                    logger.error(f"Deadlock: {len(pending)} pending tasks with unresolvable deps")
                break

            await asyncio.gather(*[self._run_task(t, tasks, on_task_done) for t in executable])

        return tasks

    async def _run_task(self, task: dict, all_tasks: List[dict], on_task_done: Callable = None):
        agent_name = task["agent"]
        agent = self.agents.get(agent_name)
        if not agent:
            logger.error(f"No agent registered for '{agent_name}'")
            task["status"] = "failed"
            task["error"] = f"Agent '{agent_name}' not found"
            return

        if not can_afford(agent_name, task["estimated_input_tokens"], task["estimated_output_tokens"]):
            logger.warning(f"Budget insufficient for task {task['task_id']}")
            task["status"] = "failed"
            task["error"] = "budget_exceeded"
            if self.failure_handler.notify:
                await self.failure_handler.notify(
                    "💰 *Presupuesto insuficiente*\n\n"
                    "El presupuesto actual no alcanza para continuar. "
                    "¿Deseas agregar más fondos? Indica el monto en dólares."
                )
            return

        task["status"] = "running"
        logger.info(f"[Dispatcher] Running task {task['task_id']} ({task['layer']}) with {agent_name}")

        try:
            result = await agent.execute(task)
            task["output"] = result
            task["status"] = "completed"
            self.memory.append_to_memory("dag.completed", task["task_id"])
            if task["task_id"] in self._get_pending_ids(all_tasks):
                self._remove_from_pending(all_tasks, task["task_id"])
            if on_task_done:
                await on_task_done(task)
        except Exception as e:
            logger.exception(f"Task {task['task_id']} raised exception: {e}")
            retry_task = await self.failure_handler.handle_task_failure(task, str(e), self)
            if retry_task is not None:
                await self._run_task(retry_task, all_tasks, on_task_done)

    def _get_pending_ids(self, tasks):
        return {t["task_id"] for t in tasks if t["status"] == "pending"}

    def _remove_from_pending(self, tasks, task_id):
        pass  # statuses managed in-place
