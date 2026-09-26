import os
import logging
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class FileWriter:
    def __init__(self, project_root: str, memory: MemoryManager):
        self.project_root = project_root
        self.memory = memory

    def write_dart_file(self, relative_path: str, content: str) -> str:
        """Writes a Dart file to the Flutter project. Returns absolute path."""
        abs_path = os.path.join(self.project_root, relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Wrote: {relative_path}")
        return abs_path

    def write_task_output(self, task: dict) -> str:
        """Writes the Dart file from a completed agent task."""
        output = task.get("output", {})
        filename = output.get("filename", "")
        content = output.get("content", "")
        if not filename or not content:
            raise ValueError(f"Task {task['task_id']} has no valid output to write")
        return self.write_dart_file(filename, content)

    def update_pubspec(self, dependencies: list, dev_dependencies: list = None, assets: list = None):
        """Adds dependencies to pubspec.yaml."""
        pubspec_path = os.path.join(self.project_root, "pubspec.yaml")
        with open(pubspec_path, "r", encoding="utf-8") as f:
            content = f.read()

        dep_block = "\n".join(f"  {dep}" for dep in dependencies)
        if "dependencies:" in content and dep_block:
            content = content.replace(
                "dependencies:\n  flutter:\n    sdk: flutter",
                f"dependencies:\n  flutter:\n    sdk: flutter\n{dep_block}"
            )

        if dev_dependencies:
            dev_block = "\n".join(f"  {dep}" for dep in dev_dependencies)
            if "dev_dependencies:" in content:
                content = content.replace(
                    "dev_dependencies:\n  flutter_test:\n    sdk: flutter",
                    f"dev_dependencies:\n  flutter_test:\n    sdk: flutter\n{dev_block}"
                )

        if assets:
            asset_lines = "\n".join(f"    - {a}" for a in assets)
            if "flutter:" in content and "assets:" not in content:
                content += f"\n  assets:\n{asset_lines}\n"

        with open(pubspec_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Updated pubspec.yaml")
