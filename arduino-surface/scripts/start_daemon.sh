#!/bin/bash
# Start Arduino Status Daemon

DAEMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/daemons"
DAEMON_SCRIPT="${2:-arduino_enhanced_daemon.py}"  # Use enhanced by default
PID_FILE="/tmp/arduino_daemon.pid"
LOG_FILE="/tmp/arduino_daemon.log"
PORT="${1:-/dev/tty.usbmodem8344401}"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✗ Arduino daemon already running (PID: $PID)"
        exit 1
    else
        echo "✓ Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Start daemon in background
echo "✓ Starting Arduino daemon ($DAEMON_SCRIPT) on $PORT..."
nohup python3 "$DAEMON_DIR/$DAEMON_SCRIPT" "$PORT" > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

sleep 2

# Check if started successfully
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✓ Arduino daemon started successfully (PID: $PID)"
        echo "✓ Logs: tail -f $LOG_FILE"
    else
        echo "✗ Arduino daemon failed to start"
        cat "$LOG_FILE"
        rm "$PID_FILE"
        exit 1
    fi
else
    echo "✗ Arduino daemon failed to start"
    exit 1
fi
