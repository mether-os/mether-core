@echo off
echo.
echo  [METHER] Stopping all services...
echo.

:: Kill by window title
taskkill /FI "WindowTitle eq METHER-LLM*" /F >nul 2>&1
taskkill /FI "WindowTitle eq METHER-BACKEND*" /F >nul 2>&1
taskkill /FI "WindowTitle eq METHER-WHATSAPP*" /F >nul 2>&1
taskkill /FI "WindowTitle eq METHER-VOICE*" /F >nul 2>&1
taskkill /FI "WindowTitle eq METHER-FRONTEND*" /F >nul 2>&1

:: Also kill by known port bindings as fallback
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8082.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3001.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1

echo  [METHER] All services stopped.
echo.
pause
