#!/bin/bash
# Start Prometheus for Claude Code monitoring

PROMETHEUS_DIR="$(cd "$(dirname "$0")/prometheus" && pwd)"
PROMETHEUS_DATA="$(cd "$(dirname "$0")" && pwd)/prometheus-data"

# Create data directory
mkdir -p "$PROMETHEUS_DATA"

# Stop existing Prometheus container if running
podman stop claude-prometheus 2>/dev/null
podman rm claude-prometheus 2>/dev/null

# Start Prometheus with :z flag for SELinux
podman run -d \
  --name claude-prometheus \
  --network host \
  -v "$PROMETHEUS_DIR/prometheus.yml:/etc/prometheus/prometheus.yml:ro,z" \
  -v "$PROMETHEUS_DATA:/prometheus:z" \
  --add-host=host.containers.internal:host-gateway \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address=127.0.0.1:9090 \
  --storage.tsdb.retention.time=7d

echo "Prometheus started on http://127.0.0.1:9090"
echo "Metrics endpoint: http://127.0.0.1:9090/metrics"
echo ""
echo "To view metrics: podman logs -f claude-prometheus"
echo "To stop: podman stop claude-prometheus"
