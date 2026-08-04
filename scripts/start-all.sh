#!/usr/bin/env bash
# Local launcher for the full Capstone stack (game + Escape Room Agent).
#
# Default: one terminal, multiplexed logs via pinned
# `concurrently` from `scripts/package.json` (monorepo root stays clean).
#
# Lifecycle:
#   1. Free known ports at start.
#   2. Run concurrently in the foreground (colored prefixes).
#   3. trap EXIT/INT/TERM -> port cleanup safety net after concurrently's
#      own --kill-others handling (covers uvicorn --reload / Vite children).
#
# Prefixes: game-api, game-ui, agent-api, agent-ui
#
# Usage (from monorepo root):
#   ./scripts/start-all.sh
#   ./scripts/start-all.sh --skip-game
#   ./scripts/start-all.sh --no-browser
#   ./scripts/start-all.sh --separate-windows

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

MONOREPO_ROOT="$(dirname "$SCRIPT_DIR")"
GAME_ROOT="$MONOREPO_ROOT/game"
AGENT_ROOT="$MONOREPO_ROOT/agent"
[[ -d "$GAME_ROOT" ]] || GAME_ROOT=""

GAME_PORT=8000
GAME_FRONTEND_PORT=5173
AGENT_PORT=8001
FRONTEND_PORT=5174

SKIP_GAME=false
NO_BROWSER=false
SEPARATE_WINDOWS=false

for arg in "$@"; do
  case "$arg" in
    --skip-game) SKIP_GAME=true ;;
    --no-browser) NO_BROWSER=true ;;
    --separate-windows) SEPARATE_WINDOWS=true ;;
    -h|--help)
      sed -n '1,25p' "$0"
      exit 0
      ;;
  esac
done

if $SKIP_GAME; then
  PORTS_TO_MANAGE=("$AGENT_PORT" "$FRONTEND_PORT")
else
  PORTS_TO_MANAGE=("$GAME_PORT" "$GAME_FRONTEND_PORT" "$AGENT_PORT" "$FRONTEND_PORT")
fi

CLEANED_UP=false
cleanup() {
  if $CLEANED_UP; then
    return 0
  fi
  CLEANED_UP=true
  if $SEPARATE_WINDOWS; then
    return 0
  fi
  echo ""
  echo "Safety-net port cleanup..."
  sleep 0.5
  stop_listening_ports "${PORTS_TO_MANAGE[@]}"
  echo "Shutdown complete."
}
trap cleanup EXIT INT TERM

echo "=== Capstone stack launcher ==="

if ! $SKIP_GAME && [[ -z "${GAME_ROOT}" ]]; then
  echo "ERROR: game/ folder not found (expected $MONOREPO_ROOT/game)."
  echo "Use --skip-game if the game stack already runs elsewhere."
  exit 1
fi

if [[ ! -f "$AGENT_ROOT/.env" ]]; then
  echo "WARNING: agent/.env missing. Copy .env.example and set provider API keys."
fi

echo ""
echo "[1] Freeing ports (${PORTS_TO_MANAGE[*]})..."
stop_listening_ports "${PORTS_TO_MANAGE[@]}"
sleep 1

GAME_BACKEND="${GAME_ROOT:+$GAME_ROOT/backend}"
GAME_FRONTEND="${GAME_ROOT:+$GAME_ROOT/frontend}"
AGENT_BACKEND="$AGENT_ROOT/backend"
AGENT_FRONTEND="$AGENT_ROOT/frontend"

if ! $SKIP_GAME; then
  ensure_frontend_npm_deps "$GAME_FRONTEND" "game frontend"
fi
ensure_frontend_npm_deps "$AGENT_FRONTEND" "agent frontend"

if $SEPARATE_WINDOWS; then
  echo ""
  echo "[2] Separate windows mode (one terminal per service)..."
  if ! $SKIP_GAME; then
    start_service_terminal "game-api (:$GAME_PORT)" \
      "cd '$GAME_BACKEND' && echo 'game-api' && uv run uvicorn main:app --reload --port $GAME_PORT"
    start_service_terminal "game-ui (:$GAME_FRONTEND_PORT)" \
      "cd '$GAME_FRONTEND' && echo 'game-ui' && npm run dev"
  fi
  start_service_terminal "agent-api (:$AGENT_PORT)" \
    "cd '$AGENT_BACKEND' && echo 'agent-api' && uv run uvicorn main:app --reload --port $AGENT_PORT"
  start_service_terminal "agent-ui (:$FRONTEND_PORT)" \
    "cd '$AGENT_FRONTEND' && echo 'agent-ui' && npm run dev"

  echo ""
  echo "Waiting for services..."
  if ! $SKIP_GAME; then
    wait_http_ok "http://127.0.0.1:$GAME_PORT/health" "game-api" || true
    wait_port_listening "$GAME_FRONTEND_PORT" "game-ui" || true
  fi
  wait_http_ok "http://127.0.0.1:$AGENT_PORT/health" "agent-api" || true

  if ! $NO_BROWSER; then
    sleep 2
    if ! $SKIP_GAME; then
      open_url "http://127.0.0.1:$GAME_FRONTEND_PORT"
    fi
    open_url "http://127.0.0.1:$FRONTEND_PORT"
  fi

  echo ""
  echo "Separate windows: close each terminal to stop that service."
  echo "  Escape Room Agent: http://127.0.0.1:$FRONTEND_PORT"
  # Disable cleanup for this mode — terminals own their processes.
  SEPARATE_WINDOWS=true
  exit 0
fi

ensure_script_npm_deps "$SCRIPT_DIR"

NAMES=()
COLORS=()
CMDS=()
if ! $SKIP_GAME; then
  NAMES+=("game-api"); COLORS+=("blue")
  CMDS+=("cd '$GAME_BACKEND' && uv run uvicorn main:app --reload --port $GAME_PORT")
  NAMES+=("game-ui"); COLORS+=("cyan")
  CMDS+=("cd '$GAME_FRONTEND' && npm run dev")
fi
NAMES+=("agent-api"); COLORS+=("magenta")
CMDS+=("cd '$AGENT_BACKEND' && uv run uvicorn main:app --reload --port $AGENT_PORT")
NAMES+=("agent-ui"); COLORS+=("green")
CMDS+=("cd '$AGENT_FRONTEND' && npm run dev")

IFS=','; NAME_ARG="${NAMES[*]}"; COLOR_ARG="${COLORS[*]}"; unset IFS

if ! $NO_BROWSER; then
  (
    sleep 5
    if ! $SKIP_GAME; then
      open_url "http://127.0.0.1:$GAME_FRONTEND_PORT"
    fi
    open_url "http://127.0.0.1:$FRONTEND_PORT"
  ) &
  BROWSER_PID=$!
else
  BROWSER_PID=""
fi

echo ""
echo "[2] Starting services in this terminal (concurrently)..."
echo "  Ctrl+C stops all services; port cleanup runs via trap."
echo "  Escape Room Agent: http://127.0.0.1:$FRONTEND_PORT"
echo ""

cd "$SCRIPT_DIR"
npm exec -- concurrently \
  -n "$NAME_ARG" \
  -c "$COLOR_ARG" \
  --kill-others \
  "${CMDS[@]}"
status=$?

if [[ -n "$BROWSER_PID" ]]; then
  kill "$BROWSER_PID" 2>/dev/null || true
fi

exit "$status"
