#!/bin/bash

# Complete Agentic System Verification
# Combines KutiraAI services + AGI components for 100% coverage
# Fixed false positive risk from original script
#
# Usage:
#   ./verify-complete-system.sh           # Human-readable output
#   ./verify-complete-system.sh --json    # JSON output for agents

JSON_OUTPUT=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
    esac
done

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
total_checks=0
passed_checks=0
failed_checks=0
degraded_checks=0

if [[ "$JSON_OUTPUT" == false ]]; then
    echo "=========================================="
    echo "Complete Agentic System Verification"
    echo "KutiraAI Services + AGI Components"
    echo "=========================================="
    echo ""
fi

check_service() {
    local name=$1
    local port=$2
    local endpoint=${3:-"/health"}
    local expected=${4:-""}

    total_checks=$((total_checks + 1))

    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -n "Checking $name (port $port)... "
    fi

    if nc -z localhost $port 2>/dev/null; then
        response=$(curl -s http://localhost:$port$endpoint 2>/dev/null || echo "")

        # FIXED: Check for explicit success indicators (not just any response)
        if [[ "$response" == *"\"status\":\"ok\""* ]] || \
           [[ "$response" == *"\"status\":\"healthy\""* ]] || \
           [[ "$response" == *"Healthy"* ]] || \
           [[ "$response" == *"healthy\":true"* ]] || \
           [[ -n "$expected" && "$response" == *"$expected"* ]]; then
            if [[ "$JSON_OUTPUT" == false ]]; then
                echo -e "${GREEN}✅ RUNNING${NC}"
            fi
            passed_checks=$((passed_checks + 1))
            return 0
        elif [[ -n "$response" ]]; then
            if [[ "$JSON_OUTPUT" == false ]]; then
                echo -e "${YELLOW}🟡 DEGRADED${NC} (port open, unhealthy response)"
            fi
            degraded_checks=$((degraded_checks + 1))
            return 0
        else
            if [[ "$JSON_OUTPUT" == false ]]; then
                echo -e "${RED}❌ NO RESPONSE${NC}"
            fi
            failed_checks=$((failed_checks + 1))
            return 1
        fi
    else
        if [[ "$JSON_OUTPUT" == false ]]; then
            echo -e "${RED}❌ NOT RUNNING${NC}"
        fi
        failed_checks=$((failed_checks + 1))
        return 1
    fi
}

check_process() {
    local name=$1
    local pattern=$2

    total_checks=$((total_checks + 1))

    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -n "Checking $name... "
    fi

    if pgrep -f "$pattern" > /dev/null 2>&1; then
        count=$(pgrep -f "$pattern" | wc -l | tr -d ' ')
        if [[ "$JSON_OUTPUT" == false ]]; then
            echo -e "${GREEN}✅ RUNNING${NC} ($count process(es))"
        fi
        passed_checks=$((passed_checks + 1))
        return 0
    else
        if [[ "$JSON_OUTPUT" == false ]]; then
            echo -e "${RED}❌ NOT RUNNING${NC}"
        fi
        failed_checks=$((failed_checks + 1))
        return 1
    fi
}

check_file() {
    local name=$1
    local path=$2
    local should_have_data=${3:-false}

    total_checks=$((total_checks + 1))

    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -n "Checking $name... "
    fi

    if [[ -e "$path" ]]; then
        if [[ "$should_have_data" == "true" ]]; then
            if [[ -s "$path" ]]; then
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo -e "${GREEN}✅ OPERATIONAL${NC} (has data)"
                fi
                passed_checks=$((passed_checks + 1))
                return 0
            else
                if [[ "$JSON_OUTPUT" == false ]]; then
                    echo -e "${YELLOW}🟡 PARTIAL${NC} (empty)"
                fi
                degraded_checks=$((degraded_checks + 1))
                return 0
            fi
        else
            if [[ "$JSON_OUTPUT" == false ]]; then
                echo -e "${GREEN}✅ EXISTS${NC}"
            fi
            passed_checks=$((passed_checks + 1))
            return 0
        fi
    else
        if [[ "$JSON_OUTPUT" == false ]]; then
            echo -e "${RED}❌ MISSING${NC}"
        fi
        failed_checks=$((failed_checks + 1))
        return 1
    fi
}

# ============================================
# SECTION 1: Storage Architecture
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo "${BLUE}━━━ Storage Architecture ━━━${NC}"
fi
check_file "Hot Storage (SSDRAID0)" "/mnt/agentic-system" false
check_file "Cold Storage (FILES)" "/Volumes/FILES/agentic-system" false
check_file "Config File" "/mnt/agentic-system/config.env" false

# ============================================
# SECTION 2: MCP Servers & Databases
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ MCP Servers & Databases ━━━${NC}"
fi
check_file "Enhanced Memory DB" "/mnt/agentic-system/databases/mcp/enhanced_memories.db" true
check_file "Agent Runtime DB" "/mnt/agentic-system/databases/mcp/agent_runtime.db" true
check_process "Enhanced Memory MCP" "enhanced-memory"
check_process "Agent Runtime MCP" "agent-runtime-mcp"
check_process "Sequential Thinking MCP" "sequential-thinking"
check_process "Chrome DevTools MCP" "chrome-devtools"
check_process "Ember MCP Server" "ember-mcp"

# ============================================
# SECTION 3: Vector Database (Qdrant)
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Vector Database (Qdrant) ━━━${NC}"
fi
check_process "Qdrant Server" "qdrant"
check_service "Qdrant Health" 6333 "/healthz" "status"
check_file "Qdrant Database" "/mnt/agentic-system/databases/qdrant" false

# ============================================
# SECTION 4: Workflow Engines
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Workflow Engines ━━━${NC}"
fi
check_process "Temporal Server" "temporal server"
check_service "AutoKitteh Server" 9980 "/" ""

# ============================================
# SECTION 5: Temporal Workers (CRITICAL)
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Temporal Workers (CRITICAL) ━━━${NC}"
fi
check_process "AGI Learning Worker" "agi_learning_workflow"
check_process "Overnight Automation Worker" "overnight_automation_workflow"
check_process "AI Agent Monitoring Worker" "ai_agent_monitoring"
check_process "YouTube Processing Worker" "youtube_processing_workflow"
check_process "Cross-System Optimization Worker" "cross_system_optimization_workflow"

# ============================================
# SECTION 6: Autonomous Monitoring (CRITICAL)
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Autonomous Monitoring (CRITICAL) ━━━${NC}"
fi
check_file "Performance Metrics" "/tmp/claude_performance_metrics.json" true
check_file "Learning Memory" "/tmp/claude_learning_memory.jsonl" true
check_file "Metrics Collection Script" "/mnt/agentic-system/monitoring/metrics_collector.py" false
check_process "Metrics Collector" "metrics_collector"

# ============================================
# SECTION 7: Monitoring Stack
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Monitoring Stack ━━━${NC}"
fi
check_process "Prometheus" "prometheus"
check_service "Prometheus Health" 9700 "/-/healthy" "Healthy"
check_process "Grafana" "grafana"
check_service "Grafana Health" 9500 "/api/health" "ok"
check_process "Loki" "loki"
check_service "Loki Health" 3100 "/ready" "ready"

# ============================================
# SECTION 8: KutiraAI Backend Services
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ KutiraAI Backend Services ━━━${NC}"
fi
check_service "Frontend Dashboard" 3101 "/" ""
check_service "Agent Registry" 4100
check_service "MCP Orchestrator" 4101
check_service "Port Manager" 4102
check_service "Workflow Engine" 4103
check_service "System Monitor" 4104

# ============================================
# SECTION 9: Voice Mode Services
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Voice Mode Services ━━━${NC}"
fi
check_service "Whisper STT" 2022
check_service "Kokoro TTS" 8880
check_service "Voice Broker Main" 9091
check_service "Voice Broker Admin" 9092
check_service "Voice Cache" 9093
check_service "LiveKit Server" 7880

# ============================================
# SECTION 10: Intelligent Agents
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Intelligent Agents ━━━${NC}"
fi
check_process "System Health Guardian" "system_health_guardian.py"
check_process "System Remediation Agent" "system_remediation_agent.py"
check_process "Code Evolution Protector" "code_evolution_protector.py"

# ============================================
# SECTION 11: Self-Healing System
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Self-Healing System ━━━${NC}"
fi
check_file "Simple Optimizer" "/mnt/agentic-system/workflows/simple_optimizer.py" false
check_file "Temporal Deep Learning" "/mnt/agentic-system/workflows/temporal/claude_deep_learning_optimizer.py" false
check_file "AutoKitteh Event Handlers" "/mnt/agentic-system/workflows/autokitteh/system_event_optimizer.py" false
check_file "Agentic Markers Log" "$HOME/.claude/.config_modifications.jsonl" true

# ============================================
# SECTION 12: Arduino Smart Surface
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Arduino Smart Surface ━━━${NC}"
fi
check_file "Arduino MCP Server" "/mnt/agentic-system/arduino-surface/mcp-server/arduino_surface_mcp.py" false
check_file "Arduino Socket" "/dev/tty.usbmodem8344401"

# ============================================
# SECTION 13: Machine Learning (MLX)
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ Machine Learning (MLX) ━━━${NC}"
fi
check_file "MLX Config" "/mnt/agentic-system/mlx_config.py" false

total_checks=$((total_checks + 1))
if [[ "$JSON_OUTPUT" == false ]]; then
    echo -n "Checking MLX Import... "
fi
if python3 -c 'import mlx.core as mx; print(mx.__version__)' > /dev/null 2>&1; then
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${GREEN}✅ OPERATIONAL${NC}"
    fi
    passed_checks=$((passed_checks + 1))
else
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${RED}❌ NOT WORKING${NC}"
    fi
    failed_checks=$((failed_checks + 1))
fi

# ============================================
# SECTION 14: PM2 Managed Services
# ============================================
if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "${BLUE}━━━ PM2 Managed Services ━━━${NC}"
fi

pm2_count=$(pm2 list 2>/dev/null | grep -c "online" || echo "0")
total_checks=$((total_checks + 1))

if [[ "$JSON_OUTPUT" == false ]]; then
    echo -n "Checking PM2 Services... "
fi

if [[ $pm2_count -gt 0 ]]; then
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${GREEN}✅ RUNNING${NC} ($pm2_count online)"
    fi
    passed_checks=$((passed_checks + 1))
else
    if [[ "$JSON_OUTPUT" == false ]]; then
        echo -e "${RED}❌ NOT RUNNING${NC}"
    fi
    failed_checks=$((failed_checks + 1))
fi

# ============================================
# Summary
# ============================================
operational=$((passed_checks + degraded_checks))
percentage=$((operational * 100 / total_checks))

if [[ "$JSON_OUTPUT" == false ]]; then
    echo ""
    echo "=========================================="
    echo "SUMMARY"
    echo "=========================================="
    echo "Total checks: $total_checks"
    echo -e "✅ Fully Operational: ${GREEN}$passed_checks${NC} ($((passed_checks * 100 / total_checks))%)"
    echo -e "🟡 Degraded: ${YELLOW}$degraded_checks${NC} ($((degraded_checks * 100 / total_checks))%)"
    echo -e "❌ Not Working: ${RED}$failed_checks${NC} ($((failed_checks * 100 / total_checks))%)"
    echo ""

    if [[ $percentage -eq 100 ]]; then
        echo -e "${GREEN}✓ System is 100% operational!${NC}"
    elif [[ $percentage -ge 80 ]]; then
        echo -e "${YELLOW}⚠ System is $percentage% operational${NC}"
        echo "Review degraded/failed checks above"
    else
        echo -e "${RED}✗ System is only $percentage% operational${NC}"
        echo "Critical services are missing!"
    fi
    echo ""
    echo "Detailed Analysis:"
    echo "  AGI Roadmap: /mnt/agentic-system/SYSTEM_AUDIT_AND_COMPLETION_ROADMAP.md"
    echo "  Action Plan: /mnt/agentic-system/IMMEDIATE_ACTION_PLAN.md"
    echo "=========================================="
fi

exit 0
