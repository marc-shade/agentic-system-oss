#!/bin/bash
# Stop Arduino Status Daemon

PID_FILE="/tmp/arduino_daemon.pid"

PIDS=""
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        PIDS="$PID"
    else
        echo "✗ Arduino daemon is not running (stale PID: $PID)"
        rm "$PID_FILE"
    fi
fi

if [ -z "$PIDS" ]; then
    PIDS=$(pgrep -f arduino_enhanced_daemon.py | tr '\n' ' ')
    if [ -z "$PIDS" ]; then
        echo "✗ Arduino daemon is not running"
        exit 1
    fi
    echo "✓ Using pgrep fallback (PIDs: $PIDS)"
fi

for PID in $PIDS; do
    echo "✓ Stopping Arduino daemon (PID: $PID)..."
    kill "$PID"
done

# Wait up to 5 seconds for graceful shutdown
for PID in $PIDS; do
    for i in {1..5}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "✓ Arduino daemon stopped successfully (PID: $PID)"
            break
        fi
        sleep 1
    done

    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✗ Graceful shutdown failed for PID $PID, forcing kill..."
        kill -9 "$PID"
        echo "✓ Arduino daemon killed (PID: $PID)"
    fi
done

rm -f "$PID_FILE"
