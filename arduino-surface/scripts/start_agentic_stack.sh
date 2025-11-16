#!/bin/sh
# Start the full Arduino Surface agentic stack (daemon + web API)

# Ensure Homebrew Python is first in PATH
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-/dev/tty.usbmodem8344401}"
DAEMON_SCRIPT="${2:-arduino_enhanced_daemon.py}"
API_PID_FILE="/tmp/ember_api.pid"
API_LOG_FILE="/tmp/ember_api.log"
API_SCRIPT="$ROOT_DIR/web_controller/ember_api.py"

printf '== Agentic Stack Startup ==\n'
printf 'Arduino port: %s\n' "$PORT"
printf 'Daemon script: %s\n' "$DAEMON_SCRIPT"

# Start the Arduino daemon via existing helper
"$ROOT_DIR/scripts/start_daemon.sh" "$PORT" "$DAEMON_SCRIPT"
DAEMON_STATUS=$?
if [ $DAEMON_STATUS -ne 0 ]; then
  printf '[WARN] Arduino daemon returned non-zero exit (%s)\n' "$DAEMON_STATUS"
fi

# Start the Ember web API if not already running
if [ -f "$API_PID_FILE" ]; then
  PID=$(cat "$API_PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    printf '[OK] Ember API already running (PID: %s)\n' "$PID"
    exit 0
  else
    printf '[OK] Removing stale Ember API PID file\n'
    rm -f "$API_PID_FILE"
  fi
fi

if [ -z "${PID:-}" ]; then
  PID=$(pgrep -f ember_api.py | head -n 1)
  if [ -n "$PID" ] && ps -p "$PID" >/dev/null 2>&1; then
    printf '[WARN] Ember API already running (pgrep detected PID: %s)\n' "$PID"
    exit 0
  fi
fi

printf '[OK] Starting Ember web API (port 5001)...\n'
nohup python3 "$API_SCRIPT" > "$API_LOG_FILE" 2>&1 &
API_PID=$!
echo "$API_PID" > "$API_PID_FILE"

sleep 2
if ps -p "$API_PID" >/dev/null 2>&1; then
  printf '[OK] Ember web API started (PID: %s)\n' "$API_PID"
  printf '[OK] Logs: tail -f %s\n' "$API_LOG_FILE"
  exit 0
else
  printf '[FAIL] Ember web API failed to start\n'
  if [ -f "$API_LOG_FILE" ]; then
    tail -n 20 "$API_LOG_FILE"
  fi
  rm -f "$API_PID_FILE"
  exit 1
fi

# Ensure Arduino daemon PID file exists for status tooling
if [ ! -f "/tmp/arduino_daemon.pid" ]; then
  DAEMON_PID=$(pgrep -f arduino_enhanced_daemon.py | head -n 1)
  if [ -n "$DAEMON_PID" ]; then
    echo "$DAEMON_PID" > /tmp/arduino_daemon.pid
  fi
fi
