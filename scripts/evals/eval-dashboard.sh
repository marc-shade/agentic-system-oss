#!/bin/bash
# Comprehensive Eval Dashboard for Self-Improving Agentic System
# Shows metrics across all components: actions, hooks, soundtrack, consolidation, agents

DB_PATH="$HOME/.claude/enhanced_memories/memory.db"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Time window (default: 24 hours)
HOURS="${1:-24}"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        AGENTIC SYSTEM EVAL DASHBOARD - Last ${HOURS}h                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# ACTION OUTCOMES
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ ACTION OUTCOMES ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    action_type as 'Action',
    COUNT(*) as 'Count',
    ROUND(AVG(success_score), 2) as 'Avg Score',
    ROUND(MIN(success_score), 2) as 'Min',
    ROUND(MAX(success_score), 2) as 'Max'
FROM action_outcomes
WHERE executed_at > datetime('now', '-${HOURS} hours')
GROUP BY action_type
ORDER BY COUNT(*) DESC
LIMIT 10;
" 2>/dev/null || echo "No action data"

TOTAL_ACTIONS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM action_outcomes WHERE executed_at > datetime('now', '-${HOURS} hours');" 2>/dev/null || echo "0")
AVG_SUCCESS=$(sqlite3 "$DB_PATH" "SELECT ROUND(AVG(success_score), 3) FROM action_outcomes WHERE executed_at > datetime('now', '-${HOURS} hours');" 2>/dev/null || echo "0")
echo -e "\n${GREEN}Total: ${TOTAL_ACTIONS} actions | Avg Success: ${AVG_SUCCESS}${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# HOOK PERFORMANCE
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ HOOK PERFORMANCE ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    hook_type as 'Hook',
    COUNT(*) as 'Calls',
    ROUND(AVG(execution_time_ms), 1) as 'Avg ms',
    ROUND(MAX(execution_time_ms), 1) as 'Max ms',
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as 'Success',
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as 'Failed'
FROM hook_evals
WHERE recorded_at > datetime('now', '-${HOURS} hours')
GROUP BY hook_type;
" 2>/dev/null || echo "No hook data yet"

# P50/P99 latencies
P50=$(sqlite3 "$DB_PATH" "
SELECT ROUND(execution_time_ms, 1)
FROM hook_evals
WHERE recorded_at > datetime('now', '-${HOURS} hours')
ORDER BY execution_time_ms
LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM hook_evals WHERE recorded_at > datetime('now', '-${HOURS} hours'));
" 2>/dev/null || echo "N/A")

