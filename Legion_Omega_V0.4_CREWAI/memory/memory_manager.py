import json
import os
from datetime import datetime
from typing import Any
from config.pricing import calculate_cost, ROLE_MODEL as AGENT_MODELS

MEMORY_FILE = os.getenv("MEMORY_FILE", "./memory/project_memory.json")

DEFAULT_MEMORY = {
    "project": {
        "name": "",
        "description": "",
        "created_at": "",
        "status": "idle",
        "budget_usd": 0.0,
        "budget_remaining_usd": 0.0
    },
    "flutter_project": {
        "path": "",
        "package_name": "",
        "features": [],
        "dependencies": []
    },
    "token_usage": {
        "planner":      {"input": 0, "output": 0, "cost_usd": 0.0},
        "logic":        {"input": 0, "output": 0, "cost_usd": 0.0},
        "ui":           {"input": 0, "output": 0, "cost_usd": 0.0},
        "compiler_ops": {"input": 0, "output": 0, "cost_usd": 0.0},
        "fixer":        {"input": 0, "output": 0, "cost_usd": 0.0},
        "comms":        {"input": 0, "output": 0, "cost_usd": 0.0},
        "total_cost_usd": 0.0
    },
    "dag": {"tasks": [], "completed": [], "failed": [], "pending": []},
    "code_map": {
        "entities": {}, "repositories": {}, "use_cases": {},
        "cubits": {}, "screens": {}, "widgets": {}, "routes": {}
    },
    "brand_assets": {"colors": [], "fonts": [], "logo_path": "", "raw_files": []},
    "errors_log": [],
    "compilation_attempts": 0
}


class MemoryManager:
    def __init__(self, memory_file: str = None):
        self.memory_file = memory_file or MEMORY_FILE
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        if not os.path.exists(self.memory_file):
            self._write(DEFAULT_MEMORY)

    def _read(self) -> dict:
        with open(self.memory_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_memory(self) -> dict:
        return self._read()

    def update_memory(self, path: str, value: Any):
        data = self._read()
        keys = path.split(".")
        node = data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
        self._write(data)

    def append_to_memory(self, path: str, item: Any):
        data = self._read()
        keys = path.split(".")
        node = data
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        lst = node.setdefault(keys[-1], [])
        lst.append(item)
        self._write(data)

    def log_token_usage(self, agent: str, input_tokens: int, output_tokens: int):
        data = self._read()
        usage = data.setdefault("token_usage", {})
        agent_usage = usage.setdefault(agent, {"input": 0, "output": 0, "cost_usd": 0.0})
        agent_usage["input"] += input_tokens
        agent_usage["output"] += output_tokens
        model = AGENT_MODELS.get(agent, "gemini-2.0-flash")
        cost = calculate_cost(model, input_tokens, output_tokens)
        agent_usage["cost_usd"] = round(agent_usage.get("cost_usd", 0.0) + cost, 6)
        total = sum(v.get("cost_usd", 0.0) for k, v in usage.items() if isinstance(v, dict))
        usage["total_cost_usd"] = round(total, 6)
        # Deduct from remaining budget
        project = data.setdefault("project", {})
        remaining = project.get("budget_remaining_usd", 0.0)
        project["budget_remaining_usd"] = max(0.0, round(remaining - cost, 6))
        self._write(data)

    def get_remaining_budget(self) -> float:
        data = self._read()
        return data.get("project", {}).get("budget_remaining_usd", 0.0)

    def register_file(self, layer: str, name: str, path: str, description: str):
        data = self._read()
        code_map = data.setdefault("code_map", {})
        layer_map = code_map.setdefault(layer, {})
        layer_map[name] = {"path": path, "description": description}
        self._write(data)

    def reset(self):
        mem = dict(DEFAULT_MEMORY)
        mem["project"]["created_at"] = datetime.utcnow().isoformat()
        self._write(mem)
