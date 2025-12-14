#!/bin/bash
# Agentic System Statusline - Comprehensive AGI Observability
# Provides real-time visibility into all agentic system components

set -o pipefail

# Configuration
STORAGE_BASE="${AGENTIC_ROOT:-/home/marc/agentic-system}"
MEMORY_DB="$STORAGE_BASE/mcp-servers/enhanced-memory-mcp/memory.db"
AGENT_RUNTIME_DB="$STORAGE_BASE/mcp-servers/agent-runtime-mcp/agent_runtime.db"
CLUSTER_DB="$STORAGE_BASE/databases/cluster/node_registry.db"
SHARED_MEMORY_DB="$STORAGE_BASE/databases/cluster/shared_memories.db"
HIVE_STATE="$STORAGE_BASE/.hive-mind/current-session.json"
VOICE_STATE="/tmp/voice-mode-state.json"
CONSOLIDATION_STATE="$STORAGE_BASE/databases/consolidation_state.json"
IMPROVEMENT_QUEUE="$STORAGE_BASE/intelligent-agents/improvement_queue.json"

# Cache directory for performance
CACHE_DIR="/tmp/agentic-statusline-cache"
CACHE_TTL=5  # seconds
mkdir -p "$CACHE_DIR" 2>/dev/null

# Helper: Check if cache is valid
cache_valid() {
    local cache_file="$1"
    if [ -f "$cache_file" ]; then
        local age=$(($(date +%s) - $(stat -c %Y "$cache_file" 2>/dev/null || echo 0)))
        [ "$age" -lt "$CACHE_TTL" ] && return 0
    fi
    return 1
}

