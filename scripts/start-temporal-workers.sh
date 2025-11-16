#!/bin/bash
# Start Temporal workflow workers for autonomous operations

set -e

# Add Temporal to PATH
export PATH="/home/marc/.temporalio/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Storage paths
STORAGE_BASE="/home/marc/agentic-system"
LOG_DIR="$STORAGE_BASE/logs"

mkdir -p "$LOG_DIR"

echo "Starting Temporal workflow workers..."
echo "Logs: $LOG_DIR/temporal-workers.log"

# Start all workers
exec python3 "$STORAGE_BASE/workflows/temporal/start_all_workers.py" \
  >> "$LOG_DIR/temporal-workers.log" \
  2>&1
