#Requires -Version 5.1
<#
.SYNOPSIS
  Local launcher for the full Capstone stack (game + Escape Room Agent).

.DESCRIPTION
  Default mode: one terminal, multiplexed logs via pinned
  `concurrently` from `scripts/package.json` (keeps the monorepo root clean).

  Lifecycle:
    1. Free known ports at start (stale uvicorn/vite leftovers).
    2. Run `concurrently` in the foreground (colored prefixes).
    3. On Ctrl+C / exit: `finally` runs Stop-ListeningPorts as a
       deterministic safety net. Primary stop is concurrently's own
       `--kill-others` / SIGINT handling; port cleanup catches Windows
       grandchildren from `uvicorn --reload` and Vite that can linger.

  Prefixes: game-api, game-ui, agent-api, agent-ui

.PARAMETER SkipGame
  Start only agent services (8001/5174). Does not free or start game ports.

.PARAMETER NoBrowser
  Do not auto-open browser tabs.

.PARAMETER SeparateWindows
  Escape hatch: one PowerShell window per service (legacy debug mode).

.EXAMPLE
  .\scripts\start-all.ps1
  .\scripts\start-all.ps1 -NoBrowser
  .\scripts\start-all.ps1 -SkipGame
  .\scripts\start-all.ps1 -SeparateWindows
#>

param(
    [switch]$SkipGame,
    [switch]$NoBrowser,
    [switch]$SeparateWindows
)

$ErrorActionPreference = "Stop"

$ScriptsDir   = $PSScriptRoot
$MonorepoRoot = Split-Path -Parent $ScriptsDir
. (Join-Path $ScriptsDir "lib\common.ps1")

$GameRoot  = Join-Path $MonorepoRoot "game"
$AgentRoot = Join-Path $MonorepoRoot "agent"
if (-not (Test-Path $GameRoot)) { $GameRoot = $null }

$GamePort         = 8000
$GameFrontendPort = 5173
$AgentPort        = 8001
$FrontendPort     = 5174

$agentPorts = @($AgentPort, $FrontendPort)
$gamePorts  = @($GamePort, $GameFrontendPort)
$portsToManage = if ($SkipGame) { $agentPorts } else { $gamePorts + $agentPorts }

Write-Host "=== Capstone stack launcher ===" -ForegroundColor Cyan

if (-not $SkipGame -and -not $GameRoot) {
    Write-Host "ERROR: game/ folder not found (expected $MonorepoRoot\game)." -ForegroundColor Red
    Write-Host "Use -SkipGame if the game stack already runs elsewhere." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $AgentRoot ".env"))) {
    Write-Host "WARNING: agent\.env missing. Copy .env.example and set provider API keys." -ForegroundColor Yellow
}

Write-Host "`n[1] Freeing ports ($($portsToManage -join ', '))..." -ForegroundColor Cyan
Stop-ListeningPorts -Ports $portsToManage
Start-Sleep -Seconds 1

$gameBackend   = if ($GameRoot) { Join-Path $GameRoot "backend" } else { $null }
$gameFrontend  = if ($GameRoot) { Join-Path $GameRoot "frontend" } else { $null }
$agentBackend  = Join-Path $AgentRoot "backend"
$agentFrontend = Join-Path $AgentRoot "frontend"

if (-not $SkipGame) {
    Ensure-FrontendNpmDeps -FrontendDir $gameFrontend -Label "game frontend"
}
Ensure-FrontendNpmDeps -FrontendDir $agentFrontend -Label "agent frontend"

