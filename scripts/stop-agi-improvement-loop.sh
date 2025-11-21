#!/bin/bash
#
# Stop Autonomous Improvement Loop
# =================================
#
# Gracefully stops the AGI improvement daemon.

set -e

PID_FILE="/tmp/agi_improvement_daemon.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID file not found. Daemon may not be running."
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ Process $PID not found. Daemon may have already stopped."
    rm "$PID_FILE"
    exit 1
fi

echo "🛑 Stopping AGI Improvement Daemon (PID: $PID)..."

# Send SIGTERM for graceful shutdown
kill -TERM "$PID"

# Wait for process to stop (max 10 seconds)
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Daemon stopped successfully"
        rm "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "⚠️  Daemon didn't stop gracefully, forcing shutdown..."
kill -KILL "$PID" 2>/dev/null || true
rm "$PID_FILE"

echo "✅ Daemon stopped (forced)"
