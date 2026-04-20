import os
import json
import logging
import asyncio
from mistralai.client import Mistral
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "ui_agent_system.txt")

# Mistral rate limit: 20 calls/minute on Experimental plan
_RATE_LIMIT_LOCK = asyncio.Semaphore(20)
_CALL_TIMESTAMPS = []


class UIAgent:
    MODEL = "mistral-small-latest"

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def _rate_limited_call(self, messages: list) -> any:
        """Enforce 20 calls/minute rate limit."""
        import time
        async with _RATE_LIMIT_LOCK:
            now = time.time()
            # Remove timestamps older than 60 seconds
            _CALL_TIMESTAMPS[:] = [t for t in _CALL_TIMESTAMPS if now - t < 60]
            if len(_CALL_TIMESTAMPS) >= 20:
                wait_time = 60 - (now - _CALL_TIMESTAMPS[0]) + 0.5
                logger.info(f"[UIAgent] Rate limit reached. Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            _CALL_TIMESTAMPS.append(time.time())

        response = await asyncio.to_thread(
            self.client.chat,
            model=self.MODEL,
            messages=messages,
            temperature=0.2
        )
        return response

    async def execute(self, task: dict) -> dict:
        user_message = json.dumps({
            "task_id": task["task_id"],
            "layer": task["layer"],
            "feature": task["feature"],
            "description": task["description"],
            "input_contract": task["input_contract"],
            "output_contract": task["output_contract"]
        }, ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = await self._rate_limited_call(messages)
        # Mistral free plan: tokens are $0 but we still track them
        if hasattr(response, 'usage') and response.usage:
            self.memory.log_token_usage("ui_agent", response.usage.prompt_tokens, response.usage.completion_tokens)
        else:
            # Estimate: assume roughly equal input/output for free plan
            self.memory.log_token_usage("ui_agent", 1000, 1000)

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.rsplit("```", 1)[0].strip()

        result = json.loads(content)

        if "filename" in result:
            layer = task["layer"]
            name = os.path.basename(result["filename"]).replace(".dart", "")
            self.memory.register_file(layer, name, result["filename"], task["description"])

        return result
