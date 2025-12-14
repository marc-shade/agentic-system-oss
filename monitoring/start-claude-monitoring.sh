#!/bin/bash
# Start complete Claude Code monitoring system


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

MONITORING_DIR="$STORAGE_BASE/monitoring"
COLLECTOR_SCRIPT="$MONITORING_DIR/claude-telemetry-collector.py"
EXPORTER_SCRIPT="$MONITORING_DIR/claude-metrics-exporter.py"
COLLECTOR_LOG="$MONITORING_DIR/claude-telemetry-collector.log"
EXPORTER_LOG="$MONITORING_DIR/claude-metrics-exporter.log"

echo "🚀 Starting Claude Code monitoring system..."

# Start telemetry collector (scrapes Claude Code's Prometheus endpoint)
if pgrep -f "claude-telemetry-collector.py" > /dev/null; then
    echo "✓ Telemetry collector already running"
else
    echo "  Starting telemetry collector..."
    nohup python3 "$COLLECTOR_SCRIPT" > "$COLLECTOR_LOG" 2>&1 &
    sleep 1
    if pgrep -f "claude-telemetry-collector.py" > /dev/null; then
        echo "  ✅ Telemetry collector started (PID: $(pgrep -f claude-telemetry-collector.py))"
    else
        echo "  ❌ Telemetry collector failed to start"
    fi
fi

# Start metrics exporter (serves data to XRG)
if pgrep -f "claude-metrics-exporter.py" > /dev/null; then
    echo "✓ Metrics exporter already running"
else
    echo "  Starting metrics exporter..."
    nohup python3 "$EXPORTER_SCRIPT" > "$EXPORTER_LOG" 2>&1 &
    sleep 1
    if pgrep -f "claude-metrics-exporter.py" > /dev/null; then
        echo "  ✅ Metrics exporter started (PID: $(pgrep -f claude-metrics-exporter.py))"
    else
        echo "  ❌ Metrics exporter failed to start"
    fi
fi

echo ""
echo "📊 Monitoring endpoints:"
echo "  XRG endpoint: http://localhost:4318/v1/metrics"
echo "  Health check: http://localhost:4318/health"
echo "  Claude OTel:  http://localhost:9464/metrics (requires restart)"
echo ""
echo "📝 Log files:"
echo "  Collector: $COLLECTOR_LOG"
echo "  Exporter:  $EXPORTER_LOG"
echo ""
echo "⚠️  Note: Restart your terminal for Claude Code telemetry to be enabled"
