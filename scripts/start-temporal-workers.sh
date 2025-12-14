#!/bin/bash
# Start Temporal workflow workers for autonomous operations

set -e

# Add Temporal to PATH

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

export PATH="/home/marc/.temporalio/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Storage paths
STORAGE_BASE="$STORAGE_BASE"
LOG_DIR="$STORAGE_BASE/logs"

mkdir -p "$LOG_DIR"

echo "Starting Temporal workflow workers..."
echo "Logs: $LOG_DIR/temporal-workers.log"

# Start all workers
exec python3 "$STORAGE_BASE/workflows/temporal/start_all_workers.py" \
  >> "$LOG_DIR/temporal-workers.log" \
  2>&1
