#!/bin/bash
# Check status of all agentic system services
# Provides comprehensive overview of system health

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        Agentic System - Service Status Report             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    if systemctl --user is-active --quiet "$service"; then
        echo -e "  ${GREEN}●${NC} $service - ${GREEN}running${NC}"
        return 0
    elif systemctl --user is-enabled --quiet "$service" 2>/dev/null; then
        echo -e "  ${YELLOW}○${NC} $service - ${YELLOW}enabled but not running${NC}"
        return 1
    else
        echo -e "  ${RED}○${NC} $service - ${RED}disabled/not found${NC}"
        return 2
    fi
}

# Core infrastructure
echo "🐳 Core Infrastructure Containers"
check_service redis.service
check_service qdrant.service
check_service n8n.service
echo ""

# Monitoring stack
echo "📊 Monitoring Stack"
check_service prometheus.service
check_service loki.service
check_service grafana.service
echo ""

# MCP servers
echo "🔌 MCP Servers"
check_service mcp-enhanced-memory.service
check_service mcp-agent-runtime.service
check_service mcp-ember.service
check_service mcp-safla.service
check_service mcp-cluster-execution.service
check_service mcp-video-transcript.service
check_service mcp-research-paper.service
check_service mcp-agi.service
echo ""

# Builder services
echo "🔨 Builder Node Services"
check_service builder-api.service
check_service builder-heartbeat.service
check_service builder-task-queue.service
echo ""

# Cluster services
echo "🌐 Cluster Services"
check_service cluster-heartbeat.service
echo ""

# Maintenance
echo "🧹 Maintenance Services"
check_service artifact-cleanup.service
echo ""

# Docker containers
echo "🐋 Docker Containers"
if command -v docker &> /dev/null; then
    docker ps --format "  {{.Names}}: {{.Status}}" | grep -E "redis|qdrant|n8n|prometheus|loki|grafana" || echo "  No agentic containers running"
else
    echo "  Docker not available"
fi
echo ""

# User lingering status
echo "👤 User Lingering (for service persistence)"
if loginctl show-user $USER | grep -q "Linger=yes"; then
    echo -e "  ${GREEN}●${NC} Lingering enabled - services will persist after logout"
else
    echo -e "  ${YELLOW}○${NC} Lingering disabled - services may stop on logout"
    echo "  Run: sudo loginctl enable-linger $USER"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
total_services=$(systemctl --user list-unit-files --type=service | grep -E "agentic|builder|mcp|redis|qdrant|n8n" | wc -l)
enabled_services=$(systemctl --user list-unit-files --state=enabled | grep -E "agentic|builder|mcp|redis|qdrant|n8n" | wc -l)
running_services=$(systemctl --user list-units --type=service --state=running | grep -E "agentic|builder|mcp|redis|qdrant|n8n" | wc -l)

echo "📋 Summary:"
echo "  Total services configured: $total_services"
echo "  Enabled for auto-start: $enabled_services"
echo "  Currently running: $running_services"
echo ""

if [ $enabled_services -lt $total_services ]; then
    echo "⚠️  Some services are not enabled for auto-start"
    echo "   Run: /mnt/agentic-system/scripts/enable-all-services.sh"
    echo ""
fi

if [ $running_services -lt $enabled_services ]; then
    echo "⚠️  Some enabled services are not running"
    echo "   Run: /mnt/agentic-system/scripts/enable-all-services.sh --start"
    echo ""
fi

if [ $running_services -eq $enabled_services ] && [ $enabled_services -gt 0 ]; then
    echo -e "${GREEN}✅ All enabled services are running!${NC}"
    echo ""
fi
