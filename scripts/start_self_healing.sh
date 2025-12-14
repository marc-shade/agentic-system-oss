#!/bin/bash
# Start Self-Healing Monitor as a background daemon
# Runs every 5 minutes to detect and fix errors autonomously


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

LOG_DIR="$STORAGE_BASE/logs"
SCRIPT="$STORAGE_BASE/workflows/self_healing_monitor.py"
PID_FILE="/tmp/self_healing_monitor.pid"

mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Self-Healing Monitor already running (PID: $PID)"
        exit 0
    fi
fi

# Start daemon loop
echo "Starting Self-Healing Monitor daemon..."

# Background loop
(
    echo $$ > "$PID_FILE"

    while true; do
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Running self-healing check..." >> "$LOG_DIR/self_healing_daemon.log"
        python3 "$SCRIPT" >> "$LOG_DIR/self_healing_daemon.log" 2>&1

        # Sleep for 5 minutes
        sleep 300
    done
) &

DAEMON_PID=$!
echo "$DAEMON_PID" > "$PID_FILE"

echo "Self-Healing Monitor daemon started (PID: $DAEMON_PID)"
echo "  Runs every 5 minutes"
echo "  Logs: $LOG_DIR/self_healing.log"
echo "  Daemon log: $LOG_DIR/self_healing_daemon.log"
echo ""
echo "To stop: kill $DAEMON_PID"
