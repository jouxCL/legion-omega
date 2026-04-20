import os
import sys
import logging
import warnings
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows encoding for Unicode characters
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Suppress google.generativeai deprecation warning (still works, just deprecated)
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("legion_omega.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("main")

# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)          # HTTP requests (getUpdates spam)
logging.getLogger("telegram.ext.Updater").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

BANNER = """
╔══════════════════════════════════════╗
║   LEGION OMEGA V0.33 ALPHA           ║
║   Orchestrated Multimodal            ║
║   Engineering by Generative Agents   ║
╚══════════════════════════════════════╝
"""

REQUIRED_ENV_VARS = [
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_USER_ID",
]


def check_env_vars():
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        print(f"❌ Faltan variables de entorno: {', '.join(missing)}")
        print("   Copia .env.example a .env y llena los valores.")
        sys.exit(1)
    print("✅ Variables de entorno OK")


def check_flutter():
    import shutil
    flutter_bin = os.getenv("FLUTTER_PATH", "flutter")
    flutter_exe = shutil.which(flutter_bin)

    if flutter_exe:
        print(f"✅ Flutter detectado en: {flutter_exe}")
        return

    try:
        result = subprocess.run(
            f"{flutter_bin} --version",
            capture_output=True, text=True, timeout=30, shell=True
        )
        if result.returncode == 0 or result.stdout:
            version_line = (result.stdout.splitlines()[0] if result.stdout else "detectado").strip()
            print(f"✅ Flutter: {version_line}")
        else:
            print(f"⚠️  Flutter ejecutado pero con stderr: {result.stderr[:100]}")
            print("   Continuando de todas formas...")
    except FileNotFoundError:
        print("❌ Flutter no encontrado. Instálalo desde https://flutter.dev/docs/get-started/install")
        print("   Luego configura FLUTTER_PATH en tu .env si flutter no está en el PATH.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("⚠️  Flutter tardó demasiado. Continuando de todas formas...")
    except Exception as e:
        print(f"⚠️  Error checking Flutter: {e}. Continuando...")


def init_memory():
    from memory.memory_manager import MemoryManager
    memory = MemoryManager()
    mem = memory.get_memory()
    status = mem.get("project", {}).get("status", "idle")
    if status not in ("idle", "done", "cancelled", "compilation_failed"):
        print(f"⚠️  Proyecto previo detectado con estado: '{status}'")
        print("   Usa /estado en Telegram para ver el progreso o /cancelar para reiniciar.")
    else:
        print("✅ Memoria del proyecto OK")


def check_single_instance():
    """Prevent multiple bot instances from running simultaneously."""
    lock_file = Path("legion_omega.lock")
    stale_threshold = 30  # seconds

    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                content = f.read().strip()
                if ":" in content:
                    stored_pid, stored_time = content.split(":")
                    stored_time = float(stored_time)
                    current_time = time.time()
                    elapsed = current_time - stored_time

                    if elapsed < stale_threshold:
                        print(f"❌ Otra instancia de LEGION OMEGA ya está corriendo (PID: {stored_pid})")
                        print("   Solo una instancia puede hacer polling del bot token.")
                        print("   Asegúrate de que solo un proceso 'python main.py' esté activo.")
                        sys.exit(1)
        except Exception as e:
            logger.warning(f"Error reading lock file: {e}. Overwriting...")

    # Create or overwrite lock file with current PID and timestamp
    pid = os.getpid()
    timestamp = time.time()
    with open(lock_file, "w") as f:
        f.write(f"{pid}:{timestamp}")
    logger.info(f"Lock file created: {lock_file} (PID: {pid})")
    return lock_file


def cleanup_lock_file(lock_file: Path):
    """Delete the lock file on exit."""
    try:
        if lock_file.exists():
            lock_file.unlink()
            logger.info("Lock file deleted")
    except Exception as e:
        logger.warning(f"Could not delete lock file: {e}")


def main():
    print(BANNER)
    check_env_vars()
    check_flutter()
    init_memory()
    lock_file = check_single_instance()

    print("\nSistema iniciado. Esperando instrucciones en Telegram…\n")

    from tg_bot.bot import run_bot
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n\nSistema detenido manualmente. ¡Hasta pronto!")
        cleanup_lock_file(lock_file)
        sys.exit(0)
    finally:
        cleanup_lock_file(lock_file)


if __name__ == "__main__":
    main()
