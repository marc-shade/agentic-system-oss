#!/bin/bash
# Start Prometheus for Claude Code monitoring (Native - No Docker)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMETHEUS_CONFIG="$SCRIPT_DIR/prometheus/prometheus.yml"
PROMETHEUS_DATA="$SCRIPT_DIR/prometheus-data"
LOG_DIR="/Volumes/SSDRAID0/agentic-system/logs"
PORT=9700

# Create directories
mkdir -p "$PROMETHEUS_DATA"
mkdir -p "$LOG_DIR"

# Check if already running via launchd
if launchctl list | grep -q "com.agentic.prometheus"; then
    echo "Prometheus is managed by launchd"
    if curl -s "http://localhost:$PORT/-/healthy" >/dev/null 2>&1; then
        echo "✓ Prometheus healthy on http://localhost:$PORT"
        exit 0
    else
        echo "Restarting via launchctl..."
        launchctl stop com.agentic.prometheus
        sleep 2
        launchctl start com.agentic.prometheus
        sleep 3
    fi
else
    # Manual start (fallback)
    echo "Starting Prometheus manually..."
    pkill -f "prometheus.*config" 2>/dev/null
    sleep 1

    nohup /opt/homebrew/bin/prometheus \
        --config.file="$PROMETHEUS_CONFIG" \
        --storage.tsdb.path="$PROMETHEUS_DATA" \
        --web.listen-address=":$PORT" \
        --storage.tsdb.retention.time=30d \
        > "$LOG_DIR/prometheus.log" 2>&1 &

    sleep 3
fi

# Verify
if curl -s "http://localhost:$PORT/-/healthy" >/dev/null 2>&1; then
    echo "✓ Prometheus running on http://localhost:$PORT"
    echo "  Metrics: http://localhost:$PORT/metrics"
    echo "  Targets: http://localhost:$PORT/targets"
else
    echo "✗ Prometheus failed to start"
    tail -10 "$LOG_DIR/prometheus.log" 2>/dev/null
    exit 1
fi
