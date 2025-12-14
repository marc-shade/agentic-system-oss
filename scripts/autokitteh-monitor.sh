#!/bin/bash
# AutoKitteh Monitoring Script for Autonomous System
# Auto-restarts AutoKitteh if it becomes unhealthy


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

AK_PORT=9980
PID_FILE="/tmp/autokitteh.pid"
LOG_DIR="$STORAGE_BASE/logs"

check_autokitteh() {
    # Check if AutoKitteh is responding (port check is more reliable than /health endpoint)
    if lsof -i:$AK_PORT > /dev/null 2>&1; then
        return 0  # Running and healthy
    fi
    return 1  # Not running or unhealthy
}

start_autokitteh() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting AutoKitteh..."
    $STORAGE_BASE/scripts/start-autokitteh.sh &
    AK_PID=$!
    echo $AK_PID > "$PID_FILE"

    # Wait for startup
    sleep 10

    if check_autokitteh; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - AutoKitteh started successfully (PID: $AK_PID)"
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: AutoKitteh failed to start"
        return 1
    fi
}

stop_autokitteh() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Stopping AutoKitteh..."

    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID"
            sleep 3

            # Force kill if still running
            if ps -p "$PID" > /dev/null 2>&1; then
                kill -9 "$PID"
            fi
        fi
        rm -f "$PID_FILE"
    fi

    # Also kill by port and process name
    PORT_PID=$(lsof -ti:$AK_PORT)
    if [ ! -z "$PORT_PID" ]; then
        kill "$PORT_PID" 2>/dev/null
        sleep 2
    fi

    # Kill any ak processes
    pkill -f "ak up" 2>/dev/null
    sleep 1

    echo "$(date '+%Y-%m-%d %H:%M:%S') - AutoKitteh stopped"
}

restart_autokitteh() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarting AutoKitteh..."
    stop_autokitteh
    sleep 3
    start_autokitteh
}

status_autokitteh() {
    if check_autokitteh; then
        PID=$(lsof -ti:$AK_PORT)
        echo "✅ AutoKitteh is running (PID: $PID)"
        echo "   Port: $AK_PORT"
        echo "   URL: http://localhost:$AK_PORT"

        # Check for deployments
        DEPLOYMENT_COUNT=$(/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/bin/ak deployment list 2>/dev/null | grep -c "DEPLOYMENT_STATE_ACTIVE" || echo "0")
        echo "   Active Deployments: $DEPLOYMENT_COUNT"
    else
        echo "❌ AutoKitteh is NOT running"
    fi
}

check_and_restart() {
    if ! check_autokitteh; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ⚠️  AutoKitteh is down, attempting restart..."
        start_autokitteh
    fi
}

case "$1" in
    start)
        start_autokitteh
        ;;
    stop)
        stop_autokitteh
        ;;
    restart)
        restart_autokitteh
        ;;
    status)
        status_autokitteh
        ;;
    check)
        check_and_restart
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        exit 1
        ;;
esac
