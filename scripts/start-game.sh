#!/usr/bin/env bash
# Start The Haunted Manor (backend + frontend + browser)
# Usage: ./scripts/start-game.sh [--restart]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(dirname "$SCRIPT_DIR")"
GAME_ROOT="$MONOREPO_ROOT/game"
cd "$MONOREPO_ROOT"

BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_DIR="$GAME_ROOT/backend"
FRONTEND_DIR="$GAME_ROOT/frontend"
GAME_URL="http://127.0.0.1:$FRONTEND_PORT"
API_DOCS_URL="http://127.0.0.1:$BACKEND_PORT/docs"
RESTART=false

if [[ "${1:-}" == "--restart" ]]; then
  RESTART=true
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: '$1' not found in PATH." >&2
    exit 1
  fi
}

get_port_pid() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n1 || true
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -n1 || true
  else
    echo ""
  fi
}

stop_port() {
  local port=$1
  local pid
  pid="$(get_port_pid "$port")"
  if [[ -n "$pid" ]]; then
    echo "Stopping process $pid on port $port..."
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    sleep 0.5
  fi
}

port_listening() {
  local port=$1
  [[ -n "$(get_port_pid "$port")" ]]
}

start_terminal() {
  local title=$1
  local cmd=$2
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -c "$cmd; exec bash"
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -c "$cmd; exec bash" &
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "tell app \"Terminal\" to do script \"$cmd\""
  else
    echo "Starting in background: $title"
    bash -c "$cmd" &
  fi
  echo "Started: $title"
}

require_cmd uv
require_cmd npm

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "First run: backend setup..."
  (cd "$BACKEND_DIR" && uv venv && uv sync)
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "First run: frontend setup..."
  (cd "$FRONTEND_DIR" && npm install)
fi

if $RESTART; then
  echo "Restart mode: freeing ports $BACKEND_PORT and $FRONTEND_PORT..."
  stop_port "$BACKEND_PORT"
  stop_port "$FRONTEND_PORT"
fi

echo ""
echo "The Haunted Manor - startup"
echo ""

backend_running=false
frontend_running=false
port_listening "$BACKEND_PORT" && backend_running=true
port_listening "$FRONTEND_PORT" && frontend_running=true

if $backend_running && ! $RESTART; then
  echo "Backend already running on port $BACKEND_PORT (skipping)."
else
  $backend_running && stop_port "$BACKEND_PORT"
  backend_cmd="cd '$BACKEND_DIR' && uv run uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT --reload"
  start_terminal "Haunted Manor - Backend" "$backend_cmd"
fi

if $frontend_running && ! $RESTART; then
  echo "Frontend already running on port $FRONTEND_PORT (skipping)."
else
  $frontend_running && stop_port "$FRONTEND_PORT"
  frontend_cmd="cd '$FRONTEND_DIR' && npm run dev"
  start_terminal "Haunted Manor - Frontend" "$frontend_cmd"
fi

if ! $backend_running || ! $frontend_running || $RESTART; then
  echo "Waiting for servers..."
  sleep 4
fi

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$GAME_URL" >/dev/null 2>&1 || true
elif [[ "$OSTYPE" == "darwin"* ]]; then
  open "$GAME_URL" || true
fi

echo ""
echo "API docs: $API_DOCS_URL"
echo "Game:     $GAME_URL"
echo ""
echo "Tips:"
echo "  Close the backend/frontend windows to stop"
echo "  ./scripts/start-game.sh --restart kill existing servers and start fresh"
echo ""