P99=$(sqlite3 "$DB_PATH" "
SELECT ROUND(execution_time_ms, 1)
FROM hook_evals
WHERE recorded_at > datetime('now', '-${HOURS} hours')
ORDER BY execution_time_ms DESC
LIMIT 1 OFFSET (SELECT COUNT(*)/100 FROM hook_evals WHERE recorded_at > datetime('now', '-${HOURS} hours'));
" 2>/dev/null || echo "N/A")

echo -e "\n${GREEN}Latency: P50=${P50}ms | P99=${P99}ms${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# SOUNDTRACK EVALS
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ SOUNDTRACK EVALS ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    target_intensity as 'Intensity',
    COUNT(*) as 'Samples',
    ROUND(AVG(actual_intensity), 3) as 'Avg Level',
    ROUND(AVG(intensity_accuracy), 3) as 'Accuracy',
    ROUND(AVG(bpm), 0) as 'Avg BPM'
FROM soundtrack_evals
WHERE recorded_at > datetime('now', '-${HOURS} hours')
GROUP BY target_intensity
ORDER BY CASE target_intensity
    WHEN 'idle' THEN 1
    WHEN 'light' THEN 2
    WHEN 'active' THEN 3
    WHEN 'intense' THEN 4
END;
" 2>/dev/null || echo "No soundtrack data yet"

# Current state
CURRENT=$(curl -s http://127.0.0.1:8766/eval 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(f\"Level: {d['intensity']['level']} | Activity: {d['sequencer']['activity_level']:.2f} | BPM: {d['sequencer']['bpm']}\")
except: print('Soundtrack not running')
" 2>/dev/null || echo "Soundtrack not running")
echo -e "\n${GREEN}Current: ${CURRENT}${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# MEMORY CONSOLIDATION
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ MEMORY CONSOLIDATION ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    consolidation_type as 'Type',
    COUNT(*) as 'Runs',
    ROUND(AVG(patterns_found), 1) as 'Avg Patterns',
    ROUND(AVG(patterns_promoted), 1) as 'Avg Promoted',
    ROUND(AVG(quality_score), 3) as 'Avg Quality'
FROM consolidation_evals
WHERE recorded_at > datetime('now', '-168 hours')
GROUP BY consolidation_type;
" 2>/dev/null || echo "No consolidation data yet"
echo ""

# ═══════════════════════════════════════════════════════════════════
# AGENT PERFORMANCE
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ AGENT PERFORMANCE ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    agent_type as 'Agent',
    COUNT(*) as 'Tasks',
    ROUND(AVG(execution_time_ms)/1000, 1) as 'Avg sec',
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as 'Success',
    ROUND(AVG(quality_score), 2) as 'Quality'
FROM agent_evals
WHERE recorded_at > datetime('now', '-${HOURS} hours')
GROUP BY agent_type
ORDER BY COUNT(*) DESC;
" 2>/dev/null || echo "No agent data yet"
echo ""

# ═══════════════════════════════════════════════════════════════════
# SELF-IMPROVEMENT ACTIONS
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ SELF-IMPROVEMENT ACTIONS ═══${NC}"
sqlite3 -column -header "$DB_PATH" "
SELECT
    trigger_metric as 'Metric',
    ROUND(trigger_value, 3) as 'Value',
    action_type as 'Action',
    outcome as 'Outcome',
    datetime(recorded_at, 'localtime') as 'Time'
FROM improvement_actions
ORDER BY recorded_at DESC
LIMIT 5;
" 2>/dev/null || echo "No improvement actions yet"
echo ""

# ═══════════════════════════════════════════════════════════════════
# SYSTEM HEALTH
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ SYSTEM HEALTH ═══${NC}"
# Memory entities
ENTITY_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM entities;" 2>/dev/null || echo "0")
RECENT_ENTITIES=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM entities WHERE created_at > datetime('now', '-${HOURS} hours');" 2>/dev/null || echo "0")

# Errors in last hour
ERRORS_1H=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM action_outcomes WHERE success_score < 0.5 AND executed_at > datetime('now', '-1 hour');" 2>/dev/null || echo "0")

# Total DB size
DB_SIZE=$(du -h "$DB_PATH" 2>/dev/null | cut -f1 || echo "N/A")

echo -e "Memory Entities: ${GREEN}${ENTITY_COUNT}${NC} total (${RECENT_ENTITIES} new in ${HOURS}h)"
echo -e "Errors (1h): ${RED}${ERRORS_1H}${NC}"
echo -e "Database Size: ${DB_SIZE}"
echo ""

# ═══════════════════════════════════════════════════════════════════
# TRENDS (if enough data)
# ═══════════════════════════════════════════════════════════════════
echo -e "${YELLOW}═══ 24h TREND SUMMARY ═══${NC}"
sqlite3 "$DB_PATH" "
SELECT
    strftime('%H:00', executed_at) as hour,
    COUNT(*) as actions,
    ROUND(AVG(success_score), 2) as success
FROM action_outcomes
WHERE executed_at > datetime('now', '-24 hours')
GROUP BY strftime('%H', executed_at)
ORDER BY hour DESC
LIMIT 6;
" 2>/dev/null | while read line; do
    echo "  $line"
done
echo ""

echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Run: eval-dashboard.sh [hours] for different time windows${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════════════${NC}"
