#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/.demo-logs"
PID_DIR="$ROOT_DIR/.demo-pids"
TMP_DIR="$ROOT_DIR/.demo-tmp"
DEMO_DATABASE_FILE="$ROOT_DIR/backend/demo_staging.db"
DEMO_DATABASE_URL="${DEMO_DATABASE_URL:-sqlite:///$DEMO_DATABASE_FILE}"
DEMO_SECRET_KEY="${DEMO_SECRET_KEY:-demo-staging-secret-key-change-before-release-1234}"

SKIP_DESKTOP=0
SKIP_WEBCAM=0
SKIP_MANAGER_PORTAL=0
RESET_DEMO_DB=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-desktop)
      SKIP_DESKTOP=1
      ;;
    --skip-webcam)
      SKIP_WEBCAM=1
      ;;
    --skip-manager-portal)
      SKIP_MANAGER_PORTAL=1
      ;;
    --reset-demo-db)
      RESET_DEMO_DB=1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--skip-desktop] [--skip-webcam] [--skip-manager-portal] [--reset-demo-db]" >&2
      exit 1
      ;;
  esac
  shift
done

mkdir -p "$LOG_DIR" "$PID_DIR" "$TMP_DIR"

kill_port_if_busy() {
  local port="$1"
  if fuser "$port/tcp" >/dev/null 2>&1; then
    echo "[warn] Port $port is already in use. Stop the existing process or run ./stop-demo.sh first." >&2
    exit 1
  fi
}

start_service() {
  local name="$1"
  local workdir="$2"
  local cmd="$3"
  local pid_file="$PID_DIR/$name.pid"
  local log_file="$LOG_DIR/$name.log"

  if [[ -f "$pid_file" ]]; then
    local old_pid
    old_pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "[skip] $name already running (pid $old_pid)"
      return
    fi
    rm -f "$pid_file"
  fi

  : > "$log_file"

  (
    cd "$workdir"
    nohup bash -lc "$cmd" </dev/null >>"$log_file" 2>&1 &
    echo "$!" > "$pid_file"
  )

  local new_pid
  new_pid="$(cat "$pid_file")"
  sleep 2

  if ! kill -0 "$new_pid" 2>/dev/null; then
    echo "[fail] $name exited during startup" >&2
    echo "       log: $log_file" >&2
    tail -n 40 "$log_file" >&2 || true
    rm -f "$pid_file"
    exit 1
  fi

  echo "[ok]   $name started (pid $new_pid)"
  echo "       log: $log_file"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local attempts="${3:-30}"
  local delay="${4:-1}"
  local i

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[ok]   $name ready at $url"
      return 0
    fi
    sleep "$delay"
  done

  echo "[fail] $name did not become ready at $url" >&2
  return 1
}

ensure_python_env() {
  local service_dir="$1"
  local req_file="$2"

  if [[ ! -d "$service_dir/.venv" ]]; then
    echo "[setup] Creating venv in $service_dir/.venv"
    python3 -m venv "$service_dir/.venv"
  fi

  echo "[setup] Installing Python deps in $service_dir"
  "$service_dir/.venv/bin/pip" install -r "$req_file"
}

ensure_node_env() {
  local service_dir="$1"
  if [[ ! -d "$service_dir/node_modules" ]]; then
    echo "[setup] Installing npm deps in $service_dir"
    (cd "$service_dir" && npm install)
  fi
}

echo "== Demo Startup =="

BACKEND_DIR="$ROOT_DIR/backend"
WEBCAM_DIR="$ROOT_DIR/webcam-service"
MANAGER_DIR="$ROOT_DIR/manager-portal"
DESKTOP_DIR="$ROOT_DIR/desktop-app"

kill_port_if_busy 8000

if [[ "$SKIP_WEBCAM" -eq 0 ]]; then
  kill_port_if_busy 8001
fi

if [[ "$SKIP_MANAGER_PORTAL" -eq 0 ]]; then
  kill_port_if_busy 3000
