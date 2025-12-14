#!/bin/bash
# Coral TPU MCP Server Startup Script
# NOTE: No stderr output - Claude Code treats stderr as errors

set -e


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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use shared venv which has mcp module installed
# coral-venv is Python 3.9 without mcp, so we always use .venv
VENV_PATH="$STORAGE_BASE/.venv"
LOG_FILE="${SCRIPT_DIR}/startup.log"

# Suppress all TensorFlow/TFLite logging
export TF_CPP_MIN_LOG_LEVEL=3
export ABSL_MIN_LOG_LEVEL=3

# Set Python path
export PYTHONPATH="${SCRIPT_DIR}/src"

# Activate venv
source "$VENV_PATH/bin/activate"

# Start the server (stderr goes to log, stdout is MCP protocol)
echo "[$(date)] Starting coral-tpu MCP server..." >> "$LOG_FILE"
# Use explicit venv python path to avoid system python
exec "$VENV_PATH/bin/python3" -m coral_tpu_mcp.server 2>> "$LOG_FILE"
