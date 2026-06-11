@echo off
SET VENV=%~dp0..\Legion_Omega_V0.33_ALPHA\venv312\Scripts\python.exe
SET SCRIPT=%~dp0main.py
echo [LEGION OMEGA V0.4] Iniciando con venv312...
"%VENV%" "%SCRIPT%"
pause