# 1. Action Success Rate (📈) - Learning pulse
get_action_success_rate() {
    local cache_file="$CACHE_DIR/action_rate"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    if [ -f "$MEMORY_DB" ]; then
        local result=$(sqlite3 "$MEMORY_DB" "
            SELECT
                COALESCE(ROUND(AVG(success_score) * 100), 0) as rate,
                COUNT(*) as total,
                COALESCE(ROUND(AVG(CASE WHEN created_at > datetime('now', '-1 hour') THEN success_score END) * 100), 0) as recent_rate
            FROM action_outcomes
            WHERE created_at > datetime('now', '-24 hours')
        " 2>/dev/null | head -1)

        if [ -n "$result" ]; then
            local rate=$(echo "$result" | cut -d'|' -f1)
            local total=$(echo "$result" | cut -d'|' -f2)
            local recent=$(echo "$result" | cut -d'|' -f3)

            # Only show if we have data
            if [ "${total:-0}" -gt 0 ]; then
                # Determine trend
                local trend="→"
                if [ -n "$recent" ] && [ -n "$rate" ] && [ "$total" -gt 5 ]; then
                    if [ "$recent" -gt "$((rate + 5))" ]; then
                        trend="↑"
                    elif [ "$recent" -lt "$((rate - 5))" ]; then
                        trend="↓"
                    fi
                fi

                # Color based on rate (convert to integer for comparison)
                local rate_int=${rate%.*}  # Strip decimal
                local color="\033[32m"  # Green
                [ "${rate_int:-0}" -lt 80 ] && color="\033[33m"  # Yellow
                [ "${rate_int:-0}" -lt 60 ] && color="\033[31m"  # Red

                local output="${color}📈${rate_int:-0}%${trend}\033[0m"
                echo "$output" > "$cache_file"
                echo "$output"
                return
            fi
        fi
    fi
    echo ""
}

# 2. Cluster Nodes Online (🌐) - Distributed health
get_cluster_status() {
    local cache_file="$CACHE_DIR/cluster_status"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local online=0
    local total=4  # mac-studio, macbook-air, macbook-pro, macpro51

    # Check node registry
    if [ -f "$CLUSTER_DB" ]; then
        online=$(sqlite3 "$CLUSTER_DB" "
            SELECT COUNT(*) FROM nodes
            WHERE last_heartbeat > datetime('now', '-5 minutes')
            AND status = 'online'
        " 2>/dev/null || echo 0)
    fi

    # Fallback: check for active connections
    if [ "$online" -eq 0 ]; then
        # At minimum, we're online
        online=1
        # Check SMB connections to other nodes
        if mount | grep -q "agentic-system" 2>/dev/null; then
            online=$((online + 1))
        fi
        # Check if other nodes are pingable (quick timeout)
        for host in mac-studio.local macbook-air.local macbook-pro.local; do
            ping -c 1 -W 1 "$host" >/dev/null 2>&1 && online=$((online + 1))
        done
        # Cap at total
        [ "$online" -gt "$total" ] && online=$total
    fi

    # Color: green if all, yellow if some, red if isolated
    local color="\033[32m"
    [ "$online" -lt "$total" ] && color="\033[33m"
    [ "$online" -lt 2 ] && color="\033[31m"

    local output="${color}🌐${online}/${total}\033[0m"
    echo "$output" > "$cache_file"
    echo "$output"
}

# 3. Goal/Task Queue (🎯) - Work visibility
get_goal_task_status() {
    local cache_file="$CACHE_DIR/goal_task"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local goals=0
    local tasks=0
    local blocked=0

    if [ -f "$AGENT_RUNTIME_DB" ]; then
        # Count active goals
        goals=$(sqlite3 "$AGENT_RUNTIME_DB" "
            SELECT COUNT(*) FROM goals WHERE status = 'active'
        " 2>/dev/null || echo 0)

        # Count pending/in_progress tasks
        tasks=$(sqlite3 "$AGENT_RUNTIME_DB" "
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('pending', 'in_progress')
        " 2>/dev/null || echo 0)

        # Count blocked tasks (have unmet dependencies)
        blocked=$(sqlite3 "$AGENT_RUNTIME_DB" "
            SELECT COUNT(*) FROM tasks t
            WHERE status = 'pending'
            AND EXISTS (
                SELECT 1 FROM task_dependencies td
                JOIN tasks dep ON td.dependency_id = dep.id
                WHERE td.task_id = t.id AND dep.status != 'completed'
            )
        " 2>/dev/null || echo 0)
    fi

    # Only show if there's work to track
    local total=$((goals + tasks))
    if [ "$total" -gt 0 ]; then
        local output="\033[36m🎯${goals}g·${tasks}t"
        [ "$blocked" -gt 0 ] && output="${output}·\033[31m${blocked}⏸\033[36m"
        output="${output}\033[0m"
        echo "$output" > "$cache_file"
        echo "$output"
    else
        echo "" > "$cache_file"
        echo ""
    fi
}

# 4. Voice Listening State (🎤/🔇) - Interaction mode
get_voice_status() {
    local cache_file="$CACHE_DIR/voice_status"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local listening=false
    local output=""

    # Check voice mode state file
    if [ -f "$VOICE_STATE" ]; then
        listening=$(jq -r '.stt_enabled // false' "$VOICE_STATE" 2>/dev/null)
    fi

    # Alternative: check if voice process is running
    if [ "$listening" != "true" ]; then
        pgrep -f "voice.*listen\|whisper" > /dev/null 2>&1 && listening=true
    fi

    if [ "$listening" = "true" ]; then
        output="\033[32m🎤\033[0m"
    else
        output="\033[90m🔇\033[0m"
    fi

    echo "$output" > "$cache_file"
    echo "$output"
}

# 5. Knowledge Gaps (🕳️) - Learning needs
get_knowledge_gaps() {
    local cache_file="$CACHE_DIR/knowledge_gaps"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local gaps=0
    local critical=0

    if [ -f "$MEMORY_DB" ]; then
        # Count open knowledge gaps
        local result=$(sqlite3 "$MEMORY_DB" "
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN severity >= 0.7 THEN 1 ELSE 0 END) as critical
            FROM knowledge_gaps
            WHERE status = 'open'
        " 2>/dev/null | head -1)

        if [ -n "$result" ]; then
            gaps=$(echo "$result" | cut -d'|' -f1)
            critical=$(echo "$result" | cut -d'|' -f2)
        fi
    fi

    local output=""
    if [ "${gaps:-0}" -gt 0 ]; then
        local color="\033[33m"  # Yellow
        [ "${critical:-0}" -gt 0 ] && color="\033[31m"  # Red if critical gaps
        output="${color}🕳️${gaps}\033[0m"
    fi

    echo "$output" > "$cache_file"
    echo "$output"
}

# 6. Consolidation Age (🌙) - Memory health
get_consolidation_status() {
    local cache_file="$CACHE_DIR/consolidation"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local age_minutes=999
    local output=""

    # Check consolidation state
    if [ -f "$CONSOLIDATION_STATE" ]; then
        local last_run=$(jq -r '.last_consolidation // empty' "$CONSOLIDATION_STATE" 2>/dev/null)
        if [ -n "$last_run" ]; then
            local last_ts=$(date -d "$last_run" +%s 2>/dev/null || echo 0)
            local now=$(date +%s)
            age_minutes=$(( (now - last_ts) / 60 ))
        fi
    fi

    # Alternative: check memory database for last consolidation job
    if [ "$age_minutes" -eq 999 ] && [ -f "$MEMORY_DB" ]; then
        local last_job=$(sqlite3 "$MEMORY_DB" "
            SELECT MAX(completed_at) FROM consolidation_jobs
            WHERE status = 'completed'
        " 2>/dev/null)
        if [ -n "$last_job" ] && [ "$last_job" != "" ]; then
            local last_ts=$(date -d "$last_job" +%s 2>/dev/null || echo 0)
            local now=$(date +%s)
            age_minutes=$(( (now - last_ts) / 60 ))
        fi
    fi

    # Format time and color
    local time_str=""
    local color="\033[32m"  # Green

    if [ "$age_minutes" -lt 60 ]; then
        time_str="${age_minutes}m"
    elif [ "$age_minutes" -lt 1440 ]; then
        time_str="$((age_minutes / 60))h"
        [ "$age_minutes" -gt 360 ] && color="\033[33m"  # Yellow after 6h
    else
        time_str="$((age_minutes / 1440))d"
        color="\033[31m"  # Red after 24h
    fi

    if [ "$age_minutes" -lt 999 ]; then
        output="${color}🌙${time_str}\033[0m"
    fi

    echo "$output" > "$cache_file"
    echo "$output"
}

# 7. Improvement Queue (🔄) - Self-improvement pipeline
get_improvement_status() {
    local cache_file="$CACHE_DIR/improvement"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local queued=0
    local in_progress=0
    local output=""

    # Check improvement queue
    if [ -f "$IMPROVEMENT_QUEUE" ]; then
        queued=$(jq -r '.queued | length // 0' "$IMPROVEMENT_QUEUE" 2>/dev/null)
        in_progress=$(jq -r '.in_progress | length // 0' "$IMPROVEMENT_QUEUE" 2>/dev/null)
    fi

    # Alternative: check memory for improvement cycles
    if [ "$queued" -eq 0 ] && [ -f "$MEMORY_DB" ]; then
        queued=$(sqlite3 "$MEMORY_DB" "
            SELECT COUNT(*) FROM improvement_cycles
            WHERE status IN ('pending', 'baseline_assessed')
        " 2>/dev/null || echo 0)

        in_progress=$(sqlite3 "$MEMORY_DB" "
            SELECT COUNT(*) FROM improvement_cycles
            WHERE status = 'strategies_applied'
        " 2>/dev/null || echo 0)
    fi

    local total=$((queued + in_progress))
    if [ "$total" -gt 0 ]; then
        local color="\033[35m"  # Magenta for active improvement
        [ "$in_progress" -gt 0 ] && color="\033[32m"  # Green if actively improving
        output="${color}🔄${total}\033[0m"
    fi

    echo "$output" > "$cache_file"
    echo "$output"
}

# 8. Hive Mind Active (🐝) - Swarm awareness
get_hive_status() {
    local cache_file="$CACHE_DIR/hive_status"
    if cache_valid "$cache_file"; then
        cat "$cache_file"
        return
    fi

    local active=false
    local agent_count=0
    local output=""

    # Check hive mind session state
    if [ -f "$HIVE_STATE" ]; then
        active=$(jq -r '.active // false' "$HIVE_STATE" 2>/dev/null)
        agent_count=$(jq -r '.agents | length // 0' "$HIVE_STATE" 2>/dev/null)
    fi

    # Alternative: check .claude-flow for swarm state
    local flow_state="$STORAGE_BASE/.claude-flow/swarm-state.json"
    if [ "$active" != "true" ] && [ -f "$flow_state" ]; then
        active=$(jq -r '.active // false' "$flow_state" 2>/dev/null)
        agent_count=$(jq -r '.agents | length // 0' "$flow_state" 2>/dev/null)
    fi

    if [ "$active" = "true" ] && [ "$agent_count" -gt 0 ]; then
        output="\033[33m🐝${agent_count}\033[0m"
    fi

    echo "$output" > "$cache_file"
    echo "$output"
}

# Main statusline assembly
main() {
    local parts=()

    # Collect all indicators (run in parallel for speed)
    local action_rate=$(get_action_success_rate)
    local cluster=$(get_cluster_status)
    local goals=$(get_goal_task_status)
    local voice=$(get_voice_status)
    local gaps=$(get_knowledge_gaps)
    local consolidation=$(get_consolidation_status)
    local improvement=$(get_improvement_status)
    local hive=$(get_hive_status)

    # Build statusline with non-empty parts
    [ -n "$action_rate" ] && parts+=("$action_rate")
    [ -n "$cluster" ] && parts+=("$cluster")
    [ -n "$goals" ] && parts+=("$goals")
    [ -n "$voice" ] && parts+=("$voice")
    [ -n "$gaps" ] && parts+=("$gaps")
    [ -n "$consolidation" ] && parts+=("$consolidation")
    [ -n "$improvement" ] && parts+=("$improvement")
    [ -n "$hive" ] && parts+=("$hive")

    # Output joined with separators
    local IFS=' | '
    echo -e "${parts[*]}"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
