#!/bin/bash
# Start Grafana for Agentic System Visualization


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

GRAFANA_CONFIG="$STORAGE_BASE/monitoring/grafana/config/grafana.ini"
GRAFANA_DATA="$STORAGE_BASE/monitoring/grafana/data"
LOG_FILE="$STORAGE_BASE/monitoring/grafana/logs/grafana.log"

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
