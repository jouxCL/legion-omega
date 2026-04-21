"""Entry point for LEGION OMEGA V0.4 (CrewAI).

Loads settings, wires the Runtime (MemoryManager + LegionOmegaFlow + notify
channel) and starts the Telegram bot.
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.settings import get_settings
from crew.runtime import get_runtime
from crew.flow import LegionOmegaFlow
from memory.memory_manager import MemoryManager
from tg_bot.bot import run_bot


def _configure_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)],
    )
    for noisy in ("httpx", "telegram", "httpcore", "urllib3", "LiteLLM"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _check_env(settings) -> None:
    required = [
        ("GEMINI_API_KEY", settings.GEMINI_API_KEY),
        ("DEEPSEEK_API_KEY", settings.DEEPSEEK_API_KEY),
        ("MISTRAL_API_KEY", settings.MISTRAL_API_KEY),
        ("TELEGRAM_BOT_TOKEN", settings.TELEGRAM_BOT_TOKEN),
    ]
    missing = [k for k, v in required if not v]
    if missing:
        raise SystemExit(f"Faltan variables de entorno: {missing}")


def main() -> None:
    settings = get_settings()
    _configure_logging(settings.LOG_FILE)
    logger = logging.getLogger("legion_omega_v04")
    _check_env(settings)

    runtime = get_runtime()
    runtime.memory = MemoryManager(settings.MEMORY_FILE)
    runtime.flow = LegionOmegaFlow()

    logger.info("LEGION OMEGA V0.4 CREWAI bootstrapped")
    run_bot()


if __name__ == "__main__":
    main()
