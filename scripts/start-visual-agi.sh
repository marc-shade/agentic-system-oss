#!/bin/bash
# Start Visual AGI Daemon
# Unified visual intelligence system

set -e

# Detect storage path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/detect-storage.sh" 2>/dev/null || STORAGE_BASE="/Volumes/SSDRAID0/agentic-system"

DAEMON_DIR="$STORAGE_BASE/intelligent-agents"
LOG_DIR="$STORAGE_BASE/logs"
PID_FILE="$STORAGE_BASE/tmp-workspace/visual_agi_daemon.pid"

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$PID_FILE")"

case "${1:-start}" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Visual AGI daemon is already running (PID: $(cat "$PID_FILE"))"
            exit 1
        fi

        echo "Starting Visual AGI daemon..."
        cd "$DAEMON_DIR"
        nohup python3 visual_agi_daemon.py > "$LOG_DIR/visual_agi_daemon.log" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Visual AGI daemon started (PID: $!)"
        echo "Logs: $LOG_DIR/visual_agi_daemon.log"
        ;;

    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if kill -0 "$PID" 2>/dev/null; then
                echo "Stopping Visual AGI daemon (PID: $PID)..."
                kill "$PID"
                rm -f "$PID_FILE"
                echo "Visual AGI daemon stopped"
            else
                echo "Visual AGI daemon not running (stale PID file)"
                rm -f "$PID_FILE"
            fi
        else
            echo "Visual AGI daemon not running (no PID file)"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        STATUS_FILE="$STORAGE_BASE/databases/visual_agi_daemon_status.json"

        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "Visual AGI daemon is RUNNING (PID: $(cat "$PID_FILE"))"

            if [ -f "$STATUS_FILE" ]; then
                echo ""
                echo "Status:"
                python3 -c "
import json
with open('$STATUS_FILE') as f:
    s = json.load(f)
stats = s.get('stats', {})
print(f\"  State: {s.get('state', 'unknown')}\")
print(f\"  Uptime: {stats.get('uptime_seconds', 0):.0f}s\")
print(f\"  Captures: {stats.get('captures_analyzed', 0)}\")
print(f\"  Alerts: {stats.get('alerts_generated', 0)}\")
print(f\"  Reasoning cycles: {stats.get('reasoning_cycles', 0)}\")
print(f\"  Learning updates: {stats.get('learning_updates', 0)}\")
print(f\"  Errors: {stats.get('errors', 0)}\")
print(f\"  Last capture: {stats.get('last_capture', 'never')[:19]}\")
"
            fi
        else
            echo "Visual AGI daemon is STOPPED"
        fi
        ;;

    logs)
        tail -f "$LOG_DIR/visual_agi_daemon.log"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
