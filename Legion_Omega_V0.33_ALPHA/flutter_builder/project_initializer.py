import asyncio
import os
import sys
import logging
import shutil
from flutter_builder.compiler import FlutterCompiler

logger = logging.getLogger(__name__)
_IS_WINDOWS = sys.platform == "win32"

BASE_DEPENDENCIES = [
    "  flutter_bloc: ^8.1.5",
    "  bloc: ^8.1.4",
    "  equatable: ^2.0.5",
    "  freezed_annotation: ^2.4.1",
    "  json_annotation: ^4.9.0",
    "  dartz: ^0.10.1",
    "  get_it: ^7.7.0",
    "  injectable: ^2.4.2",
    "  go_router: ^14.2.0",
    "  dio: ^5.5.0",
    "  cached_network_image: ^3.3.1",
    "  hive_flutter: ^1.1.0",
]

DEV_DEPENDENCIES = [
    "  build_runner: ^2.4.11",
    "  freezed: ^2.5.2",
    "  json_serializable: ^6.8.0",
    "  injectable_generator: ^2.6.1",
]

MAIN_DART = '''import 'package:flutter/material.dart';
import 'package:get_it/get_it.dart';
import 'core/router/app_router.dart';
import 'core/di/injection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  configureDependencies();
  runApp(const App());
}

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Legion Omega App',
      routerConfig: GetIt.I<AppRouter>().config(),
    );
  }
}
'''

CLEAN_ARCH_DIRS = [
    "lib/core/di",
    "lib/core/error",
    "lib/core/network",
    "lib/core/router",
    "lib/core/theme",
    "lib/core/utils",
]


class ProjectInitializer:
    def __init__(self, output_dir: str, flutter_bin: str = None):
        self.output_dir = output_dir
        self.flutter = flutter_bin or os.getenv("FLUTTER_PATH", "flutter")

    def _resolve_flutter(self) -> str:
        """Return the best flutter executable path for this OS."""
        found = shutil.which(self.flutter)
        if found:
            return found
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
        return self.flutter

    async def _run_flutter(self, *args, cwd: str) -> tuple:
        """Run a flutter command, using shell on Windows for .bat support."""
        flutter_exe = self._resolve_flutter()
        if _IS_WINDOWS:
            cmd_str = f'"{flutter_exe}" {" ".join(str(a) for a in args)}'
            logger.info(f"Flutter (shell): {cmd_str}")
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                flutter_exe, *args,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")

    async def create(self, app_name: str, org: str = "com.legomega") -> str:
        """Creates a new Flutter project. Returns the project path."""
        project_path = os.path.join(self.output_dir, app_name)

        if os.path.exists(project_path):
            logger.warning(f"Project already exists at {project_path}, skipping flutter create")
        else:
            os.makedirs(self.output_dir, exist_ok=True)
            code, out, err = await self._run_flutter(
                "create", f"--org={org}", "--platforms=android,ios", app_name,
                cwd=self.output_dir
            )
            if code != 0:
                raise RuntimeError(f"flutter create failed:\n{err[:600]}")
            logger.info(f"Flutter project created: {project_path}")

        # Overwrite main.dart
        main_path = os.path.join(project_path, "lib", "main.dart")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(MAIN_DART)

        # Create Clean Architecture directory structure
        for d in CLEAN_ARCH_DIRS:
            os.makedirs(os.path.join(project_path, d), exist_ok=True)

        # Update pubspec.yaml
        await self._update_pubspec(project_path)

        # Run pub get
        code, out, err = await self._run_flutter("pub", "get", cwd=project_path)
        if code != 0:
            logger.warning(f"pub get returned non-zero: {err[:300]}")

        return project_path

    async def _update_pubspec(self, project_path: str):
        pubspec_path = os.path.join(project_path, "pubspec.yaml")
        with open(pubspec_path, "r", encoding="utf-8") as f:
            content = f.read()

        dep_block = "\n".join(BASE_DEPENDENCIES)
        content = content.replace(
            "dependencies:\n  flutter:\n    sdk: flutter",
            f"dependencies:\n  flutter:\n    sdk: flutter\n{dep_block}"
        )

        dev_block = "\n".join(DEV_DEPENDENCIES)
        content = content.replace(
            "dev_dependencies:\n  flutter_test:\n    sdk: flutter",
            f"dev_dependencies:\n  flutter_test:\n    sdk: flutter\n{dev_block}"
        )

        with open(pubspec_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("pubspec.yaml updated with Clean Architecture dependencies")
