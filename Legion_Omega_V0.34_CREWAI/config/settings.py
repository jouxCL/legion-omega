"""Typed settings for LEGION OMEGA V0.4. Loads .env via pydantic-settings."""
from __future__ import annotations
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str
    DEEPSEEK_API_KEY: str
    MISTRAL_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ALLOWED_USER_ID: int

    FLUTTER_PATH: str = "flutter"
    OUTPUT_DIR: str = str(PROJECT_ROOT / "output")
    MEMORY_FILE: str = str(PROJECT_ROOT / "memory" / "project_memory.json")
    DEFAULT_MAX_BUDGET_USD: float = 0.5
    MAX_COMPILE_ATTEMPTS: int = 3
    LOG_FILE: str = str(PROJECT_ROOT / "legion_omega_v04.log")


def get_settings() -> Settings:
    s = Settings()
    os.environ.setdefault("GEMINI_API_KEY", s.GEMINI_API_KEY)
    os.environ.setdefault("DEEPSEEK_API_KEY", s.DEEPSEEK_API_KEY)
    os.environ.setdefault("MISTRAL_API_KEY", s.MISTRAL_API_KEY)
    os.environ.setdefault("MEMORY_FILE", s.MEMORY_FILE)
    return s
