#!/bin/bash
#
# Statusline Communication Status
#
# Displays node communication status in Claude Code statusline:
# - Unread messages from other nodes
# - Pending actions requiring attention
# - Active communication channels
#
# Output format: "📡 3 msgs • 1 action"
#

# Auto-detect storage base

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

if [ -d "$STORAGE_BASE" ]; then
    STORAGE_BASE="$STORAGE_BASE"
elif [ -d "$STORAGE_BASE" ]; then
    STORAGE_BASE="$STORAGE_BASE"
elif [ -d "/Users/marc/agentic-system" ]; then
    STORAGE_BASE="/Users/marc/agentic-system"
else
    echo "📡 offline"
    exit 0
fi

STATUS_FILE="$STORAGE_BASE/databases/cluster/comm_status.json"

# Check if status file exists and is recent (< 2 minutes old)
if [ ! -f "$STATUS_FILE" ]; then
    echo "📡 inactive"
    exit 0
fi

# Check if file is recent
FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$STATUS_FILE" 2>/dev/null || stat -f %m "$STATUS_FILE" 2>/dev/null || echo 0) ))
if [ $FILE_AGE -gt 120 ]; then
    echo "📡 stale"
    exit 0
fi

# Parse status file
if command -v jq &> /dev/null; then
    UNREAD=$(jq -r '.unread_messages // 0' "$STATUS_FILE" 2>/dev/null)
    PENDING=$(jq -r '.pending_actions // 0' "$STATUS_FILE" 2>/dev/null)
    RECEIVED=$(jq -r '.stats.messages_received // 0' "$STATUS_FILE" 2>/dev/null)
    SENT=$(jq -r '.stats.messages_sent // 0' "$STATUS_FILE" 2>/dev/null)
else
    # Fallback without jq
    UNREAD=$(grep -oP '"unread_messages":\s*\K\d+' "$STATUS_FILE" 2>/dev/null || echo 0)
    PENDING=$(grep -oP '"pending_actions":\s*\K\d+' "$STATUS_FILE" 2>/dev/null || echo 0)
    RECEIVED=0
    SENT=0
fi

# Build status string
if [ "$UNREAD" -gt 0 ] || [ "$PENDING" -gt 0 ]; then
    # Active communications
    OUTPUT="📡"

    if [ "$UNREAD" -gt 0 ]; then
        OUTPUT="$OUTPUT $UNREAD msg"
        if [ "$UNREAD" -gt 1 ]; then
            OUTPUT="${OUTPUT}s"
        fi
    fi

    if [ "$PENDING" -gt 0 ]; then
        if [ "$UNREAD" -gt 0 ]; then
            OUTPUT="$OUTPUT •"
        fi
        OUTPUT="$OUTPUT $PENDING action"
        if [ "$PENDING" -gt 1 ]; then
            OUTPUT="${OUTPUT}s"
        fi
    fi

    echo "$OUTPUT"
else
    # All quiet
    if [ "$RECEIVED" -gt 0 ] || [ "$SENT" -gt 0 ]; then
        echo "📡 connected"
    else
        echo "📡 listening"
    fi
fi
