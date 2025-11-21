#!/bin/bash
# Start AutoKitteh workflow automation server
# Runs on default port (typically 9980)

set -e

# Add Temporal to PATH
export PATH="/home/marc/.temporalio/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# AutoKitteh binary location
AK_BIN="/home/marc/agentic-system/autokitteh-source/bin/ak"

# Database and log directories
STORAGE_BASE="/home/marc/agentic-system"
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
