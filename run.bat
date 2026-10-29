@echo off
title AI Dubbing Studio
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Khoi dong AI Dubbing Studio trong moi truong ao .venv (CUDA 12.4)...
    ".venv\Scripts\python.exe" main.py
) else (
    echo [INFO] Khoi dong bang Python he thong...
    python main.py
)
pause
