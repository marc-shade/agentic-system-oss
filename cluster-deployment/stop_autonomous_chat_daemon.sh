#!/bin/bash
# Stop Autonomous Chat Daemon

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

PID_FILE="$STORAGE_BASE/logs/autonomous-chat-daemon.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Daemon not running (no PID file found)"
    exit 1
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping autonomous chat daemon (PID: $PID)..."
    kill "$PID"
    sleep 2

    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing daemon..."
        kill -9 "$PID"
    fi

    rm "$PID_FILE"
    echo "✓ Daemon stopped"
else
    echo "Daemon not running (stale PID file)"
    rm "$PID_FILE"
fi