try {
    if ($SeparateWindows) {
        Write-Host "`n[2] SeparateWindows mode (one window per service)..." -ForegroundColor Yellow
        if (-not $SkipGame) {
            Start-ServiceWindow -Title "game-api (:$GamePort)" -WorkingDirectory $gameBackend `
                -Command "uv run uvicorn main:app --reload --port $GamePort"
            Start-ServiceWindow -Title "game-ui (:$GameFrontendPort)" -WorkingDirectory $gameFrontend `
                -Command "npm run dev"
        }
        Start-ServiceWindow -Title "agent-api (:$AgentPort)" -WorkingDirectory $agentBackend `
            -Command "uv run uvicorn main:app --reload --port $AgentPort"
        Start-ServiceWindow -Title "agent-ui (:$FrontendPort)" -WorkingDirectory $agentFrontend `
            -Command "npm run dev"

        Write-Host "`nWaiting for services..." -ForegroundColor Cyan
        if (-not $SkipGame) {
            Wait-HttpOk -Url "http://127.0.0.1:$GamePort/health" -Label "game-api" | Out-Null
            Wait-PortListening -Port $GameFrontendPort -Label "game-ui" | Out-Null
        }
        Wait-HttpOk -Url "http://127.0.0.1:$AgentPort/health" -Label "agent-api" | Out-Null

        if (-not $NoBrowser) {
            Start-Sleep -Seconds 2
            if (-not $SkipGame) { Start-Process "http://127.0.0.1:$GameFrontendPort" }
            Start-Process "http://127.0.0.1:$FrontendPort"
        }

        Write-Host "`nSeparateWindows: close each service window to stop that service." -ForegroundColor Cyan
        Write-Host "  Escape Room Agent: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
        # Do not port-kill on exit — windows own their processes.
        return
    }

    Ensure-ScriptNpmDeps -ScriptsDir $ScriptsDir

    $names = New-Object System.Collections.Generic.List[string]
    $colors = New-Object System.Collections.Generic.List[string]
    $cmds = New-Object System.Collections.Generic.List[string]

    if (-not $SkipGame) {
        [void]$names.Add("game-api"); [void]$colors.Add("blue")
        [void]$cmds.Add("cd /d `"$gameBackend`" && uv run uvicorn main:app --reload --port $GamePort")
        [void]$names.Add("game-ui"); [void]$colors.Add("cyan")
        [void]$cmds.Add("cd /d `"$gameFrontend`" && npm run dev")
    }
    [void]$names.Add("agent-api"); [void]$colors.Add("magenta")
    [void]$cmds.Add("cd /d `"$agentBackend`" && uv run uvicorn main:app --reload --port $AgentPort")
    [void]$names.Add("agent-ui"); [void]$colors.Add("green")
    [void]$cmds.Add("cd /d `"$agentFrontend`" && npm run dev")

    $nameArg = ($names -join ",")
    $colorArg = ($colors -join ",")

    # Readiness + browser in a background job so concurrently can own the console.
    $probeScript = {
        param($SkipGame, $NoBrowser, $GamePort, $GameFrontendPort, $AgentPort, $FrontendPort)
        Start-Sleep -Seconds 4
        function Test-Url($Url) {
            try {
                $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
                return $r.StatusCode -eq 200
            } catch { return $false }
        }
        $deadline = (Get-Date).AddSeconds(45)
        if (-not $SkipGame) {
            while ((Get-Date) -lt $deadline -and -not (Test-Url "http://127.0.0.1:$GamePort/health")) {
                Start-Sleep -Milliseconds 500
            }
        }
        while ((Get-Date) -lt $deadline -and -not (Test-Url "http://127.0.0.1:$AgentPort/health")) {
            Start-Sleep -Milliseconds 500
        }
        if (-not $NoBrowser) {
            if (-not $SkipGame) { Start-Process "http://127.0.0.1:$GameFrontendPort" }
            Start-Process "http://127.0.0.1:$FrontendPort"
        }
    }
    $probeJob = Start-Job -ScriptBlock $probeScript -ArgumentList @(
        [bool]$SkipGame, [bool]$NoBrowser, $GamePort, $GameFrontendPort, $AgentPort, $FrontendPort
    )

    Write-Host "`n[2] Starting services in this terminal (concurrently)..." -ForegroundColor Cyan
    Write-Host "  Ctrl+C stops all services; port cleanup runs in finally." -ForegroundColor DarkGray
    Write-Host "  Escape Room Agent: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
    Write-Host ""

    Push-Location $ScriptsDir
    try {
        # concurrently uses cmd-style commands on Windows (cd /d).
        $npmArgs = @(
            "exec", "--", "concurrently",
            "-n", $nameArg,
            "-c", $colorArg,
            "--kill-others"
        ) + @($cmds.ToArray())
        & npm @npmArgs
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
        if ($probeJob) {
            Stop-Job $probeJob -ErrorAction SilentlyContinue
            Remove-Job $probeJob -Force -ErrorAction SilentlyContinue
        }
    }

    if ($exitCode -ne 0 -and $null -ne $exitCode) {
        Write-Host "concurrently exited with code $exitCode" -ForegroundColor Yellow
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
