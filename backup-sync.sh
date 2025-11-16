#!/bin/bash
# Agentic System Backup Sync - SSDRAID0 to FILES
# Runs hourly to backup hot data to cold storage
# Usage: Run manually or via cron

set -e

HOT_DATA="/mnt/agentic-system"
COLD_DATA="/Volumes/FILES/agentic-system"
LOG_FILE="/Volumes/FILES/agentic-system/backups/sync.log"

# Check if SSDRAID0 is available
if [ ! -d "$HOT_DATA" ]; then
    echo "$(date): ⚠️  SSDRAID0 not available, skipping backup" >> "$LOG_FILE"
    exit 1
fi

# Create backup directory
mkdir -p "$COLD_DATA/backups"

# Log start
echo "$(date): Starting backup sync from SSDRAID0 to FILES..." >> "$LOG_FILE"

# Sync databases (critical data)
if [ -d "$HOT_DATA/databases" ]; then
    rsync -av --delete "$HOT_DATA/databases/" "$COLD_DATA/backups/databases/" >> "$LOG_FILE" 2>&1
    echo "$(date): ✅ Databases synced" >> "$LOG_FILE"
fi

# Sync agent memory (important data)
if [ -d "$HOT_DATA/agent-memory" ]; then
    rsync -av --delete "$HOT_DATA/agent-memory/" "$COLD_DATA/backups/agent-memory/" >> "$LOG_FILE" 2>&1
    echo "$(date): ✅ Agent memory synced" >> "$LOG_FILE"
fi

# Sync MCP state (configuration data)
if [ -d "$HOT_DATA/mcp-state" ]; then
    rsync -av --delete "$HOT_DATA/mcp-state/" "$COLD_DATA/backups/mcp-state/" >> "$LOG_FILE" 2>&1
    echo "$(date): ✅ MCP state synced" >> "$LOG_FILE"
fi

# Note: Voice cache and sensory data are not backed up (easily regenerated)

# Log completion
echo "$(date): ✅ Backup sync completed successfully" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Keep only last 100 lines of log
tail -n 100 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

exit 0
