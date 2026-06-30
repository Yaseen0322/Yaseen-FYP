#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$ROOT_DIR/.demo-pids"
KNOWN_PORTS=(8000 8001 3000 3001 3002 3003 5173 8080)

stop_pid_file() {
  local pid_file="$1"
  local name
  name="$(basename "$pid_file" .pid)"
  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"

  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "[stop] $name (pid $pid)"
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "[skip] $name pid $pid already stopped"
  fi

  rm -f "$pid_file"
}

stop_port_listener() {
  local port="$1"
  if fuser "$port/tcp" >/dev/null 2>&1; then
    echo "[stop] port $port listeners"
    fuser -k "$port/tcp" >/dev/null 2>&1 || true
  fi
}

found_pid_file=0
if [[ -d "$PID_DIR" ]]; then
  for pid_file in "$PID_DIR"/*.pid; do
    [[ -e "$pid_file" ]] || continue
    found_pid_file=1
    stop_pid_file "$pid_file"
  done
else
  echo "No PID directory found: $PID_DIR"
fi

if [[ "$found_pid_file" -eq 0 ]]; then
  echo "No running demo service PID files found."
fi

for port in "${KNOWN_PORTS[@]}"; do
  stop_port_listener "$port"
done

echo "All demo services stopped."
