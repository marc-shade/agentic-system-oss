#!/bin/bash
# Enhanced Memory System Status Check for Statusline
# Returns: 🧠<icon><count> where icon indicates activity state

# Detect storage base based on platform
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS
    MEMORY_DB="/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/memory.db"
else
    # Linux
    MEMORY_DB="/home/marc/agentic-system/databases/enhanced_memory/memory.db"
fi

if [ ! -f "$MEMORY_DB" ]; then
    echo "🧠❌"
    exit 1
fi

# Count total entities in memory
COUNT=$(sqlite3 "$MEMORY_DB" "SELECT COUNT(*) FROM entities;" 2>/dev/null)

if [ -z "$COUNT" ] || [ "$COUNT" = "0" ]; then
    echo "🧠💤0"
    exit 0
fi

# Check for recent activity (last 5 minutes)
RECENT=$(sqlite3 "$MEMORY_DB" "SELECT COUNT(*) FROM entities WHERE datetime(last_accessed) > datetime('now', '-5 minutes');" 2>/dev/null)

if [ "$RECENT" -gt 0 ]; then
    # Active: recently accessed
    echo "🧠🔄$COUNT"
elif [ "$COUNT" -gt 0 ]; then
    # Idle: has data but no recent access
    echo "🧠💤$COUNT"
else
    # No data
    echo "🧠💤0"
fi
