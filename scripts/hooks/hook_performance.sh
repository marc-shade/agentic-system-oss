#!/bin/bash
# Hook Performance Shell Helpers
# Source this in hook scripts for timed execution
#
# Usage:
#   source /home/marc/agentic-system/scripts/hooks/hook_performance.sh
#   timed_exec "integration_name" "command" [timeout_ms]


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

HOOK_METRICS_LOG="$STORAGE_BASE/logs/hook-performance.jsonl"
HOOK_TIMEOUT_MS="${HOOK_TIMEOUT_MS:-500}"
HOOK_WARNING_MS="${HOOK_WARNING_MS:-100}"

# Get current timestamp in milliseconds
get_timestamp_ms() {
    python3 -c "import time; print(int(time.time() * 1000))" 2>/dev/null || date +%s000
}

# Log metrics (non-blocking)
log_hook_metric() {
    local hook_type="$1"
    local integration="$2"
    local time_ms="$3"
    local success="$4"
    local timeout="${5:-false}"
    local error="${6:-}"

    {
        echo "{\"hook_type\":\"$hook_type\",\"integration_name\":\"$integration\",\"execution_time_ms\":$time_ms,\"success\":$success,\"timeout\":$timeout,\"error\":\"$error\",\"timestamp\":$(date +%s.%N),\"node_id\":\"$(hostname)\"}" >> "$HOOK_METRICS_LOG"
    } 2>/dev/null &
}

# Execute command with timeout and metrics
# Usage: timed_exec "integration_name" "command" [timeout_ms] [hook_type]
timed_exec() {
    local integration="$1"
    local command="$2"
    local timeout_ms="${3:-$HOOK_TIMEOUT_MS}"
    local hook_type="${4:-unknown}"
    local timeout_s=$(echo "scale=3; $timeout_ms / 1000" | bc 2>/dev/null || echo "0.5")

    local start_ms=$(get_timestamp_ms)
    local success=true
    local timeout_flag=false
    local error=""
    local result=""

    # Execute with timeout
    result=$(timeout "${timeout_s}s" bash -c "$command" 2>&1)
    local exit_code=$?

    local end_ms=$(get_timestamp_ms)
    local duration_ms=$((end_ms - start_ms))

    # Check for timeout
    if [ $exit_code -eq 124 ]; then
        timeout_flag=true
        success=false
        error="timeout after ${timeout_ms}ms"
    elif [ $exit_code -ne 0 ]; then
        success=false
        error="exit code $exit_code"
    fi

    # Log metrics (background)
    log_hook_metric "$hook_type" "$integration" "$duration_ms" "$success" "$timeout_flag" "$error"

    # Warn if slow
    if [ "$duration_ms" -gt "$HOOK_WARNING_MS" ]; then
        echo "WARN: $integration took ${duration_ms}ms (>${HOOK_WARNING_MS}ms)" >&2
    fi

    # Return the result
    echo "$result"
    return $exit_code
}

# Run Python integration with timeout
# Usage: run_python_integration "module.function" "json_input" [timeout_ms]
run_python_integration() {
    local func="$1"
    local input="$2"
    local timeout_ms="${3:-300}"
    local hooks_dir="$STORAGE_BASE/scripts/hooks"

    timed_exec "$func" "echo '$input' | python3 -c \"
import sys, json
sys.path.insert(0, '$hooks_dir')
data = json.load(sys.stdin)
module, func = '$func'.rsplit('.', 1)
m = __import__(module)
result = getattr(m, func)(**data) if data else getattr(m, func)()
if result: print(json.dumps(result))
\" 2>/dev/null" "$timeout_ms"
}

# Async execution (fire and forget)
# Usage: async_exec "command"
async_exec() {
    local command="$1"
    {
        eval "$command"
    } &>/dev/null &
    disown 2>/dev/null
}
