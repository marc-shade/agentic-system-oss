#!/bin/bash
# Start Grafana for Agentic System Visualization

GRAFANA_CONFIG="/mnt/agentic-system/monitoring/grafana/config/grafana.ini"
GRAFANA_DATA="/mnt/agentic-system/monitoring/grafana/data"
LOG_FILE="/mnt/agentic-system/monitoring/grafana/logs/grafana.log"

# Ensure directories exist
mkdir -p "$GRAFANA_DATA"
mkdir -p "$(dirname "$LOG_FILE")"

# Check if already running
if pgrep -f "grafana-server.*$GRAFANA_CONFIG" > /dev/null; then
    echo "Grafana is already running"
    exit 0
fi

# Start Grafana
echo "Starting Grafana..."
nohup /opt/homebrew/bin/grafana-server \
    --config="$GRAFANA_CONFIG" \
    --homepath=/opt/homebrew/opt/grafana/share/grafana \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo "Grafana started with PID: $PID"
echo "Log file: $LOG_FILE"
echo "Access at: http://localhost:9500"
echo "Via proxy: http://localhost:3101/grafana"
echo ""
echo "Default credentials:"
echo "  Username: admin"
echo "  Password: admin"

# Wait a moment and check if it's running
sleep 3
if pgrep -f "grafana-server.*$GRAFANA_CONFIG" > /dev/null; then
    echo "✅ Grafana is running successfully"
else
    echo "❌ Grafana failed to start. Check logs at: $LOG_FILE"
    exit 1
fi
