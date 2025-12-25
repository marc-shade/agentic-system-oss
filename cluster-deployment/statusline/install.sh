#!/bin/bash
# Install statusline for Claude Code on any cluster node
# Usage: ./install.sh

CLAUDE_DIR="$HOME/.claude"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing Pixel statusline to $CLAUDE_DIR..."

# Copy files
cp "$SCRIPT_DIR/statusline-collector.py" "$CLAUDE_DIR/"
cp "$SCRIPT_DIR/statusline-command.sh" "$CLAUDE_DIR/"
chmod +x "$CLAUDE_DIR/statusline-command.sh"

# Check if settings.json exists and has statusLine configured
SETTINGS="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS" ]; then
    if grep -q "statusLine" "$SETTINGS"; then
        echo "✓ statusLine already configured in settings.json"
    else
        echo "⚠ Add to $SETTINGS:"
        echo '  "statusLine": {"command": "~/.claude/statusline-command.sh"}'
    fi
else
    echo "⚠ Create $SETTINGS with:"
    echo '{"statusLine": {"command": "~/.claude/statusline-command.sh"}}'
fi

echo "✓ Statusline installed! Restart Claude Code to activate."
