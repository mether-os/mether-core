# ═══════════════════════════════════════════════════════════════
#   METHER OS — PowerShell Advanced Launcher
#   Features: health checks, port verification, status table,
#   auto-browser, crash monitoring, graceful shutdown.
# ═══════════════════════════════════════════════════════════════

param(
    [switch]$Stop,
    [switch]$Status
)

$ErrorActionPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
$LlmDir = Join-Path (Split-Path -Parent $RootDir) "free-claude-code"

# ── Service definitions ──
$Services = @(
    @{ Name = "LLM Proxy";  Port = 8082; Dir = $LlmDir;                    Cmd = "uv run uvicorn server:app --host 0.0.0.0 --port 8082";           Title = "METHER-LLM" },
    @{ Name = "Backend";     Port = 8000; Dir = "$RootDir\backend";          Cmd = "uvicorn src.mether.main:app --host 0.0.0.0 --port 8000";         Title = "METHER-BACKEND" },
    @{ Name = "WhatsApp";    Port = 3001; Dir = "$RootDir\whatsapp";         Cmd = "node src/index.js";                                              Title = "METHER-WHATSAPP" },
    @{ Name = "Voice";       Port = 0;    Dir = "$RootDir\voice";            Cmd = "python src/main.py";                                             Title = "METHER-VOICE" },
    @{ Name = "Frontend";    Port = 5173; Dir = "$RootDir\frontend";         Cmd = "npm run dev";                                                    Title = "METHER-FRONTEND" }
)

# ── Helper: Check if port is in use ──
function Test-Port {
    param([int]$Port)
    if ($Port -eq 0) { return $false }
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen 2>$null
    return ($null -ne $conn)
}

# ── Helper: Print status table ──
function Show-Status {
    Write-Host ""
    Write-Host "  ╔═══════════════╦════════╦═══════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   SERVICE     ║  PORT  ║    STATUS     ║" -ForegroundColor Cyan
    Write-Host "  ╠═══════════════╬════════╬═══════════════╣" -ForegroundColor Cyan

    foreach ($svc in $Services) {
        $name = $svc.Name.PadRight(13)
        $port = if ($svc.Port -eq 0) { "  --  " } else { $svc.Port.ToString().PadLeft(4).PadRight(6) }

        if ($svc.Port -eq 0) {
            # Voice has no port — check if process window exists
            $proc = Get-Process | Where-Object { $_.MainWindowTitle -like "$($svc.Title)*" }
            if ($proc) {
                $status = "  ONLINE  " 
                $color = "Green"
            } else {
                $status = "  OFFLINE "
                $color = "Red"
            }
        } else {
            if (Test-Port $svc.Port) {
                $status = "  ONLINE  "
                $color = "Green"
            } else {
                $status = "  OFFLINE "
                $color = "Red"
            }
        }

        $dot = if ($color -eq "Green") { [char]0x25CF } else { [char]0x25CB }
        Write-Host "  ║ $name ║ $port ║ $dot$status ║" -ForegroundColor $color
    }

    Write-Host "  ╚═══════════════╩════════╩═══════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# ── STOP MODE ──
if ($Stop) {
    Write-Host ""
    Write-Host "  [METHER] Stopping all services..." -ForegroundColor Yellow
    
    foreach ($svc in $Services) {
        taskkill /FI "WindowTitle eq $($svc.Title)*" /F 2>$null | Out-Null
    }

    # Port-based fallback
    foreach ($svc in $Services) {
        if ($svc.Port -gt 0) {
            $conn = Get-NetTCPConnection -LocalPort $svc.Port -State Listen 2>$null
            if ($conn) {
                Stop-Process -Id $conn.OwningProcess -Force 2>$null
            }
        }
    }

    Write-Host "  [METHER] All services stopped." -ForegroundColor Green
    Write-Host ""
    exit 0
}

# ── STATUS MODE ──
if ($Status) {
    Show-Status
    exit 0
}

# ── START MODE ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║          METHER OS — LAUNCHING           ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$StartedPids = @()

foreach ($svc in $Services) {
    # Skip if directory doesn't exist
    if (-not (Test-Path $svc.Dir)) {
        Write-Host "  [SKIP] $($svc.Name) — directory not found: $($svc.Dir)" -ForegroundColor DarkYellow
        continue
    }

    # Skip if already running
    if ($svc.Port -gt 0 -and (Test-Port $svc.Port)) {
        Write-Host "  [LIVE] $($svc.Name) already running on :$($svc.Port)" -ForegroundColor Green
        continue
    }

    Write-Host "  [START] $($svc.Name)..." -ForegroundColor White
    $proc = Start-Process cmd -ArgumentList "/k title $($svc.Title) && cd /d $($svc.Dir) && $($svc.Cmd)" -PassThru
    $StartedPids += $proc.Id

    # Stagger startup
    if ($svc.Name -eq "LLM Proxy") { Start-Sleep -Seconds 3 }
    elseif ($svc.Name -eq "Backend") { Start-Sleep -Seconds 2 }
    else { Start-Sleep -Seconds 1 }
}

# Wait for ports to come online
Write-Host ""
Write-Host "  [METHER] Waiting for services to initialize..." -ForegroundColor DarkGray

$maxWait = 15
$elapsed = 0
while ($elapsed -lt $maxWait) {
    $allUp = $true
    foreach ($svc in $Services) {
        if ($svc.Port -gt 0 -and (Test-Path $svc.Dir) -and -not (Test-Port $svc.Port)) {
            $allUp = $false
            break
        }
    }
    if ($allUp) { break }
    Start-Sleep -Seconds 1
    $elapsed++
}

# Show final status
Show-Status

# Open browser
Write-Host "  [METHER] Opening dashboard..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

# ── Monitor loop ──
Write-Host "  [METHER] Monitoring services. Press Ctrl+C to stop all." -ForegroundColor DarkGray
Write-Host ""

try {
    while ($true) {
        Start-Sleep -Seconds 10

        foreach ($svc in $Services) {
            if ($svc.Port -eq 0) { continue }
            if (-not (Test-Path $svc.Dir)) { continue }

            if (-not (Test-Port $svc.Port)) {
                Write-Host "  [ALERT] $($svc.Name) on :$($svc.Port) appears DOWN!" -ForegroundColor Red
            }
        }
    }
}
finally {
    Write-Host ""
    Write-Host "  [METHER] Shutting down..." -ForegroundColor Yellow
    
    foreach ($svc in $Services) {
        taskkill /FI "WindowTitle eq $($svc.Title)*" /F 2>$null | Out-Null
    }

    Write-Host "  [METHER] All services stopped. Goodbye." -ForegroundColor Green
}
