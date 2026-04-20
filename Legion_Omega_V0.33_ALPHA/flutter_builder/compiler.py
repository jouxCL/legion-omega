import asyncio
import logging
import re
import os
import sys
import shutil
from typing import List

logger = logging.getLogger(__name__)

ERROR_PATTERN = re.compile(
    r"(?P<file>[^\s:]+\.dart):(?P<line>\d+):(?P<col>\d+): (?P<type>error|warning|info): (?P<message>.+)"
)

_IS_WINDOWS = sys.platform == "win32"


class FlutterCompiler:
    def __init__(self, project_path: str, flutter_bin: str = None):
        self.project_path = project_path
        self.flutter = flutter_bin or os.getenv("FLUTTER_PATH", "flutter")

    def _resolve_flutter(self) -> str:
        """Return the best flutter executable path available."""
        # 1. Try shutil.which (works if flutter/flutter.bat is in PATH)
        found = shutil.which(self.flutter)
        if found:
            return found
        # 2. On Windows try common install locations
        if _IS_WINDOWS:
            candidates = [
                r"C:\Users\juans\develop\flutter\bin\flutter.bat",
                r"C:\flutter\bin\flutter.bat",
                r"C:\src\flutter\bin\flutter.bat",
                os.path.expanduser(r"~\develop\flutter\bin\flutter.bat"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
        return self.flutter  # fall back to raw name; will fail with clear error

    async def _run(self, *args) -> tuple:
        flutter_exe = self._resolve_flutter()
        # On Windows .bat files must run through cmd.exe (shell=True)
        if _IS_WINDOWS:
            cmd_str = f'"{flutter_exe}" {" ".join(args)}'
            logger.info(f"Running (shell): {cmd_str}")
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            cmd = [flutter_exe] + list(args)
            logger.info(f"Running: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def pub_get(self) -> tuple:
        return await self._run("pub", "get")

    async def analyze(self) -> List[dict]:
        code, stdout, stderr = await self._run("analyze", "--no-pub")
        combined = stdout + stderr
        return self._parse_errors(combined)

    async def build_apk_debug(self) -> tuple:
        return await self._run("build", "apk", "--debug", "--no-pub")

    async def run_build_runner(self) -> tuple:
        return await self._run("pub", "run", "build_runner", "build", "--delete-conflicting-outputs")

    def _parse_errors(self, output: str) -> List[dict]:
        errors = []
        for line in output.splitlines():
            m = ERROR_PATTERN.search(line)
            if m:
                err_type = m.group("type")
                errors.append({
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "col": int(m.group("col")),
                    "error_type": "compile_error" if err_type == "error" else "analyze_warning",
                    "message": m.group("message").strip(),
                    "context_files": []
                })
        return errors

    async def full_build_cycle(self) -> dict:
        """Run pub get → build_runner → analyze → build apk. Returns structured result."""
        result = {"success": False, "errors": [], "warnings": [], "stdout": ""}

        code, out, err = await self.pub_get()
        if code != 0:
            result["errors"].append({"file": "pubspec.yaml", "line": 0, "col": 0,
                                     "error_type": "pub_get_error", "message": err[:500], "context_files": []})
            return result

        await self.run_build_runner()

        analyze_errors = await self.analyze()
        compile_errors = [e for e in analyze_errors if e["error_type"] == "compile_error"]
        warnings = [e for e in analyze_errors if e["error_type"] != "compile_error"]
        result["warnings"] = warnings

        if compile_errors:
            result["errors"] = compile_errors
            return result

        code, out, err = await self.build_apk_debug()
        result["stdout"] = out
        if code != 0:
            build_errors = self._parse_errors(out + err)
            if not build_errors:
                build_errors = [{"file": "build", "line": 0, "col": 0,
                                 "error_type": "build_error", "message": (out + err)[:500], "context_files": []}]
            result["errors"] = build_errors
        else:
            result["success"] = True
            logger.info("Build successful!")

        return result
