#!/bin/bash
# Start all monitoring services for Agentic System

MONITORING_DIR="/home/marc/agentic-system/monitoring"

echo "================================================"
echo "Starting Agentic System Monitoring Stack"
echo "================================================"
echo ""

# Start Prometheus
echo "1. Starting Prometheus..."
bash "$MONITORING_DIR/start-prometheus.sh"
echo ""

# Start Loki
echo "2. Starting Loki..."
bash "$MONITORING_DIR/start-loki.sh"
echo ""

# Start Grafana
echo "3. Starting Grafana..."
bash "$MONITORING_DIR/start-grafana.sh"
echo ""

echo "================================================"
echo "Monitoring Stack Status"
echo "================================================"
echo ""
echo "Services:"
echo "  Prometheus: http://localhost:9700"
echo "  Loki:       http://localhost:9900"
echo "  Grafana:    http://localhost:9500"
echo "              http://localhost:3101/grafana"
echo ""
echo "Default Grafana credentials:"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "================================================"
