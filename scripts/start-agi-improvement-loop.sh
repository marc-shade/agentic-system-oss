#!/bin/bash
#
# Start Autonomous Improvement Loop
# ==================================
#
# Starts the 24/7 AGI improvement daemon that continuously runs
# improvement cycles across all 6 AGI components.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGI_DIR="/mnt/agentic-system/intelligent-agents"
LOG_DIR="/mnt/agentic-system/logs"
PID_FILE="/tmp/agi_improvement_daemon.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "❌ AGI Improvement Daemon already running (PID: $PID)"
        exit 1
    else
        echo "⚠️  Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

echo "🚀 Starting AGI Autonomous Improvement Daemon..."
echo "   Location: $AGI_DIR"
echo "   Logs: $LOG_DIR/autonomous_improvement.log"

# Start daemon in background
cd "$AGI_DIR"
nohup python3 autonomous_improvement_daemon.py > "$LOG_DIR/daemon_stdout.log" 2>&1 &
DAEMON_PID=$!

# Save PID
echo "$DAEMON_PID" > "$PID_FILE"

echo "✅ AGI Improvement Daemon started (PID: $DAEMON_PID)"
echo ""
echo "Monitor logs with:"
echo "  tail -f $LOG_DIR/autonomous_improvement.log"
echo ""
echo "Stop daemon with:"
echo "  kill $DAEMON_PID"
echo "  # or"
echo "  $SCRIPT_DIR/stop-agi-improvement-loop.sh"
