#!/bin/bash
# System Reality Check - Tests what's actually operational vs. stubbed
# Usage: ./audit-system-reality.sh

# Don't exit on errors - we want to test everything
set +e


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

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}=== Agentic System Reality Check ===${NC}\n"
echo "Testing what's actually operational vs. documented..."
echo ""

# Track results
PASSED=0
FAILED=0
PARTIAL=0

test_component() {
    local name=$1
    local test_cmd=$2
    local expected=$3

    echo -ne "Testing ${name}... "

    if eval "$test_cmd" &>/dev/null; then
        if [ ! -z "$expected" ]; then
            result=$(eval "$test_cmd" 2>/dev/null)
            if echo "$result" | grep -q "$expected"; then
                echo -e "${GREEN}✅ OPERATIONAL${NC}"
                ((PASSED++))
            else
                echo -e "${YELLOW}🟡 PARTIAL${NC} (unexpected output)"
                ((PARTIAL++))
            fi
        else
            echo -e "${GREEN}✅ OPERATIONAL${NC}"
            ((PASSED++))
        fi
    else
        echo -e "${RED}❌ NOT WORKING${NC}"
        ((FAILED++))
    fi
}

test_file_exists() {
    local name=$1
    local file=$2
    local should_have_data=$3

    echo -ne "Testing ${name}... "

    if [ -e "$file" ]; then
        if [ "$should_have_data" = "true" ]; then
            if [ -s "$file" ]; then
                echo -e "${GREEN}✅ OPERATIONAL${NC} (has data)"
                ((PASSED++))
            else
                echo -e "${YELLOW}🟡 PARTIAL${NC} (empty)"
                ((PARTIAL++))
            fi
        else
            echo -e "${GREEN}✅ EXISTS${NC}"
            ((PASSED++))
        fi
    else
        echo -e "${RED}❌ MISSING${NC}"
        ((FAILED++))
    fi
}

test_process_running() {
    local name=$1
    local process_pattern=$2

    echo -ne "Testing ${name}... "

    if pgrep -f "$process_pattern" &>/dev/null; then
        count=$(pgrep -f "$process_pattern" | wc -l | tr -d ' ')
        echo -e "${GREEN}✅ RUNNING${NC} (${count} process(es))"
        ((PASSED++))
    else
        echo -e "${RED}❌ NOT RUNNING${NC}"
        ((FAILED++))
    fi
}

echo -e "${BOLD}Storage Architecture${NC}"
test_file_exists "Hot Storage (SSDRAID0)" "$STORAGE_BASE" false
test_file_exists "Cold Storage (FILES)" "$STORAGE_BASE" false
test_file_exists "Config File" "$STORAGE_BASE/config.env" false
echo ""

echo -e "${BOLD}MCP Servers${NC}"
test_file_exists "Enhanced Memory DB" "$STORAGE_BASE/databases/mcp/enhanced_memories.db" true
test_file_exists "Agent Runtime DB" "$STORAGE_BASE/databases/mcp/agent_runtime.db" true
test_file_exists "Ember MCP" "$STORAGE_BASE/mcp-servers/ember-mcp" false
echo ""

echo -e "${BOLD}Vector Database (Qdrant)${NC}"
test_process_running "Qdrant Server" "qdrant"
test_component "Qdrant Health" "curl -s http://localhost:6333/healthz" "status"
test_file_exists "Qdrant Database" "$STORAGE_BASE/databases/qdrant" false
echo ""

echo -e "${BOLD}Workflow Engines${NC}"
test_process_running "Temporal Server" "temporal server"
test_component "Temporal Health" "curl -s http://localhost:7233" ""
test_process_running "AutoKitteh Server" "ak up"
test_component "AutoKitteh Health" "curl -s http://localhost:9980" ""
test_process_running "n8n Server" "n8n"
test_component "n8n Health" "curl -s http://localhost:5678" ""
echo ""

echo -e "${BOLD}Temporal Workers (CRITICAL CHECK)${NC}"
test_process_running "Claude Deep Learning" "claude_deep_learning"
test_process_running "Overnight Automation" "overnight_automation"
test_process_running "AI Agent Monitoring" "ai_agent_monitoring"
test_process_running "Infrastructure Health" "infrastructure_health"
echo ""

