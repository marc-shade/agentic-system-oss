#!/bin/bash
# Temporal Server Startup Script for Autonomous System
# Runs Temporal with hot tier storage for performance


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

# Database on primary storage
DB_FILE="$STORAGE_BASE/databases/temporal/temporal.db"
UI_PORT=8233
GRPC_PORT=7233
METRICS_PORT=57271

# Namespace for autonomous workflows
NAMESPACE="default"

# Ensure directories exist
mkdir -p "$(dirname "$DB_FILE")"
mkdir -p "$STORAGE_BASE/logs"

# Start Temporal server
exec temporal server start-dev \
  --db-filename "$DB_FILE" \
  --ui-port "$UI_PORT" \
  --port "$GRPC_PORT" \
  --metrics-port "$METRICS_PORT" \
  --namespace "$NAMESPACE" \
  --log-level info \
  >> $STORAGE_BASE/logs/temporal-stdout.log \
  2>> $STORAGE_BASE/logs/temporal-stderr.log
