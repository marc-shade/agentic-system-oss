#!/bin/bash
# Install and configure monitoring stack via Podman containers
# Recommended by Codex and Gemini for 24/7 autonomous AI system
# Platform: Fedora 43 Linux

set -e  # Exit on error


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

STORAGE_BASE="$STORAGE_BASE"
MONITORING_DIR="$STORAGE_BASE/monitoring"

echo "================================================"
echo "Monitoring Stack Installation via Podman"
echo "================================================"
echo ""
echo "Recommended by: Codex + Gemini AI"
echo "Method: Podman containers with systemd"
echo "Benefits:"
echo "  - Upstream-fresh versions"
echo "  - Isolated and secure (SELinux)"
echo "  - Easy upgrades and rollbacks"
echo "  - Systemd integration for 24/7 reliability"
echo ""

# Check Podman is installed
if ! command -v podman &> /dev/null; then
    echo "❌ Podman not found. Installing..."
    sudo dnf install -y podman
fi

echo "✅ Podman version: $(podman --version)"
echo ""

# Create required directories
echo "Creating directory structure..."
mkdir -p "$MONITORING_DIR/prometheus/config"
mkdir -p "$MONITORING_DIR/prometheus/data"
mkdir -p "$MONITORING_DIR/loki/config"
mkdir -p "$MONITORING_DIR/loki/data"
mkdir -p "$MONITORING_DIR/grafana/data"
mkdir -p "$MONITORING_DIR/grafana/logs"
mkdir -p "$MONITORING_DIR/grafana/plugins"
echo "✅ Directories created"
echo ""

# 1. PROMETHEUS
echo "================================================"
echo "1. Installing Prometheus via Podman"
echo "================================================"

# Create Prometheus config if not exists
if [ ! -f "$MONITORING_DIR/prometheus/config/prometheus.yml" ]; then
    cat > "$MONITORING_DIR/prometheus/config/prometheus.yml" <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'agentic-system'
    node: 'macpro51'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9700']

  - job_name: 'temporal'
    static_configs:
      - targets: ['localhost:7233']

  - job_name: 'autokitteh'
    static_configs:
      - targets: ['localhost:9980']

  - job_name: 'qdrant'
    static_configs:
      - targets: ['localhost:6333']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF
    echo "✅ Created Prometheus config"
fi

# Pull Prometheus image
podman pull docker.io/prom/prometheus:latest
echo "✅ Prometheus image pulled"

# Create Prometheus container
podman create \
  --name prometheus \
  --network host \
  -v "$MONITORING_DIR/prometheus/config:/etc/prometheus:Z" \
  -v "$MONITORING_DIR/prometheus/data:/prometheus:Z" \
  docker.io/prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --storage.tsdb.retention.time=30d \
  --web.listen-address=:9700 \
  --web.enable-lifecycle \
  --web.enable-admin-api

echo "✅ Prometheus container created"
echo ""

# 2. LOKI
echo "================================================"
echo "2. Installing Loki via Podman"
echo "================================================"

# Create Loki config if not exists
if [ ! -f "$MONITORING_DIR/loki/config/loki-config.yml" ]; then
    cat > "$MONITORING_DIR/loki/config/loki-config.yml" <<EOF
auth_enabled: false

server:
  http_listen_port: 9900
  grpc_listen_port: 9901

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2023-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

limits_config:
  retention_period: 168h  # 7 days

chunk_store_config:
  max_look_back_period: 168h

table_manager:
  retention_deletes_enabled: true
  retention_period: 168h
EOF
    echo "✅ Created Loki config"
fi

# Pull Loki image
podman pull docker.io/grafana/loki:latest
echo "✅ Loki image pulled"

# Create Loki container
podman create \
  --name loki \
  --network host \
  -v "$MONITORING_DIR/loki/config:/etc/loki:Z" \
  -v "$MONITORING_DIR/loki/data:/loki:Z" \
  docker.io/grafana/loki:latest \
  -config.file=/etc/loki/loki-config.yml

echo "✅ Loki container created"
echo ""

# 3. GRAFANA
echo "================================================"
echo "3. Installing Grafana via Podman"
echo "================================================"

# Pull Grafana image
podman pull docker.io/grafana/grafana:latest
echo "✅ Grafana image pulled"

# Create Grafana container
podman create \
  --name grafana \
  --network host \
  -v "$MONITORING_DIR/grafana/data:/var/lib/grafana:Z" \
  -v "$MONITORING_DIR/grafana/logs:/var/log/grafana:Z" \
  -v "$MONITORING_DIR/grafana/plugins:/var/lib/grafana/plugins:Z" \
  -e "GF_SERVER_HTTP_PORT=9500" \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  -e "GF_INSTALL_PLUGINS=grafana-piechart-panel" \
  docker.io/grafana/grafana:latest

echo "✅ Grafana container created"
echo ""

# 4. CREATE SYSTEMD UNITS
echo "================================================"
echo "4. Creating systemd service units"
echo "================================================"

mkdir -p ~/.config/systemd/user

# Prometheus systemd unit
cat > ~/.config/systemd/user/prometheus.service <<EOF
[Unit]
Description=Prometheus Monitoring
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
TimeoutStartSec=0
ExecStart=/usr/bin/podman start prometheus
ExecStop=/usr/bin/podman stop -t 10 prometheus
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Loki systemd unit
cat > ~/.config/systemd/user/loki.service <<EOF
[Unit]
Description=Loki Log Aggregation
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
TimeoutStartSec=0
ExecStart=/usr/bin/podman start loki
ExecStop=/usr/bin/podman stop -t 10 loki
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Grafana systemd unit
cat > ~/.config/systemd/user/grafana.service <<EOF
[Unit]
Description=Grafana Visualization
After=network-online.target prometheus.service loki.service
Wants=network-online.target

[Service]
Type=forking
TimeoutStartSec=0
ExecStart=/usr/bin/podman start grafana
ExecStop=/usr/bin/podman stop -t 10 grafana
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

echo "✅ Systemd units created"
echo ""

# Reload systemd
systemctl --user daemon-reload
echo "✅ Systemd reloaded"
echo ""

# Enable services to start on boot
systemctl --user enable prometheus.service
systemctl --user enable loki.service
systemctl --user enable grafana.service
echo "✅ Services enabled for autostart"
echo ""

echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "To start services:"
echo "  systemctl --user start prometheus"
echo "  systemctl --user start loki"
echo "  systemctl --user start grafana"
echo ""
echo "Or start all at once:"
echo "  ./start-monitoring-stack.sh"
echo ""
echo "Access points:"
echo "  Prometheus: http://localhost:9700"
echo "  Loki:       http://localhost:9900"
echo "  Grafana:    http://localhost:9500"
echo "              (admin/admin)"
echo ""
echo "================================================"
