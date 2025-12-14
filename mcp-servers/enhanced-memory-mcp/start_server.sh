#!/bin/bash
# Enhanced Memory MCP Server Startup Script
# Runs migrations and starts the server
# NOTE: No stderr output - Claude Code treats stderr as errors

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${AGENTIC_SYSTEM_PATH:-/mnt/agentic-system}/.venv"
LOG_FILE="${SCRIPT_DIR}/startup.log"

# Suppress Python warnings
export PYTHONWARNINGS="ignore"

# Activate venv
source "$VENV_PATH/bin/activate"

cd "$SCRIPT_DIR"

# Run migrations first (redirect all output to log file)
echo "[$(date)] Running database migrations..." >> "$LOG_FILE"
python3 migrate_database.py >> "$LOG_FILE" 2>&1 || {
    echo "[$(date)] Migration warning - continuing" >> "$LOG_FILE"
}

# Start the server (stderr goes to log, stdout is MCP protocol)
echo "[$(date)] Starting enhanced-memory MCP server..." >> "$LOG_FILE"
exec python3 -W ignore server.py 2>> "$LOG_FILE"
