#!/bin/bash
# Session Consolidation Trigger Hook
# Tracks Claude Code sessions and triggers memory consolidation based on research findings
#
# Install: Add to Claude Code hooks configuration
# Trigger: Runs on session end

STATE_FILE="/mnt/agentic-system/databases/consolidation_state.json"
SESSION_THRESHOLD=10
LOG_FILE="/var/log/memory-consolidation.log"

# Ensure state file exists
if [ ! -f "$STATE_FILE" ]; then
    mkdir -p "$(dirname "$STATE_FILE")"
    echo '{"session_count": 0, "last_consolidation": null}' > "$STATE_FILE"
fi

# Increment session count
CURRENT_COUNT=$(jq -r '.session_count // 0' "$STATE_FILE")
NEW_COUNT=$((CURRENT_COUNT + 1))

# Update state file
jq --arg count "$NEW_COUNT" '.session_count = ($count | tonumber)' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

echo "[$(date)] Session $NEW_COUNT recorded" >> "$LOG_FILE"

# Check if we should trigger consolidation
if [ "$NEW_COUNT" -ge "$SESSION_THRESHOLD" ]; then
    echo "[$(date)] Session threshold ($SESSION_THRESHOLD) reached - triggering consolidation" >> "$LOG_FILE"

    # Send signal to daemon if running
    DAEMON_PID=$(pgrep -f "memory-consolidation-daemon.py")
    if [ -n "$DAEMON_PID" ]; then
        kill -USR1 "$DAEMON_PID"
        echo "[$(date)] Sent SIGUSR1 to daemon (PID: $DAEMON_PID)" >> "$LOG_FILE"
    else
        # Run consolidation directly via MCP if daemon not running
        echo "[$(date)] Daemon not running - consolidation will run on next daemon start" >> "$LOG_FILE"
    fi
fi

echo "Session recorded (count: $NEW_COUNT/$SESSION_THRESHOLD)"
