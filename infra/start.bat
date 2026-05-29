@echo off
title METHER OS

:: Deactivate any active virtualenv to avoid dependency conflicts
if defined VIRTUAL_ENV (
    echo [METHER] Active virtual environment detected. Deactivating...
    call deactivate 2>nul
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║          METHER OS — STARTING            ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Start LLM proxy
echo [METHER] Starting LLM Proxy on :8082...
start "METHER-LLM" cmd /k "cd /d %~dp0..\..\free-claude-code && uv run uvicorn server:app --host 0.0.0.0 --port 8082"

:: Wait for LLM proxy to initialize
timeout /t 3 /nobreak > nul

:: Start backend
echo [METHER] Starting Backend on :8000...
start "METHER-BACKEND" cmd /k "cd /d %~dp0..\backend && uvicorn src.mether.main:app --host 0.0.0.0 --port 8000"

:: Wait for backend to initialize
timeout /t 2 /nobreak > nul

:: Start WhatsApp sidecar
echo [METHER] Starting WhatsApp Bridge on :3001...
start "METHER-WHATSAPP" cmd /k "cd /d %~dp0..\whatsapp && node src/index.js"

:: Start voice sidecar
echo [METHER] Starting Voice Pipeline...
start "METHER-VOICE" cmd /k "cd /d %~dp0..\voice && python src/main.py"

:: Wait for services to stabilize
timeout /t 2 /nobreak > nul

:: Start frontend dev server
echo [METHER] Starting Frontend on :5173...
start "METHER-FRONTEND" cmd /k "cd /d %~dp0..\frontend && npm run dev"

:: Wait for Vite to start
timeout /t 3 /nobreak > nul

:: Open dashboard in browser
start http://localhost:5173

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║        METHER OS — ALL SERVICES UP       ║
echo  ╠══════════════════════════════════════════╣
echo  ║  Dashboard:  http://localhost:5173       ║
echo  ║  Backend:    http://localhost:8000       ║
echo  ║  LLM Proxy:  http://localhost:8082       ║
echo  ║  WhatsApp:   http://localhost:3001       ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Press any key to keep this window open...
pause > nul
