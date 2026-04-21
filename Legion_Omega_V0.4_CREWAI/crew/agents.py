"""CrewAI agents for LEGION OMEGA V0.4.

Six roles, each backed by a provider-specific LLM via LiteLLM. Backstories
are loaded from `prompts/*.txt` so they can be tweaked without code changes.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent
from crew.llms import get_llm
from crew.tools.flutter_tools import (
    init_flutter_project, write_dart_file, run_flutter_compile, read_project_file,
)
from crew.tools.memory_tools import get_project_status, get_last_events, list_artifacts
from crew.tools.comms_tools import start_project, cancel_project, notify_user

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _backstory(name: str) -> str:
    path = PROMPTS_DIR / f"{name}_backstory.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_planner() -> Agent:
    return Agent(
        role="Senior Flutter Architect",
        goal=(
            "Produce a well-structured ProjectPlan JSON (features, entities, use_cases, "
            "screens, global_theme, navigation_routes) from a free-form user description."
        ),
        backstory=_backstory("planner"),
        llm=get_llm("planner"),
        allow_delegation=False,
        verbose=True,
    )


def build_logic_agent() -> Agent:
    return Agent(
        role="Flutter BLoC / Clean Architecture Engineer",
        goal=(
            "Generate domain entities, repositories, use cases and cubits/blocs in Dart "
            "following Clean Architecture. Produce valid Dart code only."
        ),
        backstory=_backstory("logic"),
        llm=get_llm("logic"),
        tools=[write_dart_file, read_project_file],
        allow_delegation=False,
        verbose=True,
    )


def build_ui_agent() -> Agent:
    return Agent(
        role="Flutter Material3 UI Designer",
        goal=(
            "Generate screens, widgets, themes and router configuration in Dart using "
            "Material3. Keep files idiomatic and compile-clean."
        ),
        backstory=_backstory("ui"),
        llm=get_llm("ui"),
        tools=[write_dart_file, read_project_file],
        allow_delegation=False,
        verbose=True,
    )


def build_compiler_ops() -> Agent:
    return Agent(
        role="Flutter Build Operator",
        goal="Run the full Flutter build cycle and report structured errors/warnings.",
        backstory=_backstory("compiler_ops"),
        llm=get_llm("compiler_ops"),
        tools=[run_flutter_compile, read_project_file, list_artifacts],
        allow_delegation=False,
        verbose=True,
    )


def build_fixer() -> Agent:
    return Agent(
        role="Dart Compilation Fixer",
        goal=(
            "Given compilation errors, open the failing files, identify root cause, and "
            "write corrected Dart code back to disk."
        ),
        backstory=_backstory("fixer"),
        llm=get_llm("fixer"),
        tools=[read_project_file, write_dart_file, list_artifacts],
        allow_delegation=False,
        verbose=True,
    )


def build_comms() -> Agent:
    return Agent(
        role="Legion Omega Project Assistant",
        goal=(
            "Hold a natural conversation with the user in Spanish. Understand intent, "
            "call the right tool (start_project, cancel_project, get_project_status, "
            "get_last_events, list_artifacts), and narrate progress warmly without "
            "leaking technical jargon."
        ),
        backstory=_backstory("comms"),
        llm=get_llm("comms"),
        tools=[
            start_project, cancel_project, notify_user,
            get_project_status, get_last_events, list_artifacts,
        ],
        allow_delegation=False,
        verbose=True,
    )
