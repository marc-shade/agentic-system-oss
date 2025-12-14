#!/bin/bash
# Autonomous Mode Kill Switch Management
#
# Controls whether Claude Code can execute tasks autonomously.
# The kill switch is a simple file - its presence enables autonomous mode.
#
# Usage:
#   autonomous-mode.sh enable   - Enable autonomous task execution
#   autonomous-mode.sh disable  - Immediately halt all autonomous execution
#   autonomous-mode.sh status   - Check current state
#   autonomous-mode.sh reset    - Reset circuit breaker after failures


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

KILL_SWITCH="$STORAGE_BASE/config/autonomous-mode-enabled"
STATE_FILE="$STORAGE_BASE/databases/task_processor_state.json"
LOG_FILE="/var/log/claude-task-processor.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
    enable)
        touch "$KILL_SWITCH"
        echo -e "${GREEN}Autonomous mode ENABLED${NC}"
        echo "Task processor will execute pending tasks on next timer trigger."
        echo ""
        echo "To trigger immediately: sudo systemctl start claude-task-processor.service"
        ;;

    disable)
        rm -f "$KILL_SWITCH"
        echo -e "${RED}Autonomous mode DISABLED${NC}"
        echo "No new tasks will be executed. Running tasks will complete."
        ;;

    status)
        echo "=== Autonomous Mode Status ==="
        echo ""

        if [ -f "$KILL_SWITCH" ]; then
            echo -e "Kill Switch: ${GREEN}ENABLED${NC} (file exists)"
        else
            echo -e "Kill Switch: ${RED}DISABLED${NC} (file missing)"
        fi

        echo ""

        if [ -f "$STATE_FILE" ]; then
            echo "Processor State:"
            jq -r '
                "  Last run: \(.last_run // "never")",
                "  Tasks today: \(.tasks_processed_today // 0)",
                "  Cost today: $\(.cost_today_usd // 0 | tostring | .[0:6])",
                "  Tasks this hour: \(.tasks_this_hour // 0)",
                "  Consecutive failures: \(.consecutive_failures // 0)"
            ' "$STATE_FILE" 2>/dev/null || echo "  (could not parse state file)"
        else
            echo "Processor State: No state file found"
        fi

        echo ""

        # Check timer status
        if systemctl is-active --quiet claude-task-processor.timer 2>/dev/null; then
            echo -e "Systemd Timer: ${GREEN}ACTIVE${NC}"
            NEXT_RUN=$(systemctl show claude-task-processor.timer --property=NextElapseUSecRealtime 2>/dev/null | cut -d= -f2)
            if [ -n "$NEXT_RUN" ] && [ "$NEXT_RUN" != "n/a" ]; then
                echo "  Next run: $NEXT_RUN"
            fi
        else
            echo -e "Systemd Timer: ${YELLOW}INACTIVE${NC} (not installed or not started)"
        fi

        echo ""

        # Check for pending tasks
        if [ -f ~/.claude/agent_runtime.db ]; then
            PENDING=$(sqlite3 ~/.claude/agent_runtime.db "SELECT COUNT(*) FROM tasks WHERE status = 'pending'" 2>/dev/null)
            echo "Pending Tasks: ${PENDING:-0}"
        fi
        ;;

    reset)
        if [ -f "$STATE_FILE" ]; then
            jq '.consecutive_failures = 0' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
            echo -e "${GREEN}Circuit breaker reset${NC}"
            echo "Consecutive failures counter set to 0."
        else
            echo "No state file to reset."
        fi
        ;;

    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -50 "$LOG_FILE"
        else
            echo "No log file found at $LOG_FILE"
            echo "Try: journalctl -u claude-task-processor -f"
        fi
        ;;

    install)
        echo "Installing systemd units..."
        sudo cp $STORAGE_BASE/config/claude-task-processor.service /etc/systemd/system/
        sudo cp $STORAGE_BASE/config/claude-task-processor.timer /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable claude-task-processor.timer
        sudo systemctl start claude-task-processor.timer
        echo -e "${GREEN}Installed and started!${NC}"
        echo ""
        systemctl status claude-task-processor.timer --no-pager
        ;;

    uninstall)
        echo "Removing systemd units..."
        sudo systemctl stop claude-task-processor.timer 2>/dev/null
        sudo systemctl disable claude-task-processor.timer 2>/dev/null
        sudo rm -f /etc/systemd/system/claude-task-processor.service
        sudo rm -f /etc/systemd/system/claude-task-processor.timer
        sudo systemctl daemon-reload
        rm -f "$KILL_SWITCH"
        echo -e "${YELLOW}Uninstalled${NC}"
        ;;

    run-now)
        echo "Triggering immediate task processing..."
        if [ -f "$KILL_SWITCH" ]; then
            $STORAGE_BASE/.venv/bin/python3 $STORAGE_BASE/scripts/task-processor-daemon.py
        else
            echo -e "${RED}Error: Autonomous mode is disabled${NC}"
            echo "Run: $0 enable"
            exit 1
        fi
        ;;

    dry-run)
        echo "Checking pending tasks (dry run)..."
        $STORAGE_BASE/.venv/bin/python3 $STORAGE_BASE/scripts/task-processor-daemon.py --dry-run
        ;;

    *)
        echo "Usage: $0 {enable|disable|status|reset|logs|install|uninstall|run-now|dry-run}"
        echo ""
        echo "Commands:"
        echo "  enable    - Enable autonomous task execution"
        echo "  disable   - Disable autonomous execution (kill switch)"
        echo "  status    - Show current state and pending tasks"
        echo "  reset     - Reset circuit breaker after failures"
        echo "  logs      - Show recent log entries"
        echo "  install   - Install and start systemd timer"
        echo "  uninstall - Remove systemd units"
        echo "  run-now   - Execute task processor immediately"
        echo "  dry-run   - Show pending tasks without executing"
        exit 1
        ;;
esac