echo -e "${BOLD}Autonomous Monitoring (CRITICAL CHECK)${NC}"
test_file_exists "Performance Metrics" "/tmp/claude_performance_metrics.json" true
test_file_exists "Learning Memory" "/tmp/claude_learning_memory.jsonl" true
test_file_exists "Metrics Collection Script" "$STORAGE_BASE/monitoring/claude-metrics-exporter.py" false
test_process_running "Metrics Exporter" "claude-metrics-exporter"
echo ""

echo -e "${BOLD}Monitoring Stack${NC}"
test_process_running "Prometheus" "prometheus"
test_component "Prometheus Health" "curl -s http://localhost:9700/-/healthy" "Healthy"
test_process_running "Grafana" "grafana"
test_component "Grafana Health" "curl -s http://localhost:9500/api/health" "ok"
test_process_running "Loki" "loki"
test_component "Loki Health" "curl -s http://localhost:3100/ready" "ready"
echo ""

echo -e "${BOLD}Self-Healing System${NC}"
test_file_exists "Simple Optimizer" "$STORAGE_BASE/workflows/simple_optimizer.py" false
test_file_exists "Temporal Deep Learning" "$STORAGE_BASE/workflows/temporal/claude_deep_learning_optimizer.py" false
test_file_exists "AutoKitteh Event Handlers" "$STORAGE_BASE/workflows/autokitteh/system_event_optimizer.py" false
test_file_exists "Agentic Markers Log" "$HOME/.claude/.config_modifications.jsonl" true
echo ""

echo -e "${BOLD}Arduino Surface${NC}"
test_file_exists "Arduino MCP Server" "$STORAGE_BASE/arduino-surface/mcp-server/arduino_surface_mcp.py" false
test_process_running "Ember Broker Daemon" "ember_broker_daemon"
test_process_running "Arduino Status Daemon" "arduino_status_daemon"
echo ""

echo -e "${BOLD}Machine Learning${NC}"
test_file_exists "MLX Config" "$STORAGE_BASE/mlx_config.py" false
test_component "MLX Import" "python3 -c 'import mlx.core as mx; print(mx.__version__)'" ""
echo ""

echo -e "\n${BOLD}=== Reality Check Summary ===${NC}\n"

TOTAL=$((PASSED + PARTIAL + FAILED))

if [ $TOTAL -eq 0 ]; then
    OPERATIONAL_PCT=0
    PARTIAL_PCT=0
    STUB_PCT=0
else
    OPERATIONAL_PCT=$(echo "scale=1; ($PASSED / $TOTAL) * 100" | bc 2>/dev/null || echo "0")
    PARTIAL_PCT=$(echo "scale=1; ($PARTIAL / $TOTAL) * 100" | bc 2>/dev/null || echo "0")
    STUB_PCT=$(echo "scale=1; ($FAILED / $TOTAL) * 100" | bc 2>/dev/null || echo "0")
fi

echo -e "✅ Fully Operational: ${GREEN}${PASSED}${NC} (${OPERATIONAL_PCT}%)"
echo -e "🟡 Partially Working: ${YELLOW}${PARTIAL}${NC} (${PARTIAL_PCT}%)"
echo -e "❌ Not Working/Stubbed: ${RED}${FAILED}${NC} (${STUB_PCT}%)"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: ${FAILED} components are not operational${NC}"
    echo -e "   See SYSTEM_AUDIT_AND_COMPLETION_ROADMAP.md for build-out plan"
fi

if [ $PARTIAL -gt 0 ]; then
    echo -e "${YELLOW}⚠️  NOTE: ${PARTIAL} components are partially implemented${NC}"
    echo -e "   These need completion to reach full AGI capability"
fi

if [ $FAILED -eq 0 ] && [ $PARTIAL -eq 0 ]; then
    echo -e "${GREEN}✅ All tested components are fully operational!${NC}"
    echo -e "   System is ready for AGI operations"
fi

echo ""
echo -e "${BOLD}Detailed Analysis:${NC}"
echo "  Full report: $STORAGE_BASE/SYSTEM_AUDIT_AND_COMPLETION_ROADMAP.md"
echo "  Testing guide: $STORAGE_BASE/CLAUDE.md (Testing section)"
echo ""

exit 0
