#!/bin/bash
#
# Capture Claude Code /usage output from tmux session
# This script looks for Claude Code running in tmux and captures any visible /usage output
#

# Find tmux session with 'claude' in it
CLAUDE_SESSION=$(tmux list-sessions 2>/dev/null | grep -i claude | cut -d: -f1 | head -1)

if [ -z "$CLAUDE_SESSION" ]; then
    # No tmux session found - Claude Code not running in tmux
    exit 0
fi

# Capture the pane output
OUTPUT=$(tmux capture-pane -p -t "$CLAUDE_SESSION" -S -3000 2>/dev/null)

# Look for usage output pattern
if echo "$OUTPUT" | grep -q "Current week (all models)"; then
    # Extract the percentage
    WEEK_PCT=$(echo "$OUTPUT" | grep "Current week (all models)" -A 1 | grep "% used" | grep -oP '\d+(?=% used)')

    # Extract reset time
    RESET_TIME=$(echo "$OUTPUT" | grep "Resets" | grep -oP 'Resets \K.*')

    if [ -n "$WEEK_PCT" ] && [ -n "$RESET_TIME" ]; then
        # Save to JSON for statusline
        cat > ~/.claude/usage_snapshot.json << EOF
{
    "timestamp": "$(date -Iseconds)",
    "week_percentage": $WEEK_PCT,
    "reset_time": "$RESET_TIME",
    "source": "tmux_capture"
}
EOF
        echo "✓ Captured usage: $WEEK_PCT% (resets $RESET_TIME)"
    fi
fi
