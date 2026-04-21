"""LLM pricing + per-role model mapping for LEGION OMEGA V0.4.

Self-contained replacement for V0.33's orchestrator.costs / orchestrator.budget_manager,
so memory_manager can compute token cost without pulling legacy orchestrator code.
"""
from __future__ import annotations

COSTS: dict[str, dict[str, float]] = {
    "gemini-2.5-pro": {
        "input_tier1":  1.25 / 1_000_000,
        "input_tier2":  2.50 / 1_000_000,
        "output_tier1": 10.00 / 1_000_000,
        "output_tier2": 15.00 / 1_000_000,
        "tier_threshold": 200_000,
    },
    "gemini-2.0-flash": {"input": 0.10 / 1_000_000, "output": 0.40 / 1_000_000},
    "gemini-2.5-flash": {"input": 0.30 / 1_000_000, "output": 2.50 / 1_000_000},
    "deepseek-chat":   {"input": 0.27 / 1_000_000, "output": 1.10 / 1_000_000},
    "mistral-small":   {"input": 0.0, "output": 0.0},
}

ROLE_MODEL: dict[str, str] = {
    "planner":       "gemini-2.5-pro",
    "logic":         "deepseek-chat",
    "ui":            "mistral-small",
    "compiler_ops":  "gemini-2.0-flash",
    "fixer":         "deepseek-chat",
    "comms":         "gemini-2.0-flash",
}

ROLE_LITELLM_MODEL: dict[str, str] = {
    "planner":       "gemini/gemini-2.5-pro",
    "logic":         "deepseek/deepseek-chat",
    "ui":            "mistral/mistral-small-latest",
    "compiler_ops":  "gemini/gemini-2.0-flash",
    "fixer":         "deepseek/deepseek-chat",
    "comms":         "gemini/gemini-2.0-flash",
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    c = COSTS.get(model)
    if c is None:
        return 0.0
    if model == "gemini-2.5-pro":
        t = c["tier_threshold"]
        in_cost = (input_tokens * c["input_tier1"]) if input_tokens <= t else \
            (t * c["input_tier1"] + (input_tokens - t) * c["input_tier2"])
        out_cost = (output_tokens * c["output_tier1"]) if input_tokens <= t else \
            (output_tokens * c["output_tier2"])
        return in_cost + out_cost
    return input_tokens * c.get("input", 0.0) + output_tokens * c.get("output", 0.0)
