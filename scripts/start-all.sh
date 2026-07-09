#!/usr/bin/env bash
# Starts the full stack for local development:
#   1) The Haunted Manor backend    (port 8000)
#   2) The Haunted Manor frontend   (port 5173) - Live Game View iframe
#   3) Escape Room Agent backend   (port 8001)
#   4) Escape Room Agent frontend  (port 5174)
#
# Usage (from monorepo root):
#   ./scripts/start-all.sh
#   ./scripts/start-all.sh --skip-game
#   ./scripts/start-all.sh --no-browser

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONOREPO_ROOT="$(dirname "$SCRIPT_DIR")"
GAME_ROOT="$(cd "$MONOREPO_ROOT/game" 2>/dev/null && pwd || true)"
AGENT_ROOT="$MONOREPO_ROOT/agent"

GAME_PORT=8000
GAME_FRONTEND_PORT=5173
AGENT_PORT=8001
FRONTEND_PORT=5174
SKIP_GAME=false
NO_BROWSER=false

for arg in "$@"; do
  case "$arg" in
    --skip-game) SKIP_GAME=true ;;
    --no-browser) NO_BROWSER=true ;;
  esac
done

stop_port() {
  local port=$1
  local pids
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -ltnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true)"
  else
    pids=""
  fi
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    echo "  Port $port occupied by PID $pid -> stopping"
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  done <<< "$pids"
}

wait_for_health() {
  local url=$1 label=$2 timeout=${3:-25}
  echo -n "  Waiting for $label ($url) ..."
  local deadline=$((SECONDS + timeout))
  while (( SECONDS < deadline )); do
    if curl -sf --max-time 2 "$url" >/dev/null 2>&1; then
      echo " OK"
      return 0
    fi
    sleep 0.5
  done
  echo " TIMEOUT"
  return 1
}

wait_for_port() {
  local port=$1 label=$2 timeout=${3:-25}
  echo -n "  Waiting for $label (port $port) ..."
  local deadline=$((SECONDS + timeout))
  while (( SECONDS < deadline )); do
    if command -v lsof >/dev/null 2>&1 && lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      echo " OK"
      return 0
    fi
    if command -v ss >/dev/null 2>&1 && ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN; then
      echo " OK"
      return 0
    fi
    sleep 0.5
  done
  echo " TIMEOUT"
  return 1
}

start_terminal() {
  local title=$1 cmd=$2
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -c "$cmd; exec bash"
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -c "$cmd; exec bash" &
  elif [[ "$OSTYPE" == darwin* ]]; then
    osascript -e "tell app \"Terminal\" to do script \"$cmd\""
  else
    bash -c "$cmd" &
  fi
}

open_url() {
  local url=$1
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif [[ "$OSTYPE" == darwin* ]]; then
    open "$url" || true
  fi
}

echo "=== Capstone stack launcher ==="

echo ""
echo "[1/5] Freeing ports ($GAME_PORT, $GAME_FRONTEND_PORT, $AGENT_PORT, $FRONTEND_PORT)..."
stop_port "$GAME_PORT"
stop_port "$GAME_FRONTEND_PORT"
stop_port "$AGENT_PORT"
stop_port "$FRONTEND_PORT"
sleep 2

if ! $SKIP_GAME && [[ -z "${GAME_ROOT:-}" || ! -d "$GAME_ROOT" ]]; then
  echo "ERROR: game/ folder not found (expected $MONOREPO_ROOT/game)."
  echo "Use --skip-game if you start the game backend yourself."
  exit 1
fi

if [[ ! -f "$AGENT_ROOT/.env" ]]; then
  echo "WARNING: agent/.env missing. Copy .env.example and set OPENROUTER_API_KEY."
fi

if ! $SKIP_GAME; then
  echo ""
  echo "[2/5] Starting game backend on port $GAME_PORT..."
  game_backend="$GAME_ROOT/backend"
  start_terminal "The Haunted Manor backend (:$GAME_PORT)" \
    "cd '$game_backend' && echo 'The Haunted Manor backend (:$GAME_PORT)' && uv run uvicorn main:app --reload --port $GAME_PORT"

  echo ""
  echo "[3/5] Starting game frontend on port $GAME_FRONTEND_PORT..."
  game_frontend="$GAME_ROOT/frontend"
  if [[ ! -d "$game_frontend/node_modules" ]]; then
    echo "  First run: installing game frontend deps (npm install)..."
    (cd "$game_frontend" && npm install)
  fi
  start_terminal "The Haunted Manor frontend (:$GAME_FRONTEND_PORT)" \
    "cd '$game_frontend' && echo 'The Haunted Manor frontend (:$GAME_FRONTEND_PORT)' && npm run dev"
else
  echo ""
  echo "[2/5] Skipping game backend (--skip-game)."
  echo "[3/5] Skipping game frontend (--skip-game)."
fi

echo ""
echo "[4/5] Starting agent backend on port $AGENT_PORT..."
agent_backend="$AGENT_ROOT/backend"
start_terminal "Escape Room Agent backend (:$AGENT_PORT)" \
  "cd '$agent_backend' && echo 'Escape Room Agent backend (:$AGENT_PORT)' && uv run uvicorn main:app --reload --port $AGENT_PORT"

echo ""
echo "[5/5] Starting Escape Room Agent on port $FRONTEND_PORT..."
agent_frontend="$AGENT_ROOT/frontend"
if [[ ! -d "$agent_frontend/node_modules" ]]; then
  echo "  First run: installing agent frontend deps (npm install)..."
  (cd "$agent_frontend" && npm install)
fi
start_terminal "Escape Room Agent (:$FRONTEND_PORT)" \
  "cd '$agent_frontend' && echo 'Escape Room Agent (:$FRONTEND_PORT)' && npm run dev"

echo ""
echo "Waiting for services to come up..."
if ! $SKIP_GAME; then
  wait_for_health "http://127.0.0.1:$GAME_PORT/health" "game backend" || true
  wait_for_port "$GAME_FRONTEND_PORT" "game frontend" || true
fi
if wait_for_health "http://127.0.0.1:$AGENT_PORT/health" "agent backend"; then
  if curl -sf "http://127.0.0.1:$AGENT_PORT/agent/health/game" 2>/dev/null | grep -q '"game_api_reachable":true'; then
    echo "  Agent -> Game link OK"
  else
    echo "  WARNING: Agent cannot reach game API. Check GAME_API_BASE_URL in agent/.env"
  fi
fi

if ! $NO_BROWSER; then
  sleep 2
  if ! $SKIP_GAME; then
    open_url "http://127.0.0.1:$GAME_FRONTEND_PORT"
  fi
  open_url "http://127.0.0.1:$FRONTEND_PORT"
fi

echo ""
echo "Done."
if ! $SKIP_GAME; then
  echo "  Game:      http://127.0.0.1:$GAME_FRONTEND_PORT"
fi
echo "  Escape Room Agent: http://127.0.0.1:$FRONTEND_PORT"
echo "Close the opened terminal windows to stop each service."
