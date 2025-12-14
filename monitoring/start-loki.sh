#!/bin/bash
# Start Loki for Agentic System Log Aggregation


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

LOKI_CONFIG="$STORAGE_BASE/monitoring/loki/config/loki.yml"
LOKI_DATA="$STORAGE_BASE/monitoring/loki/data"
LOG_FILE="$STORAGE_BASE/monitoring/loki/loki.log"

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
