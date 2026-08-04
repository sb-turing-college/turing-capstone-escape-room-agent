#!/usr/bin/env bash
# Local launcher for The Haunted Manor (game backend + frontend).
#
# Default: one terminal via pinned `concurrently` in `scripts/package.json`.
# Lifecycle mirrors start-all.sh (trap -> port cleanup safety net).
#
# Prefixes: game-api, game-ui
#
# Usage:
#   ./scripts/start-game.sh
#   ./scripts/start-game.sh --restart
#   ./scripts/start-game.sh --no-browser
#   ./scripts/start-game.sh --separate-windows

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

MONOREPO_ROOT="$(dirname "$SCRIPT_DIR")"
GAME_ROOT="$MONOREPO_ROOT/game"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_DIR="$GAME_ROOT/backend"
FRONTEND_DIR="$GAME_ROOT/frontend"
PORTS_TO_MANAGE=("$BACKEND_PORT" "$FRONTEND_PORT")

RESTART=false
NO_BROWSER=false
SEPARATE_WINDOWS=false

for arg in "$@"; do
  case "$arg" in
    --restart) RESTART=true ;;
    --no-browser) NO_BROWSER=true ;;
    --separate-windows) SEPARATE_WINDOWS=true ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
  esac
done

if [[ ! -d "$GAME_ROOT" ]]; then
  echo "ERROR: game/ folder not found at $GAME_ROOT" >&2
  exit 1
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

echo "=== The Haunted Manor launcher ==="

command -v uv >/dev/null 2>&1 || { echo "ERROR: uv not found in PATH" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found in PATH" >&2; exit 1; }

echo ""
echo "[1] Freeing ports (${PORTS_TO_MANAGE[*]})..."
# --restart kept for README compatibility; ports are always freed at start.
stop_listening_ports "${PORTS_TO_MANAGE[@]}"
sleep 1
if $RESTART; then
  echo "  (--restart: ports cleared)"
fi

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "  First run: uv sync (game backend)..."
  (cd "$BACKEND_DIR" && uv sync)
fi
ensure_frontend_npm_deps "$FRONTEND_DIR" "game frontend"

if $SEPARATE_WINDOWS; then
  echo ""
  echo "[2] Separate windows mode..."
  start_service_terminal "game-api (:$BACKEND_PORT)" \
    "cd '$BACKEND_DIR' && echo 'game-api' && uv run uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT --reload"
  start_service_terminal "game-ui (:$FRONTEND_PORT)" \
    "cd '$FRONTEND_DIR' && echo 'game-ui' && npm run dev -- --host 127.0.0.1 --port $FRONTEND_PORT"
  wait_http_ok "http://127.0.0.1:$BACKEND_PORT/health" "game-api" || true
  wait_port_listening "$FRONTEND_PORT" "game-ui" || true
  if ! $NO_BROWSER; then
    sleep 2
    open_url "http://127.0.0.1:$FRONTEND_PORT"
  fi
  echo ""
  echo "Game: http://127.0.0.1:$FRONTEND_PORT"
  echo "Separate windows: close each terminal to stop that service."
  SEPARATE_WINDOWS=true
  exit 0
fi

ensure_script_npm_deps "$SCRIPT_DIR"

BROWSER_PID=""
if ! $NO_BROWSER; then
  (
    sleep 5
    open_url "http://127.0.0.1:$FRONTEND_PORT"
  ) &
  BROWSER_PID=$!
fi

echo ""
echo "[2] Starting game-api + game-ui in this terminal (concurrently)..."
echo "  Ctrl+C stops both; port cleanup runs via trap."
echo "  Game: http://127.0.0.1:$FRONTEND_PORT"
echo ""

cd "$SCRIPT_DIR"
npm exec -- concurrently \
  -n "game-api,game-ui" \
  -c "blue,cyan" \
  --kill-others \
  "cd '$BACKEND_DIR' && uv run uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT --reload" \
  "cd '$FRONTEND_DIR' && npm run dev -- --host 127.0.0.1 --port $FRONTEND_PORT"
status=$?

if [[ -n "$BROWSER_PID" ]]; then
  kill "$BROWSER_PID" 2>/dev/null || true
fi

exit "$status"
