COSTS = {
    "gemini-2.5-pro": {
        "input_tier1":  1.25 / 1_000_000,
        "input_tier2":  2.50 / 1_000_000,
        "output_tier1": 10.00 / 1_000_000,
        "output_tier2": 15.00 / 1_000_000,
        "tier_threshold": 200_000
    },
    "deepseek-chat": {
        "input":  0.27 / 1_000_000,
        "output": 1.10 / 1_000_000
    },
    "gemini-2.0-flash": {
        "input":  0.10 / 1_000_000,
        "output": 0.40 / 1_000_000
    },
    "gemini-2.5-flash": {
        "input":  0.30 / 1_000_000,
        "output": 2.50 / 1_000_000
    },
    "mistral-small": {
        "input":  0.0,
        "output": 0.0
    }
}

AGENT_BUDGET_RATIOS = {
    "orchestrator": 0.35,
    "logic_agent":  0.30,
    "ui_agent":     0.25,
    "qa_agent":     0.05,
    "context_agent":0.05
}

AGENT_MODELS = {
    "orchestrator": "gemini-2.5-pro",
    "logic_agent":  "deepseek-chat",
    "ui_agent":     "mistral-small",
    "qa_agent":     "gemini-2.5-flash",
    "context_agent":"gemini-2.0-flash"
}
