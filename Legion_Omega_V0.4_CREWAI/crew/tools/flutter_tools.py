"""Flutter-side tools exposed to CrewAI agents.

Thin wrappers around flutter_builder/* so the LLM can init a project, write
dart files, and trigger compilation. Each tool returns JSON-serializable
strings so the agent can reason over results.
"""
from __future__ import annotations
import asyncio
import json
import os
from crewai.tools import tool
from crew.runtime import get_runtime
from flutter_builder.project_initializer import ProjectInitializer
from flutter_builder.compiler import FlutterCompiler
from flutter_builder.file_writer import FileWriter


def _run(coro):
    """Execute a coroutine from a sync @tool callback."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()
    return loop.run_until_complete(coro)


@tool("init_flutter_project")
def init_flutter_project(app_name: str, output_dir: str = "./output") -> str:
    """Create a new Flutter project scaffold with Clean Architecture + BLoC deps.

    Args:
        app_name: snake_case project name (e.g. 'notes_app').
        output_dir: directory where the project will be created.

    Returns: absolute path to the created project, or an error message.
    """
    runtime = get_runtime()
    try:
        initializer = ProjectInitializer(output_dir)
        path = _run(initializer.create(app_name))
        if runtime.state is not None:
            runtime.state.project_path = path
        return json.dumps({"success": True, "project_path": path})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool("write_dart_file")
def write_dart_file(relative_path: str, content: str) -> str:
    """Write a .dart file under the current Flutter project's lib/ directory.

    Args:
        relative_path: path under lib/ (e.g. 'features/notes/presentation/notes_page.dart').
        content: full source of the Dart file.
    """
    runtime = get_runtime()
    if runtime.state is None or not runtime.state.project_path:
        return json.dumps({"success": False, "error": "No active project"})
    try:
        writer = FileWriter(runtime.state.project_path, runtime.memory)
        abs_path = writer.write_dart_file(relative_path, content)
        return json.dumps({"success": True, "path": abs_path})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool("run_flutter_compile")
def run_flutter_compile() -> str:
    """Run `flutter pub get` + `build_runner` + `flutter analyze` + `flutter build apk --debug` on the current project.

    Returns JSON: {"success": bool, "errors": [...], "warnings": [...]}
    """
    runtime = get_runtime()
    if runtime.state is None or not runtime.state.project_path:
        return json.dumps({"success": False, "error": "No active project"})
    try:
        compiler = FlutterCompiler(runtime.state.project_path)
        result = _run(compiler.full_build_cycle())
        if runtime.state is not None:
            runtime.state.last_errors = [e.get("message", str(e)) for e in result.get("errors", [])][:20]
        return json.dumps(result)[:4000]
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@tool("read_project_file")
def read_project_file(relative_path: str) -> str:
    """Read a file from the active Flutter project (relative to project root)."""
    runtime = get_runtime()
    if runtime.state is None or not runtime.state.project_path:
        return json.dumps({"success": False, "error": "No active project"})
    abs_path = os.path.join(runtime.state.project_path, relative_path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return f.read()[:8000]
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
