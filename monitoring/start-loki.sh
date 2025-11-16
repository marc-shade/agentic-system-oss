#!/bin/bash
# Start Loki for Agentic System Log Aggregation

LOKI_CONFIG="/mnt/agentic-system/monitoring/loki/config/loki.yml"
LOKI_DATA="/mnt/agentic-system/monitoring/loki/data"
LOG_FILE="/mnt/agentic-system/monitoring/loki/loki.log"

# Ensure data directories exist
mkdir -p "$LOKI_DATA"/{chunks,boltdb-shipper-active,boltdb-shipper-cache,boltdb-shipper-compactor,rules}

# Check if already running
if pgrep -f "loki.*$LOKI_CONFIG" > /dev/null; then
    echo "Loki is already running"
    exit 0
fi

# Start Loki
echo "Starting Loki..."
nohup /opt/homebrew/bin/loki \
    -config.file="$LOKI_CONFIG" \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo "Loki started with PID: $PID"
echo "Log file: $LOG_FILE"
echo "Access at: http://localhost:9900"

# Wait a moment and check if it's running
sleep 2
if pgrep -f "loki.*$LOKI_CONFIG" > /dev/null; then
    echo "✅ Loki is running successfully"
else
    echo "❌ Loki failed to start. Check logs at: $LOG_FILE"
    exit 1
fi
