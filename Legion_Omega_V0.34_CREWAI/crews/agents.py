"""CrewAI Agents for LEGION OMEGA V0.34."""
from __future__ import annotations
from crewai import Agent

planner = Agent(
    role="Senior Flutter Architect",
    goal="Produce structured ProjectPlan from user requirements.",
    backstory="Expert software architect for Flutter applications.",
    allow_delegation=False,
    verbose=True,
)

logic_agent = Agent(
    role="Flutter Clean Architecture Engineer",
    goal="Generate domain entities, repositories, use cases, and cubits.",
    backstory="Expert in Clean Architecture, BLoC, and Dart.",
    allow_delegation=False,
    verbose=True,
)

ui_agent = Agent(
    role="Flutter Material3 UI Designer",
    goal="Generate screens and widgets in Dart using Material3.",
    backstory="Expert UI designer specializing in Flutter and Material Design.",
    allow_delegation=False,
    verbose=True,
)

compiler_agent = Agent(
    role="Flutter Build Operator",
    goal="Compile Flutter app and analyze errors.",
    backstory="DevOps engineer specializing in Flutter build cycles.",
    allow_delegation=False,
    verbose=True,
)

fixer_agent = Agent(
    role="Dart Compilation Fixer",
    goal="Fix compilation errors in Dart code.",
    backstory="Expert in debugging and resolving Dart compile-time errors.",
    allow_delegation=False,
    verbose=True,
)

comms_agent = Agent(
    role="Legion Omega Project Assistant",
    goal="Communicate project status and handle user requests.",
    backstory="Friendly assistant managing communications with the user.",
    allow_delegation=False,
    verbose=True,
)
