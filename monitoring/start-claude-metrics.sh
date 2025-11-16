#!/bin/bash
# Start Claude Code Metrics Exporter

SCRIPT_PATH="/mnt/agentic-system/monitoring/claude-metrics-exporter.py"
LOG_FILE="/mnt/agentic-system/monitoring/claude-metrics-exporter.log"

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
