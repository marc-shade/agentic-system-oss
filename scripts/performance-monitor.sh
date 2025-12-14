#!/bin/bash
##############################################################################
# Performance Monitor for Agentic System
# Real-time monitoring of key performance metrics
#
# Usage: ./performance-monitor.sh [--interval SECONDS]
#
# Monitors:
# - System load and CPU usage
# - MCP process count and duplicates
# - Memory consolidation rate
# - Qdrant query performance
# - Top resource consumers
##############################################################################

INTERVAL="${2:-5}"  # Default 5 second refresh
QDRANT_URL="http://localhost:6333"
COLLECTION="enhanced_memory"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Thresholds
MCP_PROCESS_ALERT=30
LOAD_ALERT=15.0
CPU_ALERT=80
QUERY_LATENCY_ALERT=100  # ms

clear

while true; do
    # Move cursor to top
    tput cup 0 0

    echo "═══════════════════════════════════════════════════════════════════════"
    echo "  AGENTIC SYSTEM PERFORMANCE MONITOR"
    echo "  $(date '+%Y-%m-%d %H:%M:%S') | Refresh: ${INTERVAL}s"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo

    # ========================================================================
    # System Load and CPU
    # ========================================================================
    echo -e "${BLUE}[SYSTEM LOAD]${NC}"
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1, $2, $3}')
    LOAD_1MIN=$(echo $LOAD | awk '{print $1}' | tr -d ',')

    if (( $(echo "$LOAD_1MIN > $LOAD_ALERT" | bc -l) )); then
        echo -e "  ${RED}⚠ ALERT: High load${NC} - $LOAD"
    else
        echo -e "  ${GREEN}✓${NC} Load average: $LOAD"
    fi

    # CPU usage
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$CPU_USAGE > $CPU_ALERT" | bc -l) )); then
        echo -e "  ${RED}⚠ CPU: ${CPU_USAGE}%${NC}"
    else
        echo -e "  ${GREEN}✓${NC} CPU: ${CPU_USAGE}%"
    fi

    # Memory
    MEM_USED=$(free -h | grep Mem | awk '{print $3}')
    MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} Memory: ${MEM_USED} / ${MEM_TOTAL}"
    echo

    # ========================================================================
    # MCP Process Count
    # ========================================================================
    echo -e "${BLUE}[MCP PROCESSES]${NC}"
    MCP_COUNT=$(ps aux | grep -E "python.*mcp-servers|python.*server.py" | grep -v grep | wc -l)

    if [ $MCP_COUNT -gt $MCP_PROCESS_ALERT ]; then
        echo -e "  ${RED}⚠ ALERT: ${MCP_COUNT} processes${NC} (expected: ~25, threshold: ${MCP_PROCESS_ALERT})"
        echo -e "  ${YELLOW}→ Multiple Claude sessions detected${NC}"
    else
        echo -e "  ${GREEN}✓${NC} ${MCP_COUNT} MCP processes (healthy)"
    fi

    # Count duplicates per server type
    echo "  Breakdown by server type:"
    ps aux | grep -E "python.*mcp-servers" | grep -v grep | \
        awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | \
        sed 's|/mnt/agentic-system/mcp-servers/||' | \
        sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -5 | \
        while read count server; do
            if [ "$count" -gt 1 ]; then
                echo -e "    ${YELLOW}↳${NC} $server: ${YELLOW}${count}x${NC}"
            else
                echo -e "    ${GREEN}↳${NC} $server: ${count}x"
            fi
        done
    echo

    # ========================================================================
    # Top CPU Consumers
    # ========================================================================
    echo -e "${BLUE}[TOP CPU CONSUMERS]${NC}"
    ps aux --sort=-%cpu | head -6 | tail -5 | \
        awk '{printf "  %6s CPU | PID %-7s | %s\n", $3"%", $2, $11}' | \
        while read line; do
            CPU=$(echo "$line" | awk '{print $1}' | tr -d '%')
            if (( $(echo "$CPU > 80" | bc -l) )); then
                echo -e "${RED}⚠${NC} $line"
            elif (( $(echo "$CPU > 50" | bc -l) )); then
                echo -e "${YELLOW}⚠${NC} $line"
            else
                echo -e "${GREEN}✓${NC} $line"
            fi
        done
    echo

    # ========================================================================
    # Top Memory Consumers
    # ========================================================================
    echo -e "${BLUE}[TOP MEMORY CONSUMERS]${NC}"
    ps aux --sort=-%mem | head -6 | tail -5 | \
        awk '{printf "  %6s MEM | PID %-7s | %s\n", $4"%", $2, $11}' | \
        while read line; do
            echo -e "${GREEN}✓${NC} $line"
        done
    echo

    # ========================================================================
    # Qdrant Performance
    # ========================================================================
    echo -e "${BLUE}[QDRANT VECTOR SEARCH]${NC}"
    if QDRANT_INFO=$(curl -s "$QDRANT_URL/collections/$COLLECTION" 2>/dev/null); then
        POINTS=$(echo "$QDRANT_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "N/A")
        INDEXED=$(echo "$QDRANT_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['indexed_vectors_count'])" 2>/dev/null || echo "N/A")
        SEGMENTS=$(echo "$QDRANT_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['segments_count'])" 2>/dev/null || echo "N/A")

        echo -e "  ${GREEN}✓${NC} Collection: $COLLECTION"
        echo -e "    Points: $POINTS | Indexed: $INDEXED | Segments: $SEGMENTS"

        if [ "$INDEXED" = "0" ] && [ "$POINTS" != "N/A" ] && [ "$POINTS" -gt 0 ]; then
            echo -e "    ${RED}⚠ ALERT: No HNSW index${NC} - Full scan on every query (slow!)"
        elif [ "$INDEXED" != "$POINTS" ] && [ "$INDEXED" != "N/A" ] && [ "$POINTS" != "N/A" ]; then
            PERCENT=$((INDEXED * 100 / POINTS))
            echo -e "    ${YELLOW}⚠ Indexing in progress: ${PERCENT}%${NC}"
        fi
    else
        echo -e "  ${RED}✗${NC} Cannot connect to Qdrant"
    fi
    echo

    # ========================================================================
    # Memory Consolidation
    # ========================================================================
    echo -e "${BLUE}[MEMORY CONSOLIDATION]${NC}"
    if systemctl is-active --quiet memory-consolidation; then
        echo -e "  ${GREEN}✓${NC} Service: Running"

        if [ -f /mnt/agentic-system/databases/consolidation_state.json ]; then
            LAST_RUN=$(jq -r '.last_consolidation' /mnt/agentic-system/databases/consolidation_state.json 2>/dev/null | cut -d'T' -f1-2 | tr 'T' ' ')
            TOTAL_PATTERNS=$(jq -r '.total_patterns_found' /mnt/agentic-system/databases/consolidation_state.json 2>/dev/null || echo "N/A")
            TOTAL_RUNS=$(jq -r '.total_consolidations' /mnt/agentic-system/databases/consolidation_state.json 2>/dev/null || echo "N/A")

            echo "  Last run: $LAST_RUN"
            echo "  Total runs: $TOTAL_RUNS | Patterns found: $TOTAL_PATTERNS"

            if [ "$TOTAL_PATTERNS" = "0" ] || [ "$TOTAL_PATTERNS" -lt 10 ]; then
                echo -e "  ${YELLOW}⚠ Low pattern extraction${NC} - May need tuning"
            fi
        fi
    else
        echo -e "  ${RED}✗${NC} Service: Not running"
    fi
    echo

    # ========================================================================
    # Enhanced Memory Status
    # ========================================================================
    echo -e "${BLUE}[ENHANCED MEMORY]${NC}"
    if [ -f ~/.claude/enhanced_memories/memory.db ]; then
        DB_SIZE=$(du -h ~/.claude/enhanced_memories/memory.db | cut -f1)
        ENTITY_COUNT=$(sqlite3 ~/.claude/enhanced_memories/memory.db "SELECT COUNT(*) FROM entities" 2>/dev/null || echo "N/A")
        echo -e "  ${GREEN}✓${NC} Database: ${DB_SIZE} | Entities: ${ENTITY_COUNT}"

        # Check Redis connection
        if redis-cli ping &>/dev/null; then
            REDIS_MEM=$(redis-cli info memory | grep used_memory_human | cut -d':' -f2 | tr -d '\r')
            echo -e "  ${GREEN}✓${NC} Redis: Connected (${REDIS_MEM})"
        else
            echo -e "  ${YELLOW}⚠${NC} Redis: Not connected"
        fi
    else
        echo -e "  ${RED}✗${NC} Database not found"
    fi
    echo

    # ========================================================================
    # Footer
    # ========================================================================
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "Press Ctrl+C to exit | Refreshing in ${INTERVAL}s..."

    sleep $INTERVAL
done
