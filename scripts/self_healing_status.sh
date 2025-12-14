#!/bin/bash
# Check Self-Healing Monitor status


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

PID_FILE="/tmp/self_healing_monitor.pid"
LOG_FILE="$STORAGE_BASE/logs/self_healing.log"
DAEMON_LOG="$STORAGE_BASE/logs/self_healing_daemon.log"
RESULTS_FILE="$STORAGE_BASE/logs/self_healing_results.jsonl"

echo "Self-Healing Monitor Status"
echo "============================="
echo ""

# Check if running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Status: ✅ RUNNING (PID: $PID)"

        # Show last run time
        if [ -f "$DAEMON_LOG" ]; then
            LAST_RUN=$(tail -n 20 "$DAEMON_LOG" | grep "Running self-healing check" | tail -1)
            if [ -n "$LAST_RUN" ]; then
                echo "Last Check: $LAST_RUN"
            fi
        fi
    else
        echo "Status: ❌ NOT RUNNING (stale PID)"
    fi
else
    echo "Status: ❌ NOT RUNNING"
fi

echo ""

# Show recent healing results
if [ -f "$RESULTS_FILE" ]; then
    HEALED_COUNT=$(grep '"healed": true' "$RESULTS_FILE" | wc -l | xargs)
    TOTAL_COUNT=$(wc -l < "$RESULTS_FILE" | xargs)

    echo "Healing History:"
    echo "  Total errors encountered: $TOTAL_COUNT"
    echo "  Successfully healed: $HEALED_COUNT"
    echo ""

    # Show last 5 healing attempts
    echo "Last 5 Healing Attempts:"
    tail -5 "$RESULTS_FILE" | while read line; do
        ERROR_TYPE=$(echo "$line" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['error']['error_type'])")
        HEALED=$(echo "$line" | python3 -c "import sys, json; data=json.load(sys.stdin); print('✅' if data['healed'] else '❌')")
        MESSAGE=$(echo "$line" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['message'][:60])")
        echo "  $HEALED $ERROR_TYPE: $MESSAGE"
    done
else
    echo "No healing history yet"
fi

echo ""
echo "Logs:"
echo "  Main: $LOG_FILE"
echo "  Daemon: $DAEMON_LOG"
echo "  Results: $RESULTS_FILE"
