#!/bin/bash
# UserPromptSubmit Hook - Intelligent context injection and intent analysis
# Fires before Claude processes user prompts

# Read hook input from stdin
INPUT=$(cat)

# Extract user prompt
USER_PROMPT=$(echo "$INPUT" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('prompt', ''))" 2>/dev/null || echo "")

# Log prompt submission (without logging actual prompt content for privacy)
PROMPT_LENGTH=$(echo "$USER_PROMPT" | wc -c)
echo "{\"event\": \"prompt_submit\", \"node\": \"macpro51\", \"length\": $PROMPT_LENGTH, \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/claude-sessions.log 2>/dev/null || true

# Quick intent classification (non-blocking)
(
    # Classify prompt type for metrics
    INTENT="general"

    if echo "$USER_PROMPT" | grep -qiE "fix|bug|error|issue|problem|broken"; then
        INTENT="troubleshooting"
    elif echo "$USER_PROMPT" | grep -qiE "create|add|implement|build|write|make"; then
        INTENT="creation"
    elif echo "$USER_PROMPT" | grep -qiE "how|what|why|explain|describe|show|tell"; then
        INTENT="research"
    elif echo "$USER_PROMPT" | grep -qiE "test|verify|check|validate"; then
        INTENT="validation"
    elif echo "$USER_PROMPT" | grep -qiE "refactor|optimize|improve|enhance"; then
        INTENT="optimization"
    fi

    echo "{\"event\": \"intent_classified\", \"intent\": \"$INTENT\", \"timestamp\": \"$(date -Iseconds)\"}" >> /home/marc/agentic-system/logs/intents.log 2>/dev/null || true
) &

# Return success immediately
exit 0
