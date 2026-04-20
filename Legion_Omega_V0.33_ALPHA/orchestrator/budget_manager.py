from orchestrator.costs import COSTS, AGENT_BUDGET_RATIOS, AGENT_MODELS


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in COSTS:
        raise ValueError(f"Unknown model: {model}")
    c = COSTS[model]
    if model == "gemini-2.5-pro":
        threshold = c["tier_threshold"]
        if input_tokens <= threshold:
            input_cost = input_tokens * c["input_tier1"]
        else:
            input_cost = threshold * c["input_tier1"] + (input_tokens - threshold) * c["input_tier2"]
        if input_tokens <= threshold:
            output_cost = output_tokens * c["output_tier1"]
        else:
            output_cost = output_tokens * c["output_tier2"]
    elif "input" in c:
        input_cost = input_tokens * c["input"]
        output_cost = output_tokens * c["output"]
    else:
        input_cost = 0.0
        output_cost = 0.0
    return input_cost + output_cost


def can_afford(agent: str, estimated_input: int, estimated_output: int) -> bool:
    memory = MemoryManager()
    remaining = memory.get_remaining_budget()
    model = AGENT_MODELS.get(agent, "gemini-2.0-flash")
    cost = calculate_cost(model, estimated_input, estimated_output)
    return remaining >= cost


def allocate_budget_for_project(total_usd: float) -> dict:
    allocation = {}
    for agent, ratio in AGENT_BUDGET_RATIOS.items():
        budget = total_usd * ratio
        model = AGENT_MODELS[agent]
        c = COSTS[model]
        # Estimate tokens affordable (assume 1:3 input:output ratio)
        if model == "gemini-2.5-pro":
            per_token = c["input_tier1"] + 3 * c["output_tier1"]
        elif "input" in c:
            per_token = c["input"] + 3 * c["output"]
        else:
            per_token = 0.000001
        approx_input = int(budget / per_token) if per_token > 0 else 999_999_999
        allocation[agent] = {
            "model": model,
            "budget_usd": round(budget, 4),
            "approx_input_tokens": approx_input,
            "approx_output_tokens": approx_input * 3
        }
    allocation["total_usd"] = total_usd
    return allocation


def get_budget_report(memory: dict) -> str:
    usage = memory.get("token_usage", {})
    total_cost = usage.get("total_cost_usd", 0.0)
    remaining = memory.get("project", {}).get("budget_remaining_usd", 0.0)
    budget = memory.get("project", {}).get("budget_usd", 0.0)
    lines = [f"*Reporte de Presupuesto*\n"]
    lines.append(f"Presupuesto total: ${budget:.4f}")
    lines.append(f"Gastado: ${total_cost:.4f}")
    lines.append(f"Restante: ${remaining:.4f}")
    lines.append(f"\nDesglose por agente:")
    for agent in ["orchestrator", "logic_agent", "ui_agent", "qa_agent", "context_agent"]:
        data = usage.get(agent, {})
        cost = data.get("cost_usd", 0.0)
        inp = data.get("input", 0)
        out = data.get("output", 0)
        lines.append(f"  {agent}: ${cost:.4f} ({inp}↑ {out}↓ tokens)")
    return "\n".join(lines)
