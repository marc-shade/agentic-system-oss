#!/bin/bash
# Record system health snapshot for self-improvement tracking
# Run this periodically (e.g., every 5 minutes via cron or systemd timer)

DB_PATH="$HOME/.claude/enhanced_memories/memory.db"
NODE_ID="macpro51"

# Collect system metrics
CPU_PERCENT=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 2>/dev/null || echo "0")
MEM_PERCENT=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' 2>/dev/null || echo "0")
DISK_PERCENT=$(df -h /mnt/agentic-system | tail -1 | awk '{print $5}' | tr -d '%' 2>/dev/null || echo "0")

# Count active sessions (Claude processes)
ACTIVE_SESSIONS=$(pgrep -c -f "claude" 2>/dev/null || echo "0")

# Count active agents (Task subprocesses)
ACTIVE_AGENTS=$(pgrep -c -f "Task.*subagent" 2>/dev/null || echo "0")

# Get hook latencies (P50 and P99 from last hour)
HOOK_P50=$(sqlite3 "$DB_PATH" "
SELECT ROUND(execution_time_ms, 1)
FROM hook_evals
WHERE recorded_at > datetime('now', '-1 hour')
ORDER BY execution_time_ms
LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM hook_evals WHERE recorded_at > datetime('now', '-1 hour'));
" 2>/dev/null || echo "0")

HOOK_P99=$(sqlite3 "$DB_PATH" "
SELECT ROUND(execution_time_ms, 1)
FROM hook_evals
WHERE recorded_at > datetime('now', '-1 hour')
ORDER BY execution_time_ms DESC
LIMIT 1 OFFSET (SELECT COUNT(*)/100 FROM hook_evals WHERE recorded_at > datetime('now', '-1 hour'));
" 2>/dev/null || echo "0")

# Get soundtrack intensity
SOUNDTRACK_INTENSITY=$(curl -s http://127.0.0.1:8766/eval 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    print(d['intensity']['level'])
except: print('unknown')
" 2>/dev/null || echo "unknown")

# Count memory entities
ENTITY_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM entities;" 2>/dev/null || echo "0")

# Get action success rate (last hour)
SUCCESS_RATE=$(sqlite3 "$DB_PATH" "
SELECT ROUND(AVG(success_score), 3)
FROM action_outcomes
WHERE executed_at > datetime('now', '-1 hour');
" 2>/dev/null || echo "0")

# Count errors in last hour
ERRORS_1H=$(sqlite3 "$DB_PATH" "
SELECT COUNT(*)
FROM action_outcomes
WHERE success_score < 0.5 AND executed_at > datetime('now', '-1 hour');
" 2>/dev/null || echo "0")

# Handle empty values
[ -z "$HOOK_P50" ] && HOOK_P50="0"
[ -z "$HOOK_P99" ] && HOOK_P99="0"
[ -z "$SUCCESS_RATE" ] && SUCCESS_RATE="0"

# Insert into database
sqlite3 "$DB_PATH" "
INSERT INTO system_health
(cpu_percent, memory_percent, disk_percent, active_sessions, active_agents,
 hook_latency_p50_ms, hook_latency_p99_ms, soundtrack_intensity,
 memory_entities_total, action_success_rate_1h, errors_last_hour, node_id)
VALUES
($CPU_PERCENT, $MEM_PERCENT, $DISK_PERCENT, $ACTIVE_SESSIONS, $ACTIVE_AGENTS,
 $HOOK_P50, $HOOK_P99, '$SOUNDTRACK_INTENSITY',
 $ENTITY_COUNT, $SUCCESS_RATE, $ERRORS_1H, '$NODE_ID');
" 2>/dev/null

echo "$(date -Iseconds) - Health recorded: CPU=${CPU_PERCENT}% MEM=${MEM_PERCENT}% Sessions=${ACTIVE_SESSIONS} Errors=${ERRORS_1H}"
