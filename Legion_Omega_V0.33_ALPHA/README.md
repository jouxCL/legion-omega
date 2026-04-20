# LEGION OMEGA V0.33 ALPHA

**Orchestrated Multimodal Engineering by Generative Agents**

Sistema multi-agente que convierte una descripción en texto en una app Flutter completa, coordinada por IA y controlada por presupuesto. Tú describes lo que necesitas en Telegram; el sistema construye la app por ti.

---

## ¿Cómo funciona?

1. Le describes tu necesidad al bot de Telegram
2. (Opcional) Envías un .zip con tu logo y colores de marca
3. Defines un presupuesto máximo en dólares
4. El sistema planifica, genera el código Flutter, compila y te entrega la app lista

---

## Requisitos previos

Antes de instalar, necesitas tener:

- **Python 3.10 o superior** — [python.org](https://www.python.org/downloads/)
- **Flutter** — [flutter.dev](https://flutter.dev/docs/get-started/install)

Para verificar que los tienes, abre tu terminal y ejecuta:
```
python --version
flutter --version
```

---

## Instalación paso a paso

### Paso 1 — Instala las dependencias Python

Abre tu terminal, navega a la carpeta `Legion_Omega_V0.33_ALPHA` y ejecuta:
```
pip install -r requirements.txt
```

### Paso 2 — Configura las claves API

En Windows, copia manualmente el archivo `.env.example`, pégalo en la misma carpeta y renómbralo `.env`.

Luego abre el archivo `.env` con el bloc de notas y llena cada valor (ver sección siguiente).

---

## Cómo obtener cada API key

### Gemini API Key
1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Inicia sesión con tu cuenta Google
3. Haz clic en **"Get API Key"** → **"Create API Key"**
4. Copia la clave y pégala en `GEMINI_API_KEY=` en tu `.env`

### DeepSeek API Key
1. Ve a [platform.deepseek.com](https://platform.deepseek.com)
2. Crea una cuenta y ve a **"API Keys"**
3. Genera una nueva clave y pégala en `DEEPSEEK_API_KEY=`

### Mistral API Key
1. Ve a [console.mistral.ai](https://console.mistral.ai)
2. Crea una cuenta y ve a **"API Keys"**
3. Genera una nueva clave y pégala en `MISTRAL_API_KEY=`

### Telegram Bot Token
1. Abre Telegram y busca **@BotFather**
2. Escribe `/newbot`
3. Sigue las instrucciones: elige un nombre y un username para tu bot
4. BotFather te dará un token. Pégalo en `TELEGRAM_BOT_TOKEN=`

### Tu Telegram User ID
1. En Telegram, busca **@userinfobot**
2. Escríbele `/start`
3. Te responderá con tu ID numérico. Pégalo en `TELEGRAM_ALLOWED_USER_ID=`

---

## Configurar el .env

Tu archivo `.env` final debe verse así (con tus valores reales):

```
GEMINI_API_KEY=AIzaSy...
DEEPSEEK_API_KEY=sk-...
MISTRAL_API_KEY=...
TELEGRAM_BOT_TOKEN=123456789:ABC...
TELEGRAM_ALLOWED_USER_ID=123456789
FLUTTER_PATH=flutter
OUTPUT_DIR=./output
MEMORY_FILE=./memory/project_memory.json
DEFAULT_MAX_BUDGET_USD=0.5
```

> **Nota sobre FLUTTER_PATH:** Si flutter no responde al escribir `flutter` en tu terminal, pon la ruta completa.  
> En Windows sería algo como: `FLUTTER_PATH=C:\flutter\bin\flutter.bat`

---

## Iniciar el sistema

Con el `.env` configurado, ejecuta desde la carpeta del proyecto:

```
python main.py
```

Verás esto en la consola:

```
╔══════════════════════════════════════╗
║   LEGION OMEGA V0.33 ALPHA           ║
║   Orchestrated Multimodal            ║
║   Engineering by Generative Agents   ║
╚══════════════════════════════════════╝

Sistema iniciado. Esperando instrucciones en Telegram…
```

Para detener el sistema: presiona `Ctrl+C`

---

## Comandos de Telegram

| Comando | Qué hace |
|---------|----------|
| `/start` | Saludo e instrucciones de uso |
| `/nuevo` | Inicia un nuevo proyecto de app |
| `/estado` | Muestra el progreso del proyecto actual |
| `/budget` | Muestra el reporte de gastos en tiempo real |
| `/cancelar` | Cancela el proyecto activo |

Durante un proyecto activo puedes escribir mensajes libremente y el agente te responderá en lenguaje natural.

---

## Estructura de costos

El sistema distribuye tu presupuesto automáticamente entre sus agentes:

| Rol | Modelo | % del presupuesto |
|-----|--------|-------------------|
| Orquestador (planificación y DAG) | Gemini 2.5 Pro | 35% |
| Agente de lógica (Clean Arch, BLoC) | DeepSeek Chat | 30% |
| Agente de UI (widgets, screens) | Mistral Small* | 25% |
| Agente QA | Gemini 2.5 Flash | 5% |
| Agente de contexto (Telegram) | Gemini 2.0 Flash | 5% |

*Mistral Small está en plan Experimental gratuito, por lo que su costo real es $0.

---

## ¿Dónde queda la app generada?

Todas las apps se guardan en la carpeta `output/` dentro del proyecto.
Cada app tiene su propio subdirectorio con el nombre del proyecto.

Para abrirla en Android Studio o VS Code: `File → Open → output/nombre_de_tu_app`

---

## Solución de problemas

**"Flutter no encontrado"** → Instala Flutter y verifica que esté en tu PATH, o configura `FLUTTER_PATH` en `.env`

**"Faltan variables de entorno"** → Verifica que tu `.env` existe y tiene todos los valores llenos

**El bot no responde en Telegram** → Verifica que `TELEGRAM_BOT_TOKEN` es correcto y que iniciaste el bot con `/start`

**Error de compilación en la app** → El sistema lo maneja automáticamente con hasta 5 intentos de corrección automática

---

## Arquitectura del sistema

```
Tu mensaje en Telegram
        ↓
   Bot de Telegram
        ↓
  OrchestratorAgent (Gemini 2.5 Pro)
  ├── Analiza la solicitud
  ├── Construye el DAG de tareas
  ├── Distribuye tareas a agentes especializados
  │   ├── LogicAgent (DeepSeek) → entidades, repos, cubits
  │   └── UIAgent (Mistral) → screens, widgets, tema
  ├── Compila el proyecto Flutter
  └── Reporta el resultado vía ContextAgent (Gemini Flash)
```
