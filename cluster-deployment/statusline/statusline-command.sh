#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# 🐕 PIXEL THE CORGI - NES Retro Statusline for Claude Code
# Agentic System Status with 8-bit style
# Integrated with bash PS1 style: [user@hostname dir]
# ═══════════════════════════════════════════════════════════════════════════════

# NES Color Palette (authentic 8-bit feel)
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
# NES Primary Colors
NES_RED="\033[91m"      # Bright red (Mario red)
NES_GREEN="\033[92m"    # Bright green (Luigi green)
NES_YELLOW="\033[93m"   # Bright yellow (Star power)
NES_BLUE="\033[94m"     # Bright blue (Megaman blue)
NES_MAGENTA="\033[95m"  # Bright magenta (Kirby pink)
NES_CYAN="\033[96m"     # Bright cyan (Ice level)
NES_ORANGE="\033[33m"   # Orange (Corgi color!)
# Legacy colors for compatibility
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

# Get user and hostname for PS1-style format
USER=$(whoami)
HOSTNAME=$(hostname -s)

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
# Section 1: 🎮 Shell PS1 Style + Claude Model (NES + bash hybrid)
# ═══════════════════════════════════════════════════════════════════════════════
# PS1-style prefix: [user@hostname dir]
printf "${NES_GREEN}[${RESET}${NES_CYAN}$USER${RESET}${DIM}@${RESET}${NES_BLUE}$HOSTNAME${RESET} ${NES_YELLOW}$DIR${RESET}${NES_GREEN}]${RESET} "

# Pixel the Corgi + Model name
printf "${BOLD}${NES_ORANGE}🐕${RESET} ${BOLD}${NES_MAGENTA}$MODEL${RESET}"

# Git branch in bright yellow
[ -n "$BRANCH" ] && printf " ${NES_YELLOW}⎇ $BRANCH${RESET}"

# ═══════════════════════════════════════════════════════════════════════════════
# Section 2: ⚡ Agentic System Insights (8-bit power-up style)
# ═══════════════════════════════════════════════════════════════════════════════
COLLECTOR="$HOME/.claude/statusline-collector.py"

if [ -f "$COLLECTOR" ]; then
    # Make sure it's executable
    chmod +x "$COLLECTOR" 2>/dev/null

    # Try to collect status (with timeout to prevent hanging)
    AGENTIC_STATUS=$(timeout 5 python3 "$COLLECTOR" compact 2>/dev/null)

    if [ -n "$AGENTIC_STATUS" ]; then
        printf " ${DIM}│${RESET} "
        # Display agentic status with retro styling
        printf "%b" "$AGENTIC_STATUS"
    else
        # Fallback: minimal status if collector fails
        printf " ${DIM}│${RESET} ${NES_YELLOW}⚡ Agentic${RESET}"
    fi
else
    # Collector not found - show minimal info
    printf " ${DIM}│${RESET} ${GRAY}⚡ N/A${RESET}"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# Section 3: 🎯 Claude-Flow Project Integration (Level stats)
# ═══════════════════════════════════════════════════════════════════════════════
FLOW_DIR="$CWD/.claude-flow"

if [ -d "$FLOW_DIR" ]; then
    # Swarm topology (like different game levels)
    if [ -f "$FLOW_DIR/swarm-config.json" ]; then
        STRATEGY=$(jq -r '.defaultStrategy // empty' "$FLOW_DIR/swarm-config.json" 2>/dev/null)
        if [ -n "$STRATEGY" ]; then
            case "$STRATEGY" in
                "balanced") TOPO="◆mesh" ;;
                "conservative") TOPO="▲hier" ;;
                "aggressive") TOPO="●ring" ;;
                *) TOPO="$STRATEGY" ;;
            esac
            printf " ${DIM}│${RESET} ${NES_MAGENTA}$TOPO${RESET}"

            AGENT_COUNT=$(jq -r '.agentProfiles | length' "$FLOW_DIR/swarm-config.json" 2>/dev/null)
            [ -n "$AGENT_COUNT" ] && [ "$AGENT_COUNT" != "null" ] && [ "$AGENT_COUNT" -gt 0 ] && \
                printf "${NES_MAGENTA}×${AGENT_COUNT}${RESET}"
        fi
    fi

    # Performance metrics (like game score)
    if [ -f "$FLOW_DIR/metrics/task-metrics.json" ]; then
        SUCCESS_RATE=$(jq -r '
            (map(select(.success == true)) | length) as $s |
            (length) as $t |
            if $t > 0 then ($s / $t * 100 | floor) else 0 end
        ' "$FLOW_DIR/metrics/task-metrics.json" 2>/dev/null)

        if [ -n "$SUCCESS_RATE" ] && [ "$SUCCESS_RATE" != "null" ] && [ "$SUCCESS_RATE" -gt 0 ]; then
            if [ "$SUCCESS_RATE" -gt 80 ]; then
                printf " ${NES_GREEN}★${SUCCESS_RATE}%%${RESET}"
            elif [ "$SUCCESS_RATE" -ge 60 ]; then
                printf " ${NES_YELLOW}⚠${SUCCESS_RATE}%%${RESET}"
            else
                printf " ${NES_RED}✗${SUCCESS_RATE}%%${RESET}"
            fi
        fi
    fi
fi

# Final newline
echo
