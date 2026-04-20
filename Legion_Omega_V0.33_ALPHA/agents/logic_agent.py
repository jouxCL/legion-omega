import os
import json
import logging
from openai import AsyncOpenAI
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "logic_agent_system.txt")


class LogicAgent:
    MODEL = "deepseek-chat"
    API_BASE = "https://api.deepseek.com"
    MAX_TOKENS = 8000

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=self.API_BASE
        )
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def execute(self, task: dict) -> dict:
        """Execute a logic/architecture task. Returns parsed JSON result."""
        user_message = json.dumps({
            "task_id": task["task_id"],
            "layer": task["layer"],
            "feature": task["feature"],
            "description": task["description"],
            "input_contract": task["input_contract"],
            "output_contract": task["output_contract"]
        }, ensure_ascii=False, indent=2)

        response = await self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=self.MAX_TOKENS,
            temperature=0.2
        )

        usage = response.usage
        self.memory.log_token_usage("logic_agent", usage.prompt_tokens, usage.completion_tokens)

        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # Register the generated file in memory
        if "filename" in result:
            layer = task["layer"]
            name = os.path.basename(result["filename"]).replace(".dart", "")
            self.memory.register_file(
                layer, name, result["filename"],
                task["description"]
            )

        return result

    async def fix_compilation_error(self, error_info: dict) -> dict:
        """Specialized method for fixing compilation errors."""
        error_info["task_type"] = "fix_compilation_error"
        mock_task = {
            "task_id": "fix",
            "layer": "fix",
            "feature": "compilation",
            "description": f"Corregir error de compilación en {error_info.get('error_file', '')}",
            "input_contract": error_info,
            "output_contract": "archivo corregido completo"
        }
        return await self.execute(mock_task)
