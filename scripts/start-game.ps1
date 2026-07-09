# Start The Haunted Manor (backend + frontend + browser)
param(
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MonorepoRoot = Split-Path -Parent $ScriptsDir
$GameRoot = Join-Path $MonorepoRoot "game"
Set-Location $MonorepoRoot

$BackendPort = 8000
$FrontendPort = 5173
$BackendDir = Join-Path $GameRoot "backend"
$FrontendDir = Join-Path $GameRoot "frontend"
$GameUrl = "http://127.0.0.1:$FrontendPort"
$ApiDocsUrl = "http://127.0.0.1:$BackendPort/docs"

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "'$name' not found in PATH."
    }
}

function Get-PortListenerPid($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
    if ($conn) { return [int]$conn }
    return $null
}

function Test-PortListening($port) {
    return $null -ne (Get-PortListenerPid $port)
}

function Stop-PortListener($port) {
    $procId = Get-PortListenerPid $port
    if ($procId) {
        Write-Host "Stopping process $procId on port $port..."
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}

function Start-ServerWindow($title, $command) {
    Start-Process cmd -ArgumentList @("/k", $command) -WindowStyle Normal
    Write-Host "Started: $title"
}

Require-Command uv
Require-Command npm

if (-not (Test-Path (Join-Path $BackendDir ".venv"))) {
    Write-Host "First run: backend setup..."
    Push-Location $BackendDir
    uv venv
    uv sync
    Pop-Location
}

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "First run: frontend setup..."
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

if ($Restart) {
    Write-Host "Restart mode: freeing ports $BackendPort and $FrontendPort..."
    Stop-PortListener $BackendPort
    Stop-PortListener $FrontendPort
}

Write-Host ""
Write-Host "The Haunted Manor - startup"
Write-Host ""

$backendRunning = Test-PortListening $BackendPort
$frontendRunning = Test-PortListening $FrontendPort

if ($backendRunning -and -not $Restart) {
    Write-Host "Backend already running on port $BackendPort (skipping)."
} else {
    if ($backendRunning) { Stop-PortListener $BackendPort }
    $backendCmd = "title Haunted Manor - Backend && cd /d `"$BackendDir`" && uv run uvicorn main:app --host 127.0.0.1 --port $BackendPort --reload"
    Start-ServerWindow "Backend" $backendCmd
}

if ($frontendRunning -and -not $Restart) {
    Write-Host "Frontend already running on port $FrontendPort (skipping)."
} else {
    if ($frontendRunning) { Stop-PortListener $FrontendPort }
    $frontendCmd = "title Haunted Manor - Frontend && cd /d `"$FrontendDir`" && npm run dev"
    Start-ServerWindow "Frontend" $frontendCmd
}

if (-not $backendRunning -or -not $frontendRunning -or $Restart) {
    Write-Host "Waiting for servers..."
    Start-Sleep -Seconds 4
}

Start-Process $GameUrl

Write-Host ""
Write-Host "API docs: $ApiDocsUrl"
Write-Host "Game:     $GameUrl"
Write-Host ""
Write-Host "Tips:"
Write-Host "  Close the backend/frontend windows to stop"
Write-Host "  .\scripts\start-game.ps1 -Restart  kill existing servers and start fresh"
Write-Host ""
Read-Host "Press Enter to close"
