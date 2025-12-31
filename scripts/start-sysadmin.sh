#!/bin/bash
# Start SysAdmin Monitoring System
# This script ensures the sysadmin worker is running

WORKER_SCRIPT="/Volumes/SSDRAID0/agentic-system/workflows/temporal/sysadmin_worker.py"
LOG_FILE="/tmp/sysadmin_worker.log"
PID_FILE="/tmp/sysadmin_worker.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "SysAdmin worker already running (PID: $PID)"
        exit 0
    fi
fi

# Check if Temporal is running
if ! pgrep -f "temporal server" > /dev/null; then
    echo "ERROR: Temporal server not running. Start Temporal first."
    exit 1
fi

# Start the worker
echo "Starting SysAdmin worker..."
cd /Volumes/SSDRAID0/agentic-system/workflows/temporal
nohup python3 sysadmin_worker.py > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

sleep 3

if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
    echo "SysAdmin worker started (PID: $(cat $PID_FILE))"
    echo "Log: $LOG_FILE"
    echo ""
    echo "Features enabled:"
    echo "  - Service health monitoring (every 60s)"
    echo "  - Auto-recovery with exponential backoff"
    echo "  - Development mode detection"
    echo "  - Arduino LED status updates"
else
    echo "ERROR: Failed to start SysAdmin worker"
    cat "$LOG_FILE"
    exit 1
fi
