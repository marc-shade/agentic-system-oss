#!/bin/bash
# n8n Monitoring Script for Autonomous System
# Auto-restarts n8n if it becomes unhealthy


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

N8N_PORT=5678
PID_FILE="/tmp/n8n.pid"
LOG_DIR="$STORAGE_BASE/logs"

check_n8n() {
    # Check if n8n is responding
    if curl -sf http://localhost:$N8N_PORT > /dev/null 2>&1; then
        return 0  # Running and healthy
    fi
    return 1  # Not running or unhealthy
}

start_n8n() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting n8n..."
    $STORAGE_BASE/scripts/start-n8n.sh &
    N8N_PID=$!
    echo $N8N_PID > "$PID_FILE"

    # Wait a few seconds for startup
    sleep 5

    if check_n8n; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - n8n started successfully (PID: $N8N_PID)"
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: n8n failed to start"
        return 1
    fi
}

stop_n8n() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Stopping n8n..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 2

            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Also kill by port
    PORT_PID=$(lsof -ti:$N8N_PORT)
    if [ ! -z "$PORT_PID" ]; then
        kill "$PORT_PID" 2>/dev/null
        sleep 1
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - n8n stopped"
}

restart_n8n() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarting n8n..."
    stop_n8n
    sleep 2
    start_n8n
}

status_n8n() {
    if check_n8n; then
        PID=$(lsof -ti:$N8N_PORT)
        echo "✅ n8n is running (PID: $PID)"

        # Get version if possible
        VERSION=$(curl -s http://localhost:$N8N_PORT/healthz 2>/dev/null | jq -r '.version' 2>/dev/null || echo "unknown")
        echo "   Version: $VERSION"
        echo "   Port: $N8N_PORT"
        echo "   URL: http://localhost:$N8N_PORT"
    else
        echo "❌ n8n is NOT running"
    fi
}

check_and_restart() {
    if ! check_n8n; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ⚠️  n8n is down, attempting restart..."
        start_n8n
    fi
}

case "$1" in
    start)
        start_n8n
        ;;
    stop)
        stop_n8n
        ;;
    restart)
        restart_n8n
        ;;
    status)
        status_n8n
        ;;
    check)
        check_and_restart
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        exit 1
        ;;
esac
