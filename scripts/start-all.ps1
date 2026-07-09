#Requires -Version 5.1
<#
  Starts the full stack for local development:
    1) The Haunted Manor backend    (port 8000)
    2) The Haunted Manor frontend   (port 5173) - required for Escape Room Agent
       "Live Game View" iframe (spectate mode)
    3) Escape Room Agent backend   (port 8001)
    4) Escape Room Agent frontend  (port 5174)

  Each service runs in its own PowerShell window so you can watch its
  logs live and Ctrl+C it individually. Ports are force-cleared first
  to avoid the classic Windows "stale process still holds the port"
  problem (uvicorn --reload children sometimes survive Ctrl+C).

  Usage (from monorepo root):
    .\scripts\start-all.ps1
    .\scripts\start-all.ps1 -SkipGame      # if game backend + frontend already run elsewhere
    .\scripts\start-all.ps1 -NoBrowser     # don't auto-open the dashboard
#>

param(
    [switch]$SkipGame,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$MonorepoRoot = Split-Path -Parent $PSScriptRoot
$GameRoot     = Join-Path $MonorepoRoot "game" | Resolve-Path -ErrorAction SilentlyContinue
$AgentRoot    = Join-Path $MonorepoRoot "agent"

$GamePort         = 8000
$GameFrontendPort = 5173
$AgentPort        = 8001
$FrontendPort     = 5174

function Stop-Port {
    param([int]$Port)
    $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $owners) {
        Write-Host "  Port $Port occupied by PID $procId -> stopping" -ForegroundColor Yellow
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

function Wait-ForHealth {
    param([string]$Url, [string]$Label, [int]$TimeoutSec = 25)
    Write-Host "  Waiting for $Label ($Url) ..." -NoNewline
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) {
                Write-Host " OK" -ForegroundColor Green
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    return $false
}

function Wait-ForPort {
    # Vite's dev server has no /health endpoint, so we just check the port
    # is being listened on instead of probing an HTTP path.
    param([int]$Port, [string]$Label, [int]$TimeoutSec = 25)
    Write-Host "  Waiting for $Label (port $Port) ..." -NoNewline
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listening) {
            Write-Host " OK" -ForegroundColor Green
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host " TIMEOUT" -ForegroundColor Red
    return $false
}

Write-Host "=== Capstone stack launcher ===" -ForegroundColor Cyan

Write-Host "`n[1/5] Freeing ports ($GamePort, $GameFrontendPort, $AgentPort, $FrontendPort)..." -ForegroundColor Cyan
Stop-Port -Port $GamePort
Stop-Port -Port $GameFrontendPort
Stop-Port -Port $AgentPort
Stop-Port -Port $FrontendPort
Start-Sleep -Seconds 2

# --- Sanity checks -----------------------------------------------------
if (-not $SkipGame -and -not $GameRoot) {
    Write-Host "ERROR: game/ folder not found (expected $MonorepoRoot\game)." -ForegroundColor Red
    Write-Host "Use -SkipGame if you start the game backend yourself." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $AgentRoot ".env"))) {
    Write-Host "WARNING: agent\.env missing. Copy .env.example and set OPENROUTER_API_KEY." -ForegroundColor Yellow
}

# --- 1) Game backend -----------------------------------------------------
if (-not $SkipGame) {
    Write-Host "`n[2/5] Starting game backend on port $GamePort..." -ForegroundColor Cyan
    $gameBackend = Join-Path $GameRoot "backend"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$gameBackend'; Write-Host 'The Haunted Manor backend (:$GamePort)' -ForegroundColor Green; uv run uvicorn main:app --reload --port $GamePort"
    ) -WindowStyle Normal
} else {
    Write-Host "`n[2/5] Skipping game backend (-SkipGame)." -ForegroundColor Yellow
}

# --- 2) Game frontend --------------------------------------------------
# Required for Escape Room Agent's "Live Game View" iframe (spectate
# mode) - it embeds this dev server directly, so it must be reachable
# even though a human never opens it on their own during agent runs.
if (-not $SkipGame) {
    Write-Host "`n[3/5] Starting game frontend on port $GameFrontendPort..." -ForegroundColor Cyan
    $gameFrontend = Join-Path $GameRoot "frontend"
    if (-not (Test-Path (Join-Path $gameFrontend "node_modules"))) {
        Write-Host "  First run: installing game frontend deps (npm install)..." -ForegroundColor Yellow
        Push-Location $gameFrontend
        npm install
        Pop-Location
    }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$gameFrontend'; Write-Host 'The Haunted Manor frontend (:$GameFrontendPort)' -ForegroundColor Green; npm run dev"
    ) -WindowStyle Normal
} else {
    Write-Host "`n[3/5] Skipping game frontend (-SkipGame)." -ForegroundColor Yellow
}

# --- 3) Agent backend ------------------------------------------------------
Write-Host "`n[4/5] Starting agent backend on port $AgentPort..." -ForegroundColor Cyan
$agentBackend = Join-Path $AgentRoot "backend"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$agentBackend'; Write-Host 'Escape Room Agent backend (:$AgentPort)' -ForegroundColor Green; uv run uvicorn main:app --reload --port $AgentPort"
) -WindowStyle Normal

# --- 4) Agent frontend -------------------------------------------------
Write-Host "`n[5/5] Starting Escape Room Agent on port $FrontendPort..." -ForegroundColor Cyan
$agentFrontend = Join-Path $AgentRoot "frontend"
if (-not (Test-Path (Join-Path $agentFrontend "node_modules"))) {
    Write-Host "  First run: installing agent frontend deps (npm install)..." -ForegroundColor Yellow
    Push-Location $agentFrontend
    npm install
    Pop-Location
}
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$agentFrontend'; Write-Host 'Escape Room Agent (:$FrontendPort)' -ForegroundColor Green; npm run dev"
) -WindowStyle Normal

# --- Health checks -----------------------------------------------------
Write-Host "`nWaiting for services to come up..." -ForegroundColor Cyan
if (-not $SkipGame) {
    Wait-ForHealth -Url "http://127.0.0.1:$GamePort/health" -Label "game backend" | Out-Null
    Wait-ForPort -Port $GameFrontendPort -Label "game frontend" | Out-Null
}
$agentUp = Wait-ForHealth -Url "http://127.0.0.1:$AgentPort/health" -Label "agent backend"

if ($agentUp) {
    try {
        $gameCheck = Invoke-RestMethod -Uri "http://127.0.0.1:$AgentPort/agent/health/game" -TimeoutSec 5
        if ($gameCheck.game_api_reachable) {
            Write-Host "  Agent -> Game link OK ($($gameCheck.game_api_base_url))" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Agent cannot reach game API at $($gameCheck.game_api_base_url)." -ForegroundColor Red
            Write-Host "  Check GAME_API_BASE_URL in agent\.env" -ForegroundColor Red
        }
    } catch {
        Write-Host "  Could not query /agent/health/game yet - check the agent backend window." -ForegroundColor Yellow
    }
}

if (-not $NoBrowser) {
    Start-Sleep -Seconds 2
    if (-not $SkipGame) {
        Start-Process "http://127.0.0.1:$GameFrontendPort"
    }
    Start-Process "http://127.0.0.1:$FrontendPort"
}

Write-Host "`nDone." -ForegroundColor Cyan
if (-not $SkipGame) {
    Write-Host "  Game:      http://127.0.0.1:$GameFrontendPort" -ForegroundColor Cyan
}
Write-Host "  Escape Room Agent: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
Write-Host "Close the opened PowerShell windows to stop each service." -ForegroundColor Cyan
