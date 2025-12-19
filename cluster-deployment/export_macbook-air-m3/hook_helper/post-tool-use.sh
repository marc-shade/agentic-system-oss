#!/bin/bash

# Post-Tool-Use Hook for Automatic Pet Care
# Cares for the pet based on normal workflow actions

# Get pet path
PET_PATH_FILE="$HOME/.claude/tamagotchi-path.txt"
if [ ! -f "$PET_PATH_FILE" ]; then
    exit 0
fi

PET_PATH=$(cat "$PET_PATH_FILE")

# Read tool input from stdin
TOOL_INPUT=$(cat)

# Extract tool name
TOOL_NAME=$(echo "$TOOL_INPUT" | jq -r '.tool_name')

# Random chance for automatic care (low probability to avoid spam)
RANDOM_NUM=$((RANDOM % 100))

case "$TOOL_NAME" in
    Read)
        # 10% chance to auto-feed after reading (coding is hungry work)
        if [ $RANDOM_NUM -lt 10 ]; then
            cd "$PET_PATH" && bun run --silent src/commands/pet-cli.ts feed cookie &> /dev/null
        fi
        ;;

    Edit|Write)
        # 15% chance to auto-play after successful edits
        if [ $RANDOM_NUM -lt 15 ]; then
            cd "$PET_PATH" && bun run --silent src/commands/pet-cli.ts play ball &> /dev/null
        fi
        ;;

    Bash)
        # Check if running tests
        COMMAND=$(echo "$TOOL_INPUT" | jq -r '.tool_input.command // empty')
        if echo "$COMMAND" | grep -qi "test"; then
            # 20% chance to auto-pet after tests
            if [ $RANDOM_NUM -lt 20 ]; then
                cd "$PET_PATH" && bun run --silent src/commands/pet-cli.ts pet &> /dev/null
            fi
        fi
        ;;
esac

# 5% chance to auto-clean (bath time!)
if [ $RANDOM_NUM -lt 5 ]; then
    cd "$PET_PATH" && bun run --silent src/commands/pet-cli.ts clean &> /dev/null
fi

exit 0
