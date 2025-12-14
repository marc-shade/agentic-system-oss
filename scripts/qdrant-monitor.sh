#!/bin/bash

# Qdrant monitoring and auto-restart script
# This ensures Qdrant is always running for SAFLA integration


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

QDRANT_BIN="/Users/marc/.local/bin/qdrant"
CONFIG_PATH="$STORAGE_BASE/config/qdrant-config.yaml"
PID_FILE="$STORAGE_BASE/tmp-workspace/qdrant.pid"
LOG_DIR="$STORAGE_BASE/logs"

# Check if Qdrant is running
check_qdrant() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            # Check if it's actually responding
            if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
                return 0  # Running and healthy
            fi
        fi
    fi
    return 1  # Not running or unhealthy
}

# Start Qdrant
start_qdrant() {
    echo "$(date): Starting Qdrant..." >> "$LOG_DIR/qdrant-monitor.log"

    nohup "$QDRANT_BIN" \
        --config-path "$CONFIG_PATH" \
        >> "$LOG_DIR/qdrant-stdout.log" \
        2>> "$LOG_DIR/qdrant-stderr.log" &

    echo $! > "$PID_FILE"
    sleep 2

    if check_qdrant; then
        echo "$(date): Qdrant started successfully (PID: $(cat $PID_FILE))" >> "$LOG_DIR/qdrant-monitor.log"
        return 0
    else
        echo "$(date): Failed to start Qdrant" >> "$LOG_DIR/qdrant-monitor.log"
        return 1
    fi
}

# Stop Qdrant
stop_qdrant() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "$(date): Stopping Qdrant (PID: $PID)" >> "$LOG_DIR/qdrant-monitor.log"
            kill "$PID"
            sleep 2
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    fi
}

# Main logic
case "${1:-check}" in
    start)
        if check_qdrant; then
            echo "Qdrant is already running"
        else
            start_qdrant
        fi
        ;;
    stop)
        stop_qdrant
        ;;
    restart)
        stop_qdrant
        sleep 1
        start_qdrant
        ;;
    status)
        if check_qdrant; then
            PID=$(cat "$PID_FILE")
            echo "Qdrant is running (PID: $PID)"
            curl -s http://localhost:6333/ | jq -r '"Version: " + .version'
            exit 0
        else
            echo "Qdrant is not running"
            exit 1
        fi
        ;;
    check)
        if ! check_qdrant; then
            echo "$(date): Qdrant is not running, starting..." >> "$LOG_DIR/qdrant-monitor.log"
            start_qdrant
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        exit 1
        ;;
esac
