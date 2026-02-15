@echo off
setlocal
title Math Digitizer Launcher

echo ===================================================
echo       Math Digitizer - One-Click Launcher
echo ===================================================
echo.

:: 1. Start Backend Server
echo [1/3] Starting Backend Server (uv run server.py)...
start "Math Digitizer Backend" cmd /k "uv run server.py"

:: 2. Start Frontend Server
echo [2/3] Starting Frontend Client (npm run dev)...
cd frontend
start "Math Digitizer Frontend" cmd /k "npm run dev"
cd ..

:: 3. Open Browser
echo [3/3] Waiting for services to start...
timeout /t 4 >nul
echo Opening http://localhost:5173 ...
start http://localhost:5173

echo.
echo ===================================================
echo    System is running! 
echo    - Backend: http://127.0.0.1:8000
echo    - Frontend: http://localhost:5173
echo.
echo    Close the popped-up command windows to stop.
echo ===================================================
pause
