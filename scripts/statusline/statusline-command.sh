#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Unified Intelligent Agentic Statusline for Claude Code
# Combines all features for comprehensive AGI observability
# ═══════════════════════════════════════════════════════════════════════════════

# Colors
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"

# Read JSON input from stdin
INPUT=$(cat)
MODEL=$(echo "$INPUT" | jq -r '.model.display_name // "Claude"' 2>/dev/null)
CWD=$(echo "$INPUT" | jq -r '.workspace.current_dir // .cwd // empty' 2>/dev/null)
CWD=${CWD:-$(pwd)}
DIR=$(basename "$CWD")

# Branded directory names
case "$DIR" in
    "claude-code-flow") DIR="Claude Flow" ;;
    "intelligent-agents") DIR="Agents" ;;
    "mcp-servers") DIR="MCP" ;;
    "agentic-system") DIR="Agentic" ;;
    "enhanced-memory-mcp") DIR="Memory" ;;
esac

# Get git branch
BRANCH=""
if git -C "$CWD" rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git -C "$CWD" --no-optional-locks branch --show-current 2>/dev/null)
fi

# ═══════════════════════════════════════════════════════════════════════════════
# Section 1: Model & Workspace
# ═══════════════════════════════════════════════════════════════════════════════
printf "${BOLD}${MAGENTA}$MODEL${RESET} ${DIM}in${RESET} ${CYAN}$DIR${RESET}"
[ -n "$BRANCH" ] && printf " ${DIM}on${RESET} ${YELLOW}$BRANCH${RESET}"

# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: Agentic System Insights (from unified collector)
# ═══════════════════════════════════════════════════════════════════════════════
COLLECTOR="$HOME/.claude/statusline-collector.py"

if [ -x "$COLLECTOR" ] || [ -f "$COLLECTOR" ]; then
    AGENTIC_STATUS=$(timeout 4 python3 "$COLLECTOR" compact 2>/dev/null)

    if [ -n "$AGENTIC_STATUS" ]; then
        printf " ${DIM}│${RESET} "
        printf "%b" "$AGENTIC_STATUS"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: Claude-Flow Project Integration (if in a Claude-Flow project)
# ═══════════════════════════════════════════════════════════════════════════════
FLOW_DIR="$CWD/.claude-flow"

if [ -d "$FLOW_DIR" ]; then
    # Swarm topology
    if [ -f "$FLOW_DIR/swarm-config.json" ]; then
        STRATEGY=$(jq -r '.defaultStrategy // empty' "$FLOW_DIR/swarm-config.json" 2>/dev/null)
        if [ -n "$STRATEGY" ]; then
            case "$STRATEGY" in
                "balanced") TOPO="mesh" ;;
                "conservative") TOPO="hier" ;;
                "aggressive") TOPO="ring" ;;
                *) TOPO="$STRATEGY" ;;
            esac
            printf " ${DIM}│${RESET} ${MAGENTA}$TOPO${RESET}"

            AGENT_COUNT=$(jq -r '.agentProfiles | length' "$FLOW_DIR/swarm-config.json" 2>/dev/null)
            [ -n "$AGENT_COUNT" ] && [ "$AGENT_COUNT" != "null" ] && [ "$AGENT_COUNT" -gt 0 ] && \
                printf "${MAGENTA}:${AGENT_COUNT}a${RESET}"
        fi
    fi

    # Performance metrics
    if [ -f "$FLOW_DIR/metrics/task-metrics.json" ]; then
        SUCCESS_RATE=$(jq -r '
            (map(select(.success == true)) | length) as $s |
            (length) as $t |
            if $t > 0 then ($s / $t * 100 | floor) else 0 end
        ' "$FLOW_DIR/metrics/task-metrics.json" 2>/dev/null)

        if [ -n "$SUCCESS_RATE" ] && [ "$SUCCESS_RATE" != "null" ] && [ "$SUCCESS_RATE" -gt 0 ]; then
            if [ "$SUCCESS_RATE" -gt 80 ]; then
                printf " ${GREEN}${SUCCESS_RATE}%%${RESET}"
            elif [ "$SUCCESS_RATE" -ge 60 ]; then
                printf " ${YELLOW}${SUCCESS_RATE}%%${RESET}"
            else
                printf " ${RED}${SUCCESS_RATE}%%${RESET}"
            fi
        fi
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════════
# Final: NES Corgi Pixel signature!
# ═══════════════════════════════════════════════════════════════════════════════
printf " ${DIM}│${RESET} ${YELLOW}Pixel${RESET}"

echo
