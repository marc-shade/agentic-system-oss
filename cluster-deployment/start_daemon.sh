#!/bin/bash
# Start GitHub Node Daemon for mac-studio


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

DAEMON_DIR="$STORAGE_BASE/cluster-deployment"
LOG_FILE="/tmp/github-daemon-mac-studio.log"
PID_FILE="/tmp/github-daemon-mac-studio.pid"

# Check if daemon is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "✗ Daemon already running (PID: $OLD_PID)"
        echo "  To restart, first run: kill $OLD_PID"
        exit 1
    else
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
fi

# Check for GitHub token
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "✗ GITHUB_PERSONAL_ACCESS_TOKEN not set"
    echo ""
    echo "Set it with:"
    echo "  export GITHUB_PERSONAL_ACCESS_TOKEN=\"ghp_YOUR_TOKEN\""
    exit 1
fi

# Start daemon
cd "$DAEMON_DIR"
echo "Starting GitHub Node Daemon..."
echo "  Node ID: mac-studio"
echo "  Repo: marc-shade/agentic-cluster-comms"
echo "  Poll interval: 30 seconds"
echo "  Log file: $LOG_FILE"

nohup python3 github_node_daemon.py \
    --node-id mac-studio \
    --repo marc-shade/agentic-cluster-comms \
    --poll-interval 30 \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo $PID > "$PID_FILE"

# Wait a second and verify it started
sleep 2
if ps -p $PID > /dev/null 2>&1; then
    echo "✓ Daemon started successfully (PID: $PID)"
    echo ""
    echo "To monitor: tail -f $LOG_FILE"
    echo "To check status: ./check_daemon_status.sh"
    echo "To stop: kill $PID"
else
    echo "✗ Daemon failed to start"
    echo "Check logs: cat $LOG_FILE"
    exit 1
fi
