#!/bin/bash
# Install Cluster Health Monitoring Services
# Run as root or with sudo

set -e


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

echo "======================================"
echo " Installing Cluster Health Services"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# Paths
SCRIPT_DIR="$STORAGE_BASE/scripts"
SERVICE_DIR="/etc/systemd/system"

# 1. Copy service files
echo "Copying service files..."
cp "$SCRIPT_DIR/cluster-health-monitor.service" "$SERVICE_DIR/"
cp "$SCRIPT_DIR/node-health-reporter.service" "$SERVICE_DIR/"
chmod 644 "$SERVICE_DIR/cluster-health-monitor.service"
chmod 644 "$SERVICE_DIR/node-health-reporter.service"
echo "✓ Service files copied"

# 2. Create log directory if needed
echo "Creating log directory..."
mkdir -p $STORAGE_BASE/logs
chown agentic:agentic $STORAGE_BASE/logs
echo "✓ Log directory ready"

# 3. Create database directory if needed
echo "Creating database directory..."
mkdir -p $STORAGE_BASE/databases
chown agentic:agentic $STORAGE_BASE/databases
echo "✓ Database directory ready"

# 4. Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# 5. Enable services (but don't start yet)
echo "Enabling services..."
systemctl enable cluster-health-monitor.service
systemctl enable node-health-reporter.service
echo "✓ Services enabled"

echo ""
echo "======================================"
echo " Installation Complete!"
echo "======================================"
echo ""
echo "Services installed:"
echo "  • cluster-health-monitor.service"
echo "  • node-health-reporter.service"
echo ""
echo "To start the services:"
echo "  sudo systemctl start cluster-health-monitor"
echo "  sudo systemctl start node-health-reporter"
echo ""
echo "To check status:"
echo "  sudo systemctl status cluster-health-monitor"
echo "  sudo systemctl status node-health-reporter"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u cluster-health-monitor -f"
echo "  sudo journalctl -u node-health-reporter -f"
echo ""
echo "Log files:"
echo "  $STORAGE_BASE/logs/cluster_health.log"
echo "  tail -f $STORAGE_BASE/logs/cluster_health.log"
echo ""
