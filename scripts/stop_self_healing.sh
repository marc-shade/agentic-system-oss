#!/bin/bash
# Stop Self-Healing Monitor daemon

PID_FILE="/tmp/self_healing_monitor.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Self-Healing Monitor not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping Self-Healing Monitor (PID: $PID)..."
    kill "$PID"
    rm "$PID_FILE"
    echo "Stopped"
else
    echo "Self-Healing Monitor not running (stale PID file)"
    rm "$PID_FILE"
fi
