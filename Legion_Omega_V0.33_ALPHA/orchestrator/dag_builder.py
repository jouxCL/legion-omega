import uuid
from typing import List, Dict, Any


def _make_task(task_type: str, agent: str, feature: str, layer: str,
               description: str, input_contract: dict, output_contract: str,
               dependencies: List[str], est_input: int = 2000, est_output: int = 1500) -> dict:
    return {
        "task_id": str(uuid.uuid4())[:8],
        "type": task_type,
        "agent": agent,
        "feature": feature,
        "layer": layer,
        "description": description,
        "input_contract": input_contract,
        "output_contract": output_contract,
        "dependencies": dependencies,
        "estimated_input_tokens": est_input,
        "estimated_output_tokens": est_output,
        "status": "pending",
        "output": None,
        "error": None,
        "attempts": 0
    }


def _safe_slug(text: str) -> str:
    """Convert any string to a safe snake_case identifier."""
    import re
    slug = re.sub(r"[^\w\s]", "", str(text).lower())
    slug = re.sub(r"\s+", "_", slug.strip())
    return slug or "item"


def _normalize_plan(plan: dict) -> dict:
    """
    Ensure plan has all required fields. Fill in sensible defaults if Gemini
    returned an incomplete or differently-structured JSON.
    """
    # app_name: required — derive from display name or description
    if not plan.get("app_name"):
        plan["app_name"] = _safe_slug(
            plan.get("app_display_name") or plan.get("name") or "legion_app"
        )

    if not isinstance(plan.get("features"), list):
        plan["features"] = []

    for i, feature in enumerate(plan["features"]):
        if not feature.get("name"):
            feature["name"] = feature.get("feature_name") or f"feature_{i}"
        feature["name"] = _safe_slug(feature["name"])
        feature.setdefault("description", f"Feature {feature['name']}")
        feature.setdefault("entities", [])
        feature.setdefault("use_cases", [])
        feature.setdefault("screens", [feature["name"].capitalize() + "Screen"])

    plan.setdefault("global_theme", {})
    plan.setdefault("navigation_routes", [])
    plan.setdefault("brand_assets", {})
    return plan


def build_dag_from_plan(plan: dict) -> List[dict]:
    """
    Build task DAG from orchestrator plan.
    Tolerant of missing/renamed fields — normalizes before processing.
    """
    plan = _normalize_plan(plan)
    app_name = plan["app_name"]
    tasks = []
    feature_task_ids: Dict[str, Dict[str, List[str]]] = {}

    # --- THEME TASK (no deps) ---
    theme_task = _make_task(
        "ui", "ui_agent", "global", "theme",
        "Generar ThemeData completo con colores de marca, tipografía y estilos globales",
        {"brand_assets": plan.get("brand_assets", {}), "app_name": app_name},
        "archivo lib/core/theme/app_theme.dart con ThemeData completo",
        [], est_input=1500, est_output=1200
    )
    tasks.append(theme_task)

    # --- ROUTER TASK (deps updated after screens are known) ---
    router_task = _make_task(
        "ui", "ui_agent", "global", "router",
        "Generar GoRouter con todas las rutas de la aplicación",
        {"routes": plan.get("navigation_routes", []), "app_name": app_name},
        "archivo lib/core/router/app_router.dart con GoRouter configurado",
        [], est_input=1500, est_output=1000
    )
    tasks.append(router_task)

    for feature in plan.get("features", []):
        fname = feature["name"]
        desc  = feature.get("description", fname)
        feature_task_ids[fname] = {
            "entities": [], "repos": [], "use_cases": [], "cubits": [], "screens": []
        }

        # --- ENTITIES ---
        for entity in feature.get("entities", []):
            t = _make_task(
                "logic", "logic_agent", fname, "entity",
                f"Generar entidad Freezed '{entity}' para el feature '{fname}'",
                {"entity_name": entity, "feature": fname, "description": desc},
                f"archivo lib/features/{fname}/domain/entities/{entity.lower()}.dart",
                [], est_input=1200, est_output=800
            )
            tasks.append(t)
            feature_task_ids[fname]["entities"].append(t["task_id"])

        # --- REPOSITORY INTERFACE ---
        repo_iface_task = _make_task(
            "logic", "logic_agent", fname, "repository_interface",
            f"Generar abstract class del repositorio para '{fname}'",
            {
                "feature": fname,
                "entities": feature.get("entities", []),
                "use_cases": feature.get("use_cases", []),
                "description": desc
            },
            f"archivo lib/features/{fname}/domain/repositories/{fname}_repository.dart",
            feature_task_ids[fname]["entities"], est_input=2000, est_output=600
        )
        tasks.append(repo_iface_task)

        # --- USE CASES ---
        for uc in feature.get("use_cases", []):
            t = _make_task(
                "logic", "logic_agent", fname, "use_case",
                f"Generar use case '{uc}' para el feature '{fname}'",
                {
                    "use_case_name": uc,
                    "feature": fname,
                    "repository_interface": f"{fname}_repository.dart",
                    "entities": feature.get("entities", [])
                },
                f"archivo lib/features/{fname}/domain/use_cases/{uc.lower()}.dart",
                [repo_iface_task["task_id"]], est_input=1800, est_output=700
            )
            tasks.append(t)
            feature_task_ids[fname]["use_cases"].append(t["task_id"])

        # --- REPOSITORY IMPL ---
        repo_impl_task = _make_task(
            "logic", "logic_agent", fname, "repository_impl",
            f"Generar implementación del repositorio para '{fname}' con llamadas HTTP via Dio",
            {
                "feature": fname,
                "entities": feature.get("entities", []),
                "repository_interface": f"{fname}_repository.dart"
            },
            f"archivo lib/features/{fname}/data/repositories/{fname}_repository_impl.dart",
            [repo_iface_task["task_id"]], est_input=2500, est_output=1200
        )
        tasks.append(repo_impl_task)
        feature_task_ids[fname]["repos"].append(repo_impl_task["task_id"])

        # --- CUBIT ---
        cubit_task = _make_task(
            "logic", "logic_agent", fname, "cubit",
            f"Generar Cubit con estados Freezed para el feature '{fname}'",
            {
                "feature": fname,
                "use_cases": feature.get("use_cases", []),
                "entities": feature.get("entities", [])
            },
            f"archivos lib/features/{fname}/presentation/cubit/{fname}_cubit.dart y {fname}_state.dart",
            feature_task_ids[fname]["use_cases"], est_input=2500, est_output=1500
        )
        tasks.append(cubit_task)
        feature_task_ids[fname]["cubits"].append(cubit_task["task_id"])

        # --- SCREENS ---
        for screen in feature.get("screens", []):
            t = _make_task(
                "ui", "ui_agent", fname, "screen",
                f"Generar screen '{screen}' para el feature '{fname}' usando BlocBuilder",
                {
                    "screen_name": screen,
                    "feature": fname,
                    "cubit": f"{fname}_cubit.dart",
                    "entities": feature.get("entities", []),
                    "description": desc
                },
                f"archivo lib/features/{fname}/presentation/screens/{screen.lower()}_screen.dart",
                feature_task_ids[fname]["cubits"] + [theme_task["task_id"]],
                est_input=2500, est_output=2000
            )
            tasks.append(t)
            feature_task_ids[fname]["screens"].append(t["task_id"])

    # --- UPDATE ROUTER DEPS (now we know all screens) ---
    all_screen_ids = []
    for fdata in feature_task_ids.values():
        all_screen_ids.extend(fdata["screens"])
    router_task["dependencies"] = all_screen_ids

    return tasks
