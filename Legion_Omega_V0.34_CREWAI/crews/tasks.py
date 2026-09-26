"""CrewAI Tasks for LEGION OMEGA V0.34."""
from __future__ import annotations
from crewai import Task
from crews.agents import (
    planner, logic_agent, ui_agent, compiler_agent, fixer_agent, comms_agent
)

plan_project_task = Task(
    description="Analyze description '{description}' with budget ${budget_usd} and produce a ProjectPlan JSON.",
    expected_output="JSON string of ProjectPlan.",
    agent=planner,
)

init_flutter_project_task = Task(
    description="Initialize Flutter project scaffold.",
    expected_output="Path to initialized project.",
    agent=compiler_agent,
)

generate_theme_task = Task(
    description="Generate Material3 theme data.",
    expected_output="Theme code file.",
    agent=ui_agent,
)

generate_router_task = Task(
    description="Generate go_router navigation configuration.",
    expected_output="Router code file.",
    agent=ui_agent,
)

compile_project_task = Task(
    description="Run full build cycle and analyze Flutter project.",
    expected_output="Build result JSON.",
    agent=compiler_agent,
)

fix_compile_errors_task = Task(
    description="Fix compilation errors: {errors}",
    expected_output="Fix summary.",
    agent=fixer_agent,
)

report_status_task = Task(
    description="Report current project state to user.",
    expected_output="Status message string.",
    agent=comms_agent,
)
