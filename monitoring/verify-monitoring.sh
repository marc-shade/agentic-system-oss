#!/bin/bash
# Verify Monitoring Infrastructure
# Checks all monitoring components and their connectivity

set -euo pipefail

echo "=== Monitoring Infrastructure Verification ==="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    local url=$2
    local description=$3

    echo -n "Checking $description... "
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

check_container() {
    local container=$1
    local description=$2

    echo -n "Checking $description container... "
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Container status
echo "--- Container Status ---"
check_container "prometheus" "Prometheus"
check_container "loki" "Loki"
check_container "grafana" "Grafana"
check_container "node-exporter" "Node Exporter"
check_container "promtail" "Promtail"
check_container "alertmanager" "Alertmanager"
echo ""

# Service endpoints
echo "--- Service Endpoints ---"
check_service "Prometheus" "http://localhost:9700/-/healthy" "Prometheus health"
check_service "Loki" "http://localhost:9900/ready" "Loki readiness"
check_service "Grafana" "http://localhost:9500/api/health" "Grafana health"
check_service "Node Exporter" "http://localhost:9100/metrics" "Node Exporter metrics"
check_service "Promtail" "http://localhost:9080/ready" "Promtail readiness"
check_service "Alertmanager" "http://localhost:9093/-/healthy" "Alertmanager health"
echo ""

# Prometheus targets
echo "--- Prometheus Targets ---"
TARGETS=$(curl -s http://localhost:9700/api/v1/targets | jq -r '.data.activeTargets[] | "\(.labels.job): \(.health)"' 2>/dev/null || echo "Failed to fetch")
if [ "$TARGETS" != "Failed to fetch" ]; then
    echo "$TARGETS" | while IFS=: read -r job health; do
        echo -n "  $job: "
        if [ "$health" = " up" ]; then
            echo -e "${GREEN}up${NC}"
        else
            echo -e "${RED}down${NC}"
        fi
    done
else
    echo -e "  ${RED}Failed to fetch targets${NC}"
fi
echo ""

# Docker metrics
echo "--- Docker Metrics ---"
echo -n "Docker daemon metrics endpoint... "
if curl -s http://localhost:9323/metrics | head -1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    echo "  Sample metrics:"
    curl -s http://localhost:9323/metrics | grep -E "^engine_daemon_" | head -3 | sed 's/^/    /'
else
    echo -e "${YELLOW}✗ (not enabled yet - run ./enable-docker-metrics.sh)${NC}"
fi
echo ""

# Qdrant metrics
echo "--- Qdrant Metrics ---"
echo -n "Qdrant metrics endpoint... "
if curl -s http://localhost:6333/metrics | head -1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    echo "  Sample metrics:"
    curl -s http://localhost:6333/metrics | grep -E "^app_|^collections_" | head -3 | sed 's/^/    /'
else
    echo -e "${RED}✗${NC}"
fi
echo ""

# Promtail log shipping
echo "--- Promtail Log Shipping ---"
echo -n "Checking Promtail streams in Loki... "
STREAMS=$(curl -s 'http://localhost:9900/loki/api/v1/label/job/values' | jq -r '.data[]' 2>/dev/null | wc -l || echo "0")
if [ "$STREAMS" -gt 0 ]; then
    echo -e "${GREEN}✓ ($STREAMS jobs found)${NC}"
    curl -s 'http://localhost:9900/loki/api/v1/label/job/values' | jq -r '.data[]' | sed 's/^/    /'
else
    echo -e "${YELLOW}⚠ (no streams yet - may need time to collect)${NC}"
fi
echo ""

# Alertmanager status
echo "--- Alertmanager Status ---"
echo -n "Alertmanager API... "
if curl -s http://localhost:9093/api/v2/status | jq -r '.cluster.status' > /dev/null 2>&1; then
    STATUS=$(curl -s http://localhost:9093/api/v2/status | jq -r '.cluster.status')
    echo -e "${GREEN}✓ (status: $STATUS)${NC}"
else
    echo -e "${RED}✗${NC}"
fi
echo ""

# Storage usage
echo "--- Storage Usage ---"
du -sh /home/marc/agentic-system/monitoring/prometheus/data 2>/dev/null | sed 's/^/  Prometheus: /' || echo "  Prometheus: (no data yet)"
du -sh /home/marc/agentic-system/monitoring/loki/data 2>/dev/null | sed 's/^/  Loki: /' || echo "  Loki: (no data yet)"
du -sh /home/marc/agentic-system/monitoring/grafana/data 2>/dev/null | sed 's/^/  Grafana: /' || echo "  Grafana: (no data yet)"
du -sh /home/marc/agentic-system/monitoring/alertmanager/data 2>/dev/null | sed 's/^/  Alertmanager: /' || echo "  Alertmanager: (no data yet)"
echo ""

# Summary
echo "--- Summary ---"
echo "Access URLs:"
echo "  Prometheus:   http://macpro51.local:9700"
echo "  Grafana:      http://macpro51.local:9500 (admin/admin)"
echo "  Alertmanager: http://macpro51.local:9093"
echo "  Promtail:     http://macpro51.local:9080"
echo ""
echo "Next steps:"
echo "  1. Enable Docker metrics: ./enable-docker-metrics.sh"
echo "  2. Configure Grafana dashboards"
echo "  3. Create alert rules in prometheus/config/rules/"
echo "  4. Test alert routing"
