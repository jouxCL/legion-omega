import sys
from pathlib import Path

ROOT_V04 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.4_CREWAI"
ROOT_V033 = Path(__file__).resolve().parent.parent / "Legion_Omega_V0.33_ALPHA"

if str(ROOT_V04) not in sys.path:
    sys.path.insert(0, str(ROOT_V04))
