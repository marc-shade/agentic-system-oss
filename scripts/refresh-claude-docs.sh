#!/bin/bash
# refresh-claude-docs.sh - Automatically refresh Claude Code documentation in enhanced-memory
#
# Purpose: Keep local Claude Code documentation vectorized and up-to-date
# Schedule: Run weekly via cron (recommended: Sunday at 3 AM)
#
# Usage:
#   ./refresh-claude-docs.sh           # Refresh all docs
#   ./refresh-claude-docs.sh --force   # Force refresh even if recent
#
# Crontab entry:
#   0 3 * * 0 /Volumes/SSDRAID0/agentic-system/scripts/refresh-claude-docs.sh >> /Volumes/SSDRAID0/agentic-system/logs/claude-docs-refresh.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTIC_BASE="${SCRIPT_DIR}/.."
LOG_DIR="${AGENTIC_BASE}/logs"
MARKER_FILE="${LOG_DIR}/.claude-docs-last-refresh"

# Create log directory if needed
mkdir -p "${LOG_DIR}"

# Timestamp
echo "=============================================="
echo "Claude Code Documentation Refresh"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# Check if recent refresh (within 6 days) unless --force
if [[ -f "${MARKER_FILE}" && "$*" != *"--force"* ]]; then
    LAST_REFRESH=$(cat "${MARKER_FILE}")
    DAYS_AGO=$(( ($(date +%s) - $(date -j -f "%Y-%m-%d" "${LAST_REFRESH}" +%s 2>/dev/null || echo 0)) / 86400 ))

    if [[ ${DAYS_AGO} -lt 6 ]]; then
        echo "Skipping: Last refresh was ${DAYS_AGO} days ago (${LAST_REFRESH})"
        echo "Use --force to override"
        exit 0
    fi
fi

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Run the documentation loader
echo ""
echo "Loading Claude Code documentation..."
cd "${AGENTIC_BASE}/scripts"

# Try the comprehensive loader first, fallback to simpler one
if [[ -f "load_all_claude_docs.py" ]]; then
    python3 load_all_claude_docs.py
    STATUS=$?
elif [[ -f "load_claude_code_docs.py" ]]; then
    python3 load_claude_code_docs.py
    STATUS=$?
else
    echo "ERROR: No documentation loader script found"
    exit 1
fi

if [[ ${STATUS} -eq 0 ]]; then
    # Update marker
    date '+%Y-%m-%d' > "${MARKER_FILE}"

    echo ""
    echo "=============================================="
    echo "Documentation refresh complete!"
    echo "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=============================================="
else
    echo ""
    echo "ERROR: Documentation refresh failed with status ${STATUS}"
    exit ${STATUS}
fi
