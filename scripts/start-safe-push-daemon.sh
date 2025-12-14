#!/bin/bash
# Start Safe GitHub Push Daemon
# Part of the GitHub Hygiene System

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Source storage detection
if [ -f "$SCRIPT_DIR/detect-storage.sh" ]; then
    source "$SCRIPT_DIR/detect-storage.sh"
fi

# Set defaults
STORAGE_BASE="${STORAGE_BASE:-/Volumes/SSDRAID0/agentic-system}"
INTERVAL="${1:-300}"  # Default: 5 minutes

echo "Starting Safe GitHub Push Daemon..."
echo "  Repository: $STORAGE_BASE"
echo "  Interval: ${INTERVAL}s"

# Check if daemon is already running
PID_FILE="/tmp/safe-github-push-daemon.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Daemon already running (PID: $OLD_PID)"
        exit 1
    fi
fi

# Run the daemon
cd "$STORAGE_BASE"
nohup python3 "$STORAGE_BASE/intelligent-agents/safe_github_push_daemon.py" \
    --repo "$STORAGE_BASE" \
    --interval "$INTERVAL" \
    > "$STORAGE_BASE/logs/safe_github_push.log" 2>&1 &

DAEMON_PID=$!
echo $DAEMON_PID > "$PID_FILE"

echo "Daemon started (PID: $DAEMON_PID)"
echo "Logs: $STORAGE_BASE/logs/safe_github_push.log"
echo ""
echo "To stop: kill $DAEMON_PID"
echo "To check status: ps aux | grep safe_github_push_daemon"