fi

if [[ "$SKIP_DESKTOP" -eq 0 ]]; then
  kill_port_if_busy 5173
  kill_port_if_busy 8080
fi

ensure_python_env "$BACKEND_DIR" "$BACKEND_DIR/requirements.txt"

if [[ "$SKIP_WEBCAM" -eq 0 ]]; then
  ensure_python_env "$WEBCAM_DIR" "$WEBCAM_DIR/requirements.txt"
fi

if [[ "$SKIP_MANAGER_PORTAL" -eq 0 ]]; then
  ensure_node_env "$MANAGER_DIR"
fi

if [[ "$SKIP_DESKTOP" -eq 0 ]]; then
  ensure_node_env "$DESKTOP_DIR"
fi

if [[ "$RESET_DEMO_DB" -eq 1 ]]; then
  echo "[setup] Resetting demo database at $DEMO_DATABASE_FILE"
  rm -f "$DEMO_DATABASE_FILE"
fi

echo "[setup] Applying backend migrations"
(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  DATABASE_URL="$DEMO_DATABASE_URL" SECRET_KEY="$DEMO_SECRET_KEY" alembic upgrade head
)

echo "[setup] Seeding demo accounts"
(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  DATABASE_URL="$DEMO_DATABASE_URL" SECRET_KEY="$DEMO_SECRET_KEY" python scripts/seed_demo_accounts.py
)

start_service \
  "backend" \
  "$BACKEND_DIR" \
  "export DATABASE_URL='$DEMO_DATABASE_URL' SECRET_KEY='$DEMO_SECRET_KEY' && source .venv/bin/activate && exec uvicorn app.main:app --host 127.0.0.1 --port 8000"
wait_for_http "backend" "http://127.0.0.1:8000/health"

start_service \
  "alert-worker" \
  "$BACKEND_DIR" \
  "export DATABASE_URL='$DEMO_DATABASE_URL' SECRET_KEY='$DEMO_SECRET_KEY' && source .venv/bin/activate && exec python -m app.workers.operational_jobs --interval 30"

if [[ "$SKIP_WEBCAM" -eq 0 ]]; then
  start_service \
    "webcam" \
    "$WEBCAM_DIR" \
    "export MPLCONFIGDIR='$TMP_DIR/matplotlib' && source .venv/bin/activate && exec python main.py"
  wait_for_http "webcam" "http://127.0.0.1:8001/health"
else
  echo "[skip] webcam startup skipped"
fi

if [[ "$SKIP_MANAGER_PORTAL" -eq 0 ]]; then
  start_service \
    "manager-portal" \
    "$MANAGER_DIR" \
    "exec npm run dev -- --host 127.0.0.1 --port 3000"
  wait_for_http "manager portal" "http://127.0.0.1:3000"
else
  echo "[skip] manager portal startup skipped"
fi

if [[ "$SKIP_DESKTOP" -eq 0 ]]; then
  start_service \
    "desktop-app" \
    "$DESKTOP_DIR" \
    "exec npm run dev"
else
  echo "[skip] desktop app startup skipped"
fi

echo
echo "== Demo Services =="
echo "Backend API:      http://127.0.0.1:8000"
echo "Backend docs:     http://127.0.0.1:8000/docs"
echo "Alert worker:     running every 30 seconds"
echo "Webcam service:   http://127.0.0.1:8001/health"
echo "Manager portal:   http://127.0.0.1:3000"
echo "Demo database:    $DEMO_DATABASE_FILE"
echo
echo "Demo manager login:"
echo "  manager@Yaseenfyp.com / Password@123"
echo
echo "Demo employee logins:"
echo "  employee1@Yaseenfyp.com / Password@123"
echo "  employee2@Yaseenfyp.com / Password@123"
echo
echo "Browser extension path:"
echo "  $ROOT_DIR/browser-extension"
echo
echo "To stop all services:"
echo "  $ROOT_DIR/stop-demo.sh"
