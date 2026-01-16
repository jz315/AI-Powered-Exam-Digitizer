@echo off
REM Math Digitizer GPU 启动脚本
REM 使用 .venv 中的 Python 直接运行，避免 uv sync 覆盖 GPU torch
cd /d "%~dp0"
".venv\Scripts\python.exe" main.py
pause
