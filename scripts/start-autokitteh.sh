#!/bin/bash
# Start AutoKitteh workflow automation server
# Runs on default port (typically 9980)

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

# AutoKitteh binary location
AK_BIN="$STORAGE_BASE/autokitteh-source/bin/ak"

# Database and log directories
STORAGE_BASE="$STORAGE_BASE"
DB_DIR="$STORAGE_BASE/databases/autokitteh"
LOG_DIR="$STORAGE_BASE/logs"

mkdir -p "$DB_DIR"
mkdir -p "$LOG_DIR"

# Set AutoKitteh data directory
export AK_HOME="$DB_DIR"

echo "Starting AutoKitteh server..."
echo "Database: $DB_DIR"
echo "Logs: $LOG_DIR/autokitteh.log"

# Start in dev mode for easier debugging
exec "$AK_BIN" up --mode dev \
  >> "$LOG_DIR/autokitteh.log" \
  2>&1
