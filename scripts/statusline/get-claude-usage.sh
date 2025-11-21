#!/bin/bash
# Get actual usage from Claude Code's /usage command via tmux

TMUX_SESSION="claude-usage-check"
OUTPUT_FILE="/tmp/claude_usage_output.txt"

# Kill old session if exists
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null

# Start headless Claude Code session
tmux new-session -d -s "$TMUX_SESSION" "claude --dangerously-skip-permissions" 2>/dev/null

# Wait for it to start
sleep 3

# Send /usage command
tmux send-keys -t "$TMUX_SESSION" "/usage" Enter

# Wait for output
sleep 3

# Capture the pane output
tmux capture-pane -t "$TMUX_SESSION" -p > "$OUTPUT_FILE"

# Debug: show what we captured
# cat "$OUTPUT_FILE" >&2

# Parse the weekly percentage (look for pattern like "54% used")
WEEKLY_PCT=$(grep -i "current week" "$OUTPUT_FILE" -A 2 | grep -oP '\d+(?=% used)' | head -1)

# Parse session percentage
SESSION_PCT=$(grep -i "current session" "$OUTPUT_FILE" -A 2 | grep -oP '\d+(?=% used)' | head -1)

# Kill the tmux session
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null

# Output JSON
if [ -n "$WEEKLY_PCT" ]; then
    # Convert to percentage REMAINING (not used)
    WEEKLY_REMAINING=$((100 - WEEKLY_PCT))
    SESSION_REMAINING=$((100 - SESSION_PCT))
    echo "{\"session_remaining\": ${SESSION_REMAINING}, \"weekly_remaining\": ${WEEKLY_REMAINING}, \"weekly_used\": ${WEEKLY_PCT}}"
else
    # Fallback if parsing failed - show what we got for debugging
    echo "{\"error\": \"Failed to parse\", \"output_preview\": \"$(head -20 $OUTPUT_FILE | tr '\n' ' ' | cut -c1-100)\"}"
fi

# Clean up
rm -f "$OUTPUT_FILE"
