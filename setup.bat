@echo off
python scripts/install_script.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Setup script failed or Python is missing.
    pause
)
