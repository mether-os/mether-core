@echo off
title METHER OS — Autostart Registration

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   METHER OS — REGISTER AUTOSTART         ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Get the absolute path to start.bat
set "START_BAT=%~dp0..\start.bat"

:: Register with Task Scheduler
echo [METHER] Registering with Windows Task Scheduler...
echo          Task: "METHER OS"
echo          Trigger: On user logon (30s delay)
echo          Action: %START_BAT%
echo.

schtasks /create /tn "METHER OS" /tr "\"%START_BAT%\"" /sc onlogon /delay 0000:30 /f /rl highest

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to register. Try running as Administrator.
    echo         Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       AUTOSTART REGISTERED!              ║
echo  ╠══════════════════════════════════════════╣
echo  ║                                          ║
echo  ║  METHER OS will now start automatically  ║
echo  ║  30 seconds after you log into Windows.  ║
echo  ║                                          ║
echo  ║  To remove autostart, run:               ║
echo  ║  schtasks /delete /tn "METHER OS" /f     ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
