import os
import json
import logging
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
import google.generativeai as genai
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "context_agent_system.txt")


class ContextAgent:
    MODEL = "gemini-2.0-flash"
    MAX_OUTPUT_TOKENS = 1024
    MAX_INPUT_TOKENS = 30000  # Keep well under 128k limit

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        self.model = genai.GenerativeModel(
            model_name=self.MODEL,
            system_instruction=self.system_prompt
        )

    async def translate_status(self, event: str, details: dict = None) -> str:
        """Convert a technical event to a user-friendly Telegram message."""
        import asyncio
        payload = {"event": event, "details": details or {}}
        payload_str = json.dumps(payload, ensure_ascii=False)

        # Truncate if too long
        if len(payload_str) > self.MAX_INPUT_TOKENS * 3:
            payload_str = payload_str[:self.MAX_INPUT_TOKENS * 3]

        response = await asyncio.to_thread(
            self.model.generate_content,
            payload_str,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=self.MAX_OUTPUT_TOKENS,
                temperature=0.7
            )
        )

        usage = response.usage_metadata
        self.memory.log_token_usage(
            "context_agent",
            usage.prompt_token_count,
            usage.candidates_token_count
        )

        return response.text.strip()

    async def handle_user_message(self, message: str, project_state: dict) -> str:
        """Handle free-form user message in Telegram conversation."""
        import asyncio
        context = {
            "user_message": message,
            "project_status": project_state.get("project", {}).get("status", "idle"),
            "project_name": project_state.get("project", {}).get("name", ""),
            "budget_remaining": project_state.get("project", {}).get("budget_remaining_usd", 0.0)
        }
        response = await asyncio.to_thread(
            self.model.generate_content,
            json.dumps(context, ensure_ascii=False),
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=self.MAX_OUTPUT_TOKENS,
                temperature=0.8
            )
        )
        usage = response.usage_metadata
        self.memory.log_token_usage("context_agent", usage.prompt_token_count, usage.candidates_token_count)
        return response.text.strip()
