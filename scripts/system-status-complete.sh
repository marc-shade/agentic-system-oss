#!/bin/bash
# Complete System Status for Autonomous Agentic System
# Shows all auto-start services and their dependencies

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     AUTONOMOUS AGENTIC SYSTEM - COMPLETE STATUS                 ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Phase 1: Foundation Services
echo "📍 PHASE 1: Foundation Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Qdrant
if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    version=$(curl -s http://localhost:6333/ | jq -r '.version' 2>/dev/null || echo "unknown")
    collections=$(curl -s http://localhost:6333/collections | jq -r '.result.collections | length' 2>/dev/null || echo "0")
    pid=$(lsof -ti:6333 2>/dev/null)
    echo -e "${GREEN}✅ Qdrant Vector DB${NC}      v$version (PID: $pid)"
    echo "   Collections:            $collections"
    echo "   Dashboard:              http://localhost:6333/dashboard"
else
    echo -e "${RED}❌ Qdrant Vector DB${NC}      NOT RUNNING"
    echo "   Start: /mnt/agentic-system/scripts/qdrant-monitor.sh start"
fi
echo ""

# Phase 2: Core Infrastructure
echo "📍 PHASE 2: Core Infrastructure"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Temporal
if lsof -i:7233 > /dev/null 2>&1; then
    pid=$(lsof -ti:7233 2>/dev/null)
    echo -e "${GREEN}✅ Temporal Server${NC}        Running (PID: $pid)"
    echo "   gRPC Port:              7233"
    echo "   UI:                     http://localhost:8233"
else
    echo -e "${RED}❌ Temporal Server${NC}        NOT RUNNING"
    echo "   Start: /mnt/agentic-system/scripts/temporal-monitor.sh start"
fi
echo ""

# n8n
if curl -sf http://localhost:5678 > /dev/null 2>&1; then
    pid=$(lsof -ti:5678 2>/dev/null)
    echo -e "${GREEN}✅ n8n Workflow Engine${NC}    Running (PID: $pid)"
    echo "   Dashboard:              http://localhost:5678"
else
    echo -e "${RED}❌ n8n Workflow Engine${NC}    NOT RUNNING"
    echo "   Start: /mnt/agentic-system/scripts/n8n-monitor.sh start"
fi
echo ""

# AutoKitteh
if curl -sf http://localhost:9980/health > /dev/null 2>&1; then
    pid=$(lsof -ti:9980 2>/dev/null)
    deployment_count=$(/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/bin/ak deployment list 2>/dev/null | grep -c "DEPLOYMENT_STATE_ACTIVE" || echo "0")
    echo -e "${GREEN}✅ AutoKitteh${NC}             Running (PID: $pid)"
    echo "   Active Deployments:     $deployment_count"
    echo "   API:                    http://localhost:9980"
else
    echo -e "${RED}❌ AutoKitteh${NC}             NOT RUNNING"
    echo "   Start: /mnt/agentic-system/scripts/autokitteh-monitor.sh start"
fi
echo ""

# Phase 3: Workflow Workers
echo "📍 PHASE 3: Workflow Workers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

workers_running=0

# Count active Temporal workflow workers
WORKER_COUNT=$(ps aux | grep -E "(agi_learning|ai_agent_monitoring|youtube_processing|cross_system|overnight_automation)" | grep python | grep -v grep | wc -l | tr -d ' ')

if [ "$WORKER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Temporal Workers${NC}       $WORKER_COUNT active"

    # List individual workers
    if ps aux | grep -q "[a]gi_learning.*python"; then
        echo "   • AGI Learning          ✓"
        workers_running=$((workers_running + 1))
    fi

    if ps aux | grep -q "[a]i_agent_monitoring.*python"; then
        echo "   • AI Agent Monitoring   ✓"
        workers_running=$((workers_running + 1))
    fi

    if ps aux | grep -q "[y]outube_processing.*python"; then
        echo "   • YouTube Processing    ✓"
        workers_running=$((workers_running + 1))
    fi

    if ps aux | grep -q "[c]ross_system.*python"; then
        echo "   • Cross-System Opt      ✓"
        workers_running=$((workers_running + 1))
    fi

    if ps aux | grep -q "[o]vernight_automation.*python"; then
        echo "   • Overnight Automation  ✓"
        workers_running=$((workers_running + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Temporal Workers${NC}       None running"
    echo "   Start: /mnt/agentic-system/scripts/start-temporal-workers.sh"
fi
echo ""

# Phase 4: Physical Interface (Optional)
echo "📍 PHASE 4: Physical Interface (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Arduino Surface
if ps aux | grep -q "[a]rduino_enhanced_daemon.py"; then
    pid=$(ps aux | grep "[a]rduino_enhanced_daemon.py" | awk '{print $2}')
    echo -e "${GREEN}✅ Arduino Surface${NC}        Running (PID: $pid)"
    echo "   Port:                   /dev/tty.usbmodem8344401"
elif ps aux | grep -q "[a]rduino.*python"; then
    echo -e "${YELLOW}⚠️  Arduino Surface${NC}        Partially running"
    echo "   Some Arduino processes detected"
else
    echo -e "${YELLOW}⚠️  Arduino Surface${NC}        NOT RUNNING (Optional)"
    echo "   Start: /mnt/agentic-system/arduino-surface/scripts/start_agentic_stack.sh"
fi
echo ""

# Overall System Status
echo "═════════════════════════════════════════════════════════════════"
echo "📊 OVERALL SYSTEM STATUS"
echo "═════════════════════════════════════════════════════════════════"

services_total=4  # Qdrant, Temporal, n8n, AutoKitteh
services_running=0

curl -sf http://localhost:6333/healthz > /dev/null 2>&1 && services_running=$((services_running + 1))
lsof -i:7233 > /dev/null 2>&1 && services_running=$((services_running + 1))
curl -sf http://localhost:5678 > /dev/null 2>&1 && services_running=$((services_running + 1))
curl -sf http://localhost:9980/health > /dev/null 2>&1 && services_running=$((services_running + 1))

if [ "$services_running" -eq "$services_total" ] && [ "$workers_running" -gt 0 ]; then
    echo -e "${GREEN}STATUS: 🟢 FULLY AUTONOMOUS${NC} - All systems operational"
    echo ""
    echo "The system is:"
    echo "  • Self-monitoring (every 5 min via cron)"
    echo "  • Self-analyzing (Temporal workflows)"
    echo "  • Self-learning (AGI Learning worker)"
    echo "  • Self-optimizing (Cross-System worker)"
    echo "  • Self-healing (cron health checks)"
    echo "  • Event-driven (AutoKitteh)"
elif [ "$services_running" -ge 3 ]; then
    echo -e "${YELLOW}STATUS: 🟡 PARTIAL${NC} - Some services not running ($services_running/$services_total)"
else
    echo -e "${RED}STATUS: 🔴 OFFLINE${NC} - Critical services down ($services_running/$services_total)"
fi
echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "📋 Detailed Status:         /Volumes/FILES/agentic-system/claude-status.sh"
echo "🚀 Boot Orchestrator:       /mnt/agentic-system/scripts/boot-orchestrator.sh"
echo "📊 Log Files:               /mnt/agentic-system/logs/"
echo ""
