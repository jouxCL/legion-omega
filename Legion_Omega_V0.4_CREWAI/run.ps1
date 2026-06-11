$PY = Join-Path $PSScriptRoot "..\Legion_Omega_V0.33_ALPHA\venv312\Scripts\python.exe"
Write-Host "[LEGION OMEGA V0.4] Usando: $PY"
& $PY "$PSScriptRoot\main.py"
