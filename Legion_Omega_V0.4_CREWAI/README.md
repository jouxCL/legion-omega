# LEGION OMEGA V0.4 — CrewAI

Generador multi-agente de apps Flutter, reescrito sobre **CrewAI Flows + Crews** (CrewAI ≥ 1.14). Basado en V0.33 ALPHA.

## Qué hay aquí

- `crew/flow.py` — `LegionOmegaFlow`: pipeline `init → plan → build → compile → (fix ↺ compile) → finalize` con `@start` / `@listen` / `@router`.
- `crew/agents.py` — 6 agentes CrewAI: planner, logic, ui, compiler_ops, fixer, **comms**.
- `crew/tasks.py` — fábricas de Tasks (incluye `feature_*_task` con `async_execution=True`).
- `crew/tools/` — `@tool` wrappers sobre `flutter_builder/`, `memory/` y tools exclusivas del CommsAgent (`start_project`, `cancel_project`, `notify_user`).
- `crew/runtime.py` — registro compartido de proceso (Flow + MemoryManager + canal de notificación + cola de eventos).
- `tg_bot/` — Telegram con **un único** handler: cada mensaje entra al CommsAgent (que es un LLM con tools), no hay máquina de estados hardcoded.
- `flutter_builder/`, `memory/` — reusados tal cual de V0.33.
- `prompts/*_backstory.txt` — personalidad de cada agente.

## Instalación

Python 3.12 obligatorio (por CrewAI ≥ 1.14). No contaminar `venv312` de V0.33.

```bash
cd Legion_Omega_V0.4_CREWAI

# Windows (Git Bash / PowerShell)
py -3.12 -m venv venv_v04
source venv_v04/Scripts/activate   # en CMD:  venv_v04\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
```

Copia tu `.env` de V0.33 (ya debería estar presente). Variables requeridas:

```
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
MISTRAL_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_USER_ID=123456789
```

## Arranque

```bash
python main.py
```

En Telegram: abre el chat del bot y escribe cualquier cosa — el **CommsAgent** (Gemini 2.0 Flash) responde. Dile, por ejemplo:

> "quiero una app de notas con tema oscuro, presupuesto 0.5 dólares"

El comms agent llamará `start_project` con los inferidos; el Flow corre en background y los eventos de cada fase (`init`, `plan`, `build`, `compile`, `fix`, `done`) pasan por la cola, son narrados por el LLM y se entregan al usuario. Puedes preguntar en cualquier momento "¿cómo va?" y llamará `get_project_status`.

## Verificación

1. **Smoke LLMs**:
   ```bash
   python -c "from crew.llms import get_llm; print(get_llm('planner').call([{'role':'user','content':'di ping'}]))"
   python -c "from crew.llms import get_llm; print(get_llm('logic').call([{'role':'user','content':'di ping'}]))"
   python -c "from crew.llms import get_llm; print(get_llm('ui').call([{'role':'user','content':'di ping'}]))"
   ```

2. **Flow aislado** (sin Telegram), útil para debug:
   ```bash
   python -c "import asyncio; from crew.runtime import get_runtime; from crew.flow import LegionOmegaFlow; from memory.memory_manager import MemoryManager; \
   rt = get_runtime(); rt.memory = MemoryManager(); rt.flow = LegionOmegaFlow(); \
   asyncio.run(rt.flow.kickoff_async(inputs={'description':'app de notas simple','budget_usd':0.3}))"
   ```

3. **E2E Telegram**: `python main.py`, `/start`, luego pide una app. Criterios de éxito:
   - Respuestas del comms agent variables (reinicia con backstory modificada para confirmar que no son strings fijos).
   - Al menos 3 mensajes proactivos distintos entre fases.
   - `flutter analyze` del proyecto generado termina sin errores en ≤3 intentos.
   - `legion_omega_v04.log` muestra trazas CrewAI (`Agent: … Task: …`) sin `ImportError`.

## Diferencias clave vs V0.33

| Aspecto | V0.33 | V0.4 |
|---|---|---|
| Orquestación | DAG manual + máquina de estados | `crewai.Flow` con `@start`/`@listen`/`@router` |
| Agentes | SDKs directos (google-generativeai, openai, mistralai) | `crewai.Agent` + `crewai.LLM` vía LiteLLM |
| Telegram | ConversationHandler manual | CommsAgent LLM con tools, sin handlers por comando |
| Mensajes al usuario | Strings hardcoded | Redactados por CommsAgent a partir de eventos |
| Parallelismo | `asyncio.gather` manual en TaskDispatcher | `async_execution=True` en Tasks + `asyncio.gather` de Crews |
