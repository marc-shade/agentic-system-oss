#!/bin/bash
# Stop all monitoring services for Agentic System

echo "Stopping Agentic System Monitoring Stack..."

# Stop Grafana
if pgrep -f "grafana-server" > /dev/null; then
    echo "Stopping Grafana..."
    pkill -f "grafana-server"
    echo "✅ Grafana stopped"
else
    echo "⚠️  Grafana was not running"
fi

# Stop Loki
if pgrep -f "loki.*config" > /dev/null; then
    echo "Stopping Loki..."
    pkill -f "loki.*config"
    echo "✅ Loki stopped"
else
    echo "⚠️  Loki was not running"
fi

# Stop Prometheus
if pgrep -f "prometheus.*config" > /dev/null; then
    echo "Stopping Prometheus..."
    pkill -f "prometheus.*config"
    echo "✅ Prometheus stopped"
else
    echo "⚠️  Prometheus was not running"
fi

echo ""
echo "All monitoring services stopped"
