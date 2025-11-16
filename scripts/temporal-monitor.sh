#!/bin/bash
# Temporal Server Monitoring Script for Autonomous System
# Auto-restarts Temporal if it becomes unhealthy

GRPC_PORT=7233
UI_PORT=8233
PID_FILE="/tmp/temporal.pid"
LOG_DIR="/mnt/agentic-system/logs"

check_temporal() {
    # Check if Temporal gRPC port is responding
    if lsof -i:$GRPC_PORT > /dev/null 2>&1; then
        # Also check UI port
        if lsof -i:$UI_PORT > /dev/null 2>&1; then
            return 0  # Running and healthy
        fi
    fi
    return 1  # Not running or unhealthy
}

start_temporal() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Temporal server..."
    /mnt/agentic-system/scripts/start-temporal.sh &
    TEMPORAL_PID=$!
    echo $TEMPORAL_PID > "$PID_FILE"

    # Wait for startup
    sleep 10

    if check_temporal; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Temporal server started successfully (PID: $TEMPORAL_PID)"
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: Temporal server failed to start"
        return 1
    fi
}

stop_temporal() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Stopping Temporal server..."

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

    # Also kill by port
    GRPC_PID=$(lsof -ti:$GRPC_PORT)
    if [ ! -z "$GRPC_PID" ]; then
        kill "$GRPC_PID" 2>/dev/null
        sleep 2
    fi

    UI_PID=$(lsof -ti:$UI_PORT)
    if [ ! -z "$UI_PID" ]; then
        kill "$UI_PID" 2>/dev/null
        sleep 1
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Temporal server stopped"
}

restart_temporal() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarting Temporal server..."
    stop_temporal
    sleep 3
    start_temporal
}

status_temporal() {
    if check_temporal; then
        GRPC_PID=$(lsof -ti:$GRPC_PORT)
        echo "✅ Temporal server is running (PID: $GRPC_PID)"
        echo "   gRPC Port: $GRPC_PORT"
        echo "   UI Port: $UI_PORT"
        echo "   Web UI: http://localhost:$UI_PORT"

        # Check for workflows
        WORKFLOW_COUNT=$(temporal workflow list --namespace default 2>/dev/null | grep -c "WorkflowId" || echo "0")
        echo "   Active Workflows: $WORKFLOW_COUNT"
    else
        echo "❌ Temporal server is NOT running"
    fi
}

check_and_restart() {
    if ! check_temporal; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ⚠️  Temporal server is down, attempting restart..."
        start_temporal
    fi
}

case "$1" in
    start)
        start_temporal
        ;;
    stop)
        stop_temporal
        ;;
    restart)
        restart_temporal
        ;;
    status)
        status_temporal
        ;;
    check)
        check_and_restart
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|check}"
        exit 1
        ;;
esac
