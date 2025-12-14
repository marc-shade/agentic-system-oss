#!/bin/bash
# Start all monitoring services for Agentic System


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
