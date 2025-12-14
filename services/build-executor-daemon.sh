#!/bin/bash
# Build Executor Daemon Script
# Runs the build executor as a background daemon

set -e

# Configuration

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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$STORAGE_BASE/.venv"
PYTHON="${VENV_DIR}/bin/python3"
EXECUTOR="${SCRIPT_DIR}/build_executor.py"
PID_FILE="$STORAGE_BASE/logs/build-executor.pid"
LOG_DIR="$STORAGE_BASE/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Run: python3 -m venv $VENV_DIR && $VENV_DIR/bin/pip install redis docker"
    exit 1
fi

# Function to check if daemon is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start daemon
start_daemon() {
    if is_running; then
        echo "Build executor is already running (PID $(cat $PID_FILE))"
        exit 1
    fi

    echo "Starting build executor daemon..."

    # Start executor in background
    nohup "$PYTHON" "$EXECUTOR" \
        >> "$LOG_DIR/build_executor.log" 2>&1 &

    PID=$!
    echo $PID > "$PID_FILE"

    # Wait a moment to ensure it started
    sleep 2

    if is_running; then
        echo "Build executor started successfully (PID $PID)"
    else
        echo "Failed to start build executor"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Function to stop daemon
stop_daemon() {
    if ! is_running; then
        echo "Build executor is not running"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    echo "Stopping build executor (PID $PID)..."

    # Send SIGTERM for graceful shutdown
    kill -TERM "$PID"

    # Wait for process to exit (up to 60 seconds)
    for i in {1..60}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            echo "Build executor stopped gracefully"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
    done

    # Force kill if still running
    echo "Process did not stop gracefully, forcing..."
    kill -KILL "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "Build executor stopped"
}

# Function to restart daemon
restart_daemon() {
    echo "Restarting build executor..."
    if is_running; then
        stop_daemon
    fi
    sleep 2
    start_daemon
}

# Function to show status
show_status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "Build executor is running (PID $PID)"

        # Show health check
        echo ""
        echo "Health check:"
        "$PYTHON" "$EXECUTOR" health 2>/dev/null || echo "Health check failed"
    else
        echo "Build executor is not running"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    LINES=${1:-50}
    tail -n "$LINES" -f "$LOG_DIR/build_executor.log"
}

# Main command handler
case "${1:-}" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        restart_daemon
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-50}"
        ;;
    health)
        "$PYTHON" "$EXECUTOR" health
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the build executor daemon"
        echo "  stop     - Stop the build executor daemon"
        echo "  restart  - Restart the build executor daemon"
        echo "  status   - Show daemon status"
        echo "  logs     - Show daemon logs (tail -f)"
        echo "  health   - Run health check"
        exit 1
        ;;
esac
