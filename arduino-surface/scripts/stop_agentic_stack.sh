#!/bin/sh
# Stop the Arduino Surface agentic stack (daemon + web API)

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_PID_FILE="/tmp/ember_api.pid"

printf '== Agentic Stack Shutdown ==\n'

# Stop the Arduino daemon
"$ROOT_DIR/scripts/stop_daemon.sh"
DAEMON_STATUS=$?
if [ $DAEMON_STATUS -ne 0 ]; then
  printf '[WARN] Arduino daemon stop script returned (%s)\n' "$DAEMON_STATUS"
fi

# Stop the Ember web API
PIDS=""
if [ -f "$API_PID_FILE" ]; then
  PID=$(cat "$API_PID_FILE")
  if ps -p "$PID" >/dev/null 2>&1; then
    PIDS="$PID"
  else
    printf '[OK] Ember web API already stopped (stale PID: %s)\n' "$PID"
    rm -f "$API_PID_FILE"
  fi
fi

if [ -z "$PIDS" ]; then
  PIDS=$(pgrep -f ember_api.py | tr '\n' ' ')
  if [ -z "$PIDS" ]; then
    printf '[OK] Ember web API is not running\n'
    exit 0
  fi
  printf '[WARN] No PID file; using pgrep results (%s)\n' "$PIDS"
fi

for PID in $PIDS; do
  printf '[OK] Stopping Ember web API (PID: %s)...\n' "$PID"
  kill "$PID"
done

for PID in $PIDS; do
  for _ in 1 2 3 4 5; do
    if ! ps -p "$PID" >/dev/null 2>&1; then
      printf '[OK] Ember web API stopped (PID: %s)\n' "$PID"
      break
    fi
    sleep 1
  done

  if ps -p "$PID" >/dev/null 2>&1; then
    printf '[WARN] Forcing Ember web API to stop (PID: %s)\n' "$PID"
    kill -9 "$PID"
  fi
done

rm -f "$API_PID_FILE"
printf '[OK] Ember web API fully stopped\n'
