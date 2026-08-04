#!/usr/bin/env bash
# Shared helpers for Capstone start scripts (Linux / macOS).
# Source from start-*.sh — do not run directly.
#
# Process lifecycle:
#   1) Prefer orderly shutdown of the process tree we started (concurrently).
#   2) Always run stop_listening_ports in the EXIT/INT/TERM trap as a
#      deterministic safety net for uvicorn --reload / Vite grandchildren.

stop_listening_ports() {
  local port pids
  for port in "$@"; do
    pids=""
    if command -v lsof >/dev/null 2>&1; then
      pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    elif command -v ss >/dev/null 2>&1; then
      # Portable parse (no GNU grep -P); ss may show users:(("cmd",pid=N,fd=M))
      pids="$(ss -ltnp "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u || true)"
    fi
    while read -r pid; do
      [[ -z "${pid:-}" ]] && continue
      echo "  Port $port still held by PID $pid -> stopping"
      kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    done <<< "$pids"
  done
}

ensure_script_npm_deps() {
  local scripts_dir="$1"
  if [[ -d "$scripts_dir/node_modules/concurrently" ]]; then
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm not found in PATH (required for scripts/ concurrently orchestration)." >&2
    exit 1
  fi
  echo "  First run: npm install in scripts/ (pinned concurrently)..."
  (cd "$scripts_dir" && npm install --no-fund --no-audit)
}

ensure_frontend_npm_deps() {
  local frontend_dir="$1"
  local label="$2"
  if [[ -d "$frontend_dir/node_modules" ]]; then
    return 0
  fi
  echo "  First run: npm install ($label)..."
  (cd "$frontend_dir" && npm install --no-fund --no-audit)
}

wait_http_ok() {
  local url="$1" label="$2" timeout="${3:-25}"
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

wait_port_listening() {
  local port="$1" label="$2" timeout="${3:-25}"
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

start_service_terminal() {
  local title="$1" cmd="$2"
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="$title" -- bash -c "$cmd; exec bash"
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$title" -e bash -c "$cmd; exec bash" &
  elif [[ "${OSTYPE:-}" == darwin* ]]; then
    osascript -e "tell app \"Terminal\" to do script \"$cmd\""
  else
    bash -c "$cmd" &
  fi
  echo "  Started terminal: $title"
}

open_url() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  elif [[ "${OSTYPE:-}" == darwin* ]]; then
    open "$url" || true
  fi
}
