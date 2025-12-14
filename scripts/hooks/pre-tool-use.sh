#!/bin/bash
# PreToolUse Hook - TPU-Enhanced intelligent pre-flight checks
# Uses TPU Warm Service for intent classification and context loading
# User-level operational hook (not project-specific)

exec 2>/dev/null  # Suppress stderr for clean operation

# Read hook input from stdin
INPUT=$(cat)

# Extract tool information
TOOL_NAME=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('tool_name', 'unknown'))" 2>/dev/null || echo "unknown")
TOOL_PARAMS=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(json.dumps(data.get('parameters', {})))" 2>/dev/null || echo "{}")

# TPU Intent Classification for complex operations (via TPU Warm Service)
# Only for Task tool (agent spawning) - classify intent to optimize routing
if [ "$TOOL_NAME" = "Task" ]; then
    TASK_DESC=$(echo "$TOOL_PARAMS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt','')[:300])" 2>/dev/null || echo "")
    if [ -n "$TASK_DESC" ]; then
        INTENT=$(python3 -c "
import sys
sys.path.insert(0, '/mnt/agentic-system/scripts/hooks')
try:
    from tpu_importance import classify_intent
    result = classify_intent('''$TASK_DESC''')
    print(result.get('intent', 'general'))
except:
    print('general')
" 2>/dev/null || echo "general")
        # Log classified intent for analytics
        echo "{\"pre_tool\":\"$TOOL_NAME\",\"intent\":\"$INTENT\",\"ts\":\"$(date -Is)\"}" >> /home/marc/agentic-system/logs/intent-classification.log &
    fi
fi

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
