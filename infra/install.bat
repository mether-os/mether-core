@echo off
title METHER OS — First Time Setup

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      METHER OS — FIRST TIME SETUP        ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Check Node.js ──
echo [CHECK] Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo         Found %%v

:: ── Check Python ──
echo [CHECK] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version') do echo         Found %%v

:: ── Check npm ──
echo [CHECK] npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Comes with Node.js — reinstall Node.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('npm --version') do echo         Found v%%v

:: ── Check pip ──
echo [CHECK] pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARN]  pip not found. Trying python -m pip...
)

echo.
echo  ────────────────────────────────────────────
echo  Installing dependencies...
echo  ────────────────────────────────────────────
echo.

:: ── Frontend ──
echo [1/4] Installing frontend dependencies...
cd /d "%~dp0..\frontend"
call npm install
if errorlevel 1 (
    echo [ERROR] Frontend install failed.
    pause
    exit /b 1
)
echo       Frontend OK.
echo.

:: ── Backend ──
echo [2/4] Installing backend dependencies...
cd /d "%~dp0..\backend"
pip install -e . >nul 2>&1
if errorlevel 1 (
    python -m pip install -e . >nul 2>&1
)
echo       Backend OK.
echo.

:: ── WhatsApp ──
echo [3/4] Installing WhatsApp bridge...
cd /d "%~dp0..\whatsapp"
if exist "package.json" (
    call npm install
    echo       WhatsApp OK.
) else (
    echo       [SKIP] No package.json found.
)
echo.

:: ── Voice ──
echo [4/4] Installing voice pipeline...
cd /d "%~dp0..\voice"
if exist "requirements.txt" (
    pip install -r requirements.txt >nul 2>&1
    echo       Voice OK.
) else (
    echo       [SKIP] No requirements.txt found.
)
echo.

:: ── Create .mether directory ──
echo  ────────────────────────────────────────────
echo  Setting up user data...
echo  ────────────────────────────────────────────
echo.

if not exist "%USERPROFILE%\.mether" (
    mkdir "%USERPROFILE%\.mether"
    echo [METHER] Created %USERPROFILE%\.mether
)

if not exist "%USERPROFILE%\.mether\CLAUDE.md" (
    (
        echo # METHER OS — Operating Manual
        echo.
        echo ## About Me
        echo - Name: [Your Name]
        echo - Timezone: IST ^(UTC+5:30^)
        echo.
        echo ## Preferences
        echo - Communication style: concise and direct
        echo - Always confirm before dangerous actions
        echo.
        echo ## Accounts
        echo - Gmail: [your@gmail.com]
        echo.
        echo ## Notes
        echo - Edit this file to personalize METHER OS.
    ) > "%USERPROFILE%\.mether\CLAUDE.md"
    echo [METHER] Created CLAUDE.md — edit to personalize METHER.
) else (
    echo [METHER] CLAUDE.md already exists.
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     METHER OS — INSTALLATION COMPLETE    ║
echo  ╠══════════════════════════════════════════╣
echo  ║                                          ║
echo  ║  Next steps:                             ║
echo  ║  1. Edit %USERPROFILE%\.mether\CLAUDE.md ║
echo  ║  2. Run infra\start.bat                  ║
echo  ║                                          ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
