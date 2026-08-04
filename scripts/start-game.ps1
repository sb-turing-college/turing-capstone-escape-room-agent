#Requires -Version 5.1
<#
.SYNOPSIS
  Local launcher for The Haunted Manor (game backend + frontend).

.DESCRIPTION
  Default: one terminal via pinned `concurrently` in `scripts/package.json`.
  See start-all.ps1 header for lifecycle rationale (SIGINT ->
  concurrently kill-others -> port cleanup in finally).

  Prefixes: game-api, game-ui

.PARAMETER Restart
  Free ports 8000/5173 before start (alias for a clean relaunch).

.PARAMETER NoBrowser
  Do not auto-open the game UI.

.PARAMETER SeparateWindows
  Escape hatch: one window per service.

.EXAMPLE
  .\scripts\start-game.ps1
  .\scripts\start-game.ps1 -Restart
  .\scripts\start-game.ps1 -SeparateWindows
#>

param(
    [switch]$Restart,
    [switch]$NoBrowser,
    [switch]$SeparateWindows
)

$ErrorActionPreference = "Stop"

$ScriptsDir   = $PSScriptRoot
$MonorepoRoot = Split-Path -Parent $ScriptsDir
. (Join-Path $ScriptsDir "lib\common.ps1")

$GameRoot = Join-Path $MonorepoRoot "game"
$BackendPort = 8000
$FrontendPort = 5173
$BackendDir = Join-Path $GameRoot "backend"
$FrontendDir = Join-Path $GameRoot "frontend"
$portsToManage = @($BackendPort, $FrontendPort)

if (-not (Test-Path $GameRoot)) {
    throw "game/ folder not found at $GameRoot"
}

Write-Host "=== The Haunted Manor launcher ===" -ForegroundColor Cyan

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "'uv' not found in PATH."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "'npm' not found in PATH."
}

Write-Host "`n[1] Freeing ports ($($portsToManage -join ', '))..." -ForegroundColor Cyan
Stop-ListeningPorts -Ports $portsToManage
Start-Sleep -Seconds 1

if (-not (Test-Path (Join-Path $BackendDir ".venv"))) {
    Write-Host "  First run: uv sync (game backend)..." -ForegroundColor Yellow
    Push-Location $BackendDir
    try { uv sync } finally { Pop-Location }
}
Ensure-FrontendNpmDeps -FrontendDir $FrontendDir -Label "game frontend"

try {
    if ($SeparateWindows) {
        Write-Host "`n[2] SeparateWindows mode..." -ForegroundColor Yellow
        Start-ServiceWindow -Title "game-api (:$BackendPort)" -WorkingDirectory $BackendDir `
            -Command "uv run uvicorn main:app --host 127.0.0.1 --port $BackendPort --reload"
        Start-ServiceWindow -Title "game-ui (:$FrontendPort)" -WorkingDirectory $FrontendDir `
            -Command "npm run dev"
        Wait-HttpOk -Url "http://127.0.0.1:$BackendPort/health" -Label "game-api" | Out-Null
        Wait-PortListening -Port $FrontendPort -Label "game-ui" | Out-Null
        if (-not $NoBrowser) {
            Start-Sleep -Seconds 2
            Start-Process "http://127.0.0.1:$FrontendPort"
        }
        Write-Host "`nGame: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
        Write-Host "SeparateWindows: close each service window to stop that service." -ForegroundColor Cyan
        return
    }

    Ensure-ScriptNpmDeps -ScriptsDir $ScriptsDir

    $probeJob = $null
    if (-not $NoBrowser) {
        $probeJob = Start-Job -ScriptBlock {
            param($Port)
            Start-Sleep -Seconds 5
            $deadline = (Get-Date).AddSeconds(40)
            while ((Get-Date) -lt $deadline) {
                try {
                    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 2
                    if ($r.StatusCode -ge 200) { break }
                } catch { Start-Sleep -Milliseconds 500 }
            }
            Start-Process "http://127.0.0.1:$Port"
        } -ArgumentList $FrontendPort
    }

    Write-Host "`n[2] Starting game-api + game-ui in this terminal (concurrently)..." -ForegroundColor Cyan
    Write-Host "  Ctrl+C stops both; port cleanup runs in finally." -ForegroundColor DarkGray
    Write-Host "  Game: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
    Write-Host ""

    Push-Location $ScriptsDir
    try {
        & npm @(
            "exec", "--", "concurrently",
            "-n", "game-api,game-ui",
            "-c", "blue,cyan",
            "--kill-others",
            "cd /d `"$BackendDir`" && uv run uvicorn main:app --host 127.0.0.1 --port $BackendPort --reload",
            "cd /d `"$FrontendDir`" && npm run dev"
        )
    } finally {
        Pop-Location
        if ($probeJob) {
            Stop-Job $probeJob -ErrorAction SilentlyContinue
            Remove-Job $probeJob -Force -ErrorAction SilentlyContinue
        }
    }
}
finally {
    if (-not $SeparateWindows) {
        Write-Host "`nSafety-net port cleanup..." -ForegroundColor Cyan
        Start-Sleep -Milliseconds 500
        Stop-ListeningPorts -Ports $portsToManage
        Write-Host "Shutdown complete." -ForegroundColor Cyan
    }
}
