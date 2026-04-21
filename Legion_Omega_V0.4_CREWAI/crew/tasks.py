"""Task factories for each Flow phase."""
from __future__ import annotations
from crewai import Task, Agent


def plan_task(agent: Agent) -> Task:
    return Task(
        description=(
            "El usuario describe una app Flutter que quiere crear:\n"
            "\"\"\"{description}\"\"\"\n\n"
            "Presupuesto máximo: ${budget_usd}.\n"
            "Produce un plan JSON VÁLIDO (solo JSON, sin markdown ni prosa) con este esquema:\n"
            "{{\n"
            '  "app_name": "snake_case",\n'
            '  "app_display_name": "Nombre Humano",\n'
            '  "features": [{{"name": "...", "description": "...", "entities": [...], '
            '"use_cases": [...], "screens": [...]}}],\n'
            '  "global_theme": {{"primary_color": "#RRGGBB", ...}},\n'
            '  "navigation_routes": ["/home", ...]\n'
            "}}\n"
            "Máximo 3 features. Sé específico y realista dentro del presupuesto."
        ),
        expected_output="Un único objeto JSON con el esquema ProjectPlan, sin texto alrededor.",
        agent=agent,
    )


def feature_logic_task(agent: Agent, feature_name: str) -> Task:
    return Task(
        description=(
            f"Genera y ESCRIBE en disco (con la tool write_dart_file) el código de la capa "
            f"logic para la feature '{feature_name}':\n"
            f"- entidades (lib/features/{feature_name}/domain/entities/)\n"
            f"- repositorios abstractos + impl (lib/features/{feature_name}/domain/repositories/, "
            f"lib/features/{feature_name}/data/repositories/)\n"
            f"- use cases (lib/features/{feature_name}/domain/usecases/)\n"
            f"- cubit/bloc + state (lib/features/{feature_name}/presentation/bloc/)\n"
            "Usa freezed y equatable donde aplique. Código Dart compilable."
        ),
        expected_output="Lista de paths relativos de archivos escritos.",
        agent=agent,
        async_execution=True,
    )


def feature_ui_task(agent: Agent, feature_name: str) -> Task:
    return Task(
        description=(
            f"Genera y ESCRIBE en disco las pantallas Material3 y widgets para la feature "
            f"'{feature_name}' bajo lib/features/{feature_name}/presentation/. Integra con el "
            f"cubit/bloc que el logic agent está creando en paralelo (asume nombres estándar "
            f"<Feature>Cubit / <Feature>State). Registra rutas en lib/core/router/app_router.dart "
            "usando go_router."
        ),
        expected_output="Lista de paths relativos de archivos escritos.",
        agent=agent,
        async_execution=True,
    )


def compile_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Invoca la tool run_flutter_compile y devuelve su resultado JSON tal cual. "
            "No inventes datos."
        ),
        expected_output="JSON crudo con keys success/errors/warnings.",
        agent=agent,
    )


def fix_task(agent: Agent) -> Task:
    return Task(
        description=(
            "La última compilación falló. Errores:\n{errors}\n\n"
            "Para cada error: abre el archivo con read_project_file, identifica la causa y "
            "escribe la versión corregida con write_dart_file. No reescribas archivos sanos."
        ),
        expected_output="Lista breve de archivos corregidos.",
        agent=agent,
    )


def comms_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Mensaje del usuario: \"{user_message}\"\n"
            "Historial reciente (último turno primero): {history}\n"
            "Snapshot de proyecto: {status}\n\n"
            "Responde al usuario en español, de forma natural y breve. Si pide crear una app, "
            "llama start_project. Si pregunta por progreso, llama get_project_status o "
            "get_last_events. Si pide cancelar, llama cancel_project. Responde SOLO con el "
            "texto final para el usuario (sin JSON, sin markdown innecesario)."
        ),
        expected_output="Un mensaje de chat en español dirigido al usuario.",
        agent=agent,
    )
