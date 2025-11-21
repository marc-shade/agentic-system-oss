#!/bin/bash
# PreToolUse Hook - Intelligent pre-flight checks and context loading
# Fires before each tool execution to enhance agentic awareness

# Read hook input from stdin
INPUT=$(cat)

# Extract tool information
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('tool_name', 'unknown'))" 2>/dev/null || echo "unknown")
TOOL_PARAMS=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(json.dumps(data.get('parameters', {})))" 2>/dev/null || echo "{}")

# Log pre-tool event (non-blocking)
echo "{\"event\": \"pre_tool_use\", \"node\": \"macpro51\", \"tool\": \"$TOOL_NAME\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/tool-usage.log 2>/dev/null || true

# Safety checks for destructive Bash commands
if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$TOOL_PARAMS" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('command', ''))" 2>/dev/null)

    # Check for EXTREMELY dangerous patterns that should be blocked
    if echo "$COMMAND" | grep -qE "rm\s+-rf\s+/[^/]|dd\s+.*of=/dev/sd|mkfs\.|fdisk\s+/dev/sd|parted\s+/dev/sd.*rm"; then
        echo "{\"event\": \"dangerous_command_blocked\", \"command\": \"$COMMAND\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/safety-warnings.log 2>/dev/null || true
        echo "🛑 BLOCKED: Extremely dangerous command detected!" >&2
        echo "Command: $COMMAND" >&2
        echo "This command could cause irreversible data loss." >&2
        exit 2  # Exit code 2 blocks tool execution
    fi

    # Check for potentially dangerous patterns (log warning but allow)
    if echo "$COMMAND" | grep -qE "rm\s+-rf|dd\s+|mkfs|fdisk|parted"; then
        echo "{\"event\": \"dangerous_command_warned\", \"command\": \"$COMMAND\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/safety-warnings.log 2>/dev/null || true
        echo "⚠️  WARNING: Potentially dangerous command detected" >&2
        echo "Command: $COMMAND" >&2
    fi
fi

# Context loading for Read/Edit/Write operations
if [ "$TOOL_NAME" = "Read" ] || [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$TOOL_PARAMS" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('file_path', ''))" 2>/dev/null)

    # Log file operations for memory system
    if [ -n "$FILE_PATH" ]; then
        echo "{\"event\": \"file_operation\", \"tool\": \"$TOOL_NAME\", \"file\": \"$FILE_PATH\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/file-operations.log 2>/dev/null || true
    fi
fi

# Return success (hooks should not block execution)
exit 0
