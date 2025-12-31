#!/bin/bash
# Start the AGI Environmental Awareness System
# This script launches the awareness orchestrator which manages:
# - Screenshot capture (every 30s)
# - Webcam capture (every 5min)
# - Visual memory processing (analyze images → memory)
# - Audio awareness (listen → transcribe → memory)
# - Drive health monitoring (prevent disk fill)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# CRITICAL: Always use SSDRAID0 for sensory data (hot tier)
# Do NOT rely on AGENTIC_ROOT which may point to FILES (backup only)
if [[ -d "/Volumes/SSDRAID0/agentic-system" ]]; then
    STORAGE_BASE="/Volumes/SSDRAID0/agentic-system"
elif [[ -d "/home/marc/agentic-system" ]]; then
    STORAGE_BASE="/home/marc/agentic-system"
else
    echo "ERROR: Cannot find agentic-system storage"
    exit 1
fi

AGENTS_DIR="$STORAGE_BASE/intelligent-agents"
LOG_DIR="$STORAGE_BASE/logs"
PID_FILE="$LOG_DIR/awareness.pid"

mkdir -p "$LOG_DIR"

case "${1:-start}" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Awareness system already running (PID $(cat "$PID_FILE"))"
            exit 1
        fi

        echo "Starting AGI Environmental Awareness System..."
        echo "Storage: $STORAGE_BASE"
        echo "Logs: $LOG_DIR/awareness.log"

        nohup python3 "$AGENTS_DIR/awareness_orchestrator.py" \
            >> "$LOG_DIR/awareness.log" 2>&1 &

        echo $! > "$PID_FILE"
        echo "Started with PID $(cat "$PID_FILE")"
        echo ""
        echo "Monitor with: tail -f $LOG_DIR/awareness.log"
        ;;

    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Stopping awareness system (PID $PID)..."
                kill "$PID"
                rm -f "$PID_FILE"
                echo "Stopped"
            else
                echo "Process not running, cleaning up PID file"
                rm -f "$PID_FILE"
            fi
        else
            echo "Awareness system not running"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Awareness system running (PID $(cat "$PID_FILE"))"

            # Get health status
            python3 -c "
import sys
sys.path.insert(0, '$AGENTS_DIR')
from awareness_orchestrator import get_status
import json
status = get_status()
print(json.dumps(status, indent=2))
"
        else
            echo "Awareness system not running"
        fi
        ;;

    logs)
        tail -f "$LOG_DIR/awareness.log"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
