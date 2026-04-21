"""LLM factory by role (CrewAI + LiteLLM).

Each role maps to a provider-prefixed LiteLLM model string. API keys are read
from the environment (GEMINI_API_KEY / DEEPSEEK_API_KEY / MISTRAL_API_KEY).
"""
from __future__ import annotations
from functools import lru_cache
from crewai import LLM
from config.pricing import ROLE_LITELLM_MODEL

_ROLE_TEMPERATURE = {
    "planner":      0.2,
    "logic":        0.1,
    "ui":           0.3,
    "compiler_ops": 0.0,
    "fixer":        0.1,
    "comms":        0.6,
}


@lru_cache(maxsize=None)
def get_llm(role: str) -> LLM:
    model = ROLE_LITELLM_MODEL.get(role)
    if model is None:
        raise ValueError(f"Unknown role: {role}. Known: {list(ROLE_LITELLM_MODEL)}")
    return LLM(model=model, temperature=_ROLE_TEMPERATURE.get(role, 0.2))
