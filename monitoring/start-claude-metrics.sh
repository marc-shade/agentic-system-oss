#!/bin/bash
# Start Claude Code Metrics Exporter


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

SCRIPT_PATH="$STORAGE_BASE/monitoring/claude-metrics-exporter.py"
LOG_FILE="$STORAGE_BASE/monitoring/claude-metrics-exporter.log"

# Check if already running
if pgrep -f "claude-metrics-exporter.py" > /dev/null; then
    echo "Claude metrics exporter is already running"
    exit 0
fi

# Start exporter
echo "Starting Claude Code metrics exporter..."
nohup python3 "$SCRIPT_PATH" > "$LOG_FILE" 2>&1 &

PID=$!
echo "Metrics exporter started with PID: $PID"
echo "Log file: $LOG_FILE"
echo "Metrics endpoint: http://localhost:4318/v1/metrics"
echo "Health check: http://localhost:4318/health"

# Wait and verify
sleep 2
if pgrep -f "claude-metrics-exporter.py" > /dev/null; then
    echo "✅ Claude metrics exporter is running successfully"
else
    echo "❌ Metrics exporter failed to start. Check logs at: $LOG_FILE"
    exit 1
fi
