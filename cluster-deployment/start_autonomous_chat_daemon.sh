#!/bin/bash
# Start Autonomous Chat Daemon
# Platform-aware startup script for cluster node chat daemon

# Detect platform and set paths

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

if [[ "$OSTYPE" == "darwin"* ]]; then
    STORAGE_BASE="$STORAGE_BASE"
else
    STORAGE_BASE="$STORAGE_BASE"
fi

DAEMON_DIR="$STORAGE_BASE/cluster-deployment"
PID_FILE="$STORAGE_BASE/logs/autonomous-chat-daemon.pid"
LOG_FILE="$STORAGE_BASE/logs/autonomous-chat-daemon.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Autonomous chat daemon already running (PID: $PID)"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Create logs directory
mkdir -p "$(dirname "$LOG_FILE")"

# Start daemon in background
cd "$DAEMON_DIR"
nohup python3 autonomous_chat_daemon.py > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

echo "✓ Autonomous chat daemon started (PID: $PID)"
echo "  Log file: $LOG_FILE"
echo "  PID file: $PID_FILE"
echo ""
echo "To monitor: tail -f $LOG_FILE"
echo "To stop: kill $PID"
