#!/bin/bash
# Enable Docker Daemon Metrics
# This script requires sudo and will restart Docker

set -euo pipefail

echo "=== Docker Metrics Enablement ==="
echo "This script will:"
echo "  1. Backup existing /etc/docker/daemon.json"
echo "  2. Enable metrics on port 9323"
echo "  3. Restart Docker daemon"
echo ""
echo "WARNING: This will briefly interrupt all Docker containers!"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Backup existing config
if [ -f /etc/docker/daemon.json ]; then
    echo "Backing up existing /etc/docker/daemon.json..."
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create /etc/docker if it doesn't exist
sudo mkdir -p /etc/docker

# Check if daemon.json exists and merge with metrics config
if [ -f /etc/docker/daemon.json ]; then
    echo "Existing configuration found. Merging with metrics config..."

    # Read existing config
    EXISTING_CONFIG=$(sudo cat /etc/docker/daemon.json)

    # Use jq to merge if available, otherwise manual merge
    if command -v jq &> /dev/null; then
        echo "$EXISTING_CONFIG" | jq '. + {"metrics-addr": "0.0.0.0:9323", "experimental": true}' | \
            sudo tee /etc/docker/daemon.json > /dev/null
    else
        echo "Warning: jq not found. Creating new config (may overwrite existing settings)..."
        echo '{
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}' | sudo tee /etc/docker/daemon.json > /dev/null
    fi
else
    echo "Creating new /etc/docker/daemon.json..."
    echo '{
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}' | sudo tee /etc/docker/daemon.json > /dev/null
fi

# Validate JSON
if command -v jq &> /dev/null; then
    if ! sudo cat /etc/docker/daemon.json | jq empty 2>/dev/null; then
        echo "ERROR: Invalid JSON in daemon.json"
        exit 1
    fi
fi

echo ""
echo "New configuration:"
sudo cat /etc/docker/daemon.json
echo ""

# Restart Docker
echo "Restarting Docker daemon..."
sudo systemctl restart docker

# Wait for Docker to be ready
echo "Waiting for Docker to be ready..."
sleep 5
docker info > /dev/null 2>&1 || sleep 5

# Verify metrics endpoint
echo ""
echo "Verifying metrics endpoint..."
if curl -s http://localhost:9323/metrics | head -5; then
    echo ""
    echo "✓ Docker metrics successfully enabled on port 9323"
else
    echo ""
    echo "✗ Failed to access metrics endpoint"
    exit 1
fi

echo ""
echo "Done! Docker daemon metrics are now available at http://localhost:9323/metrics"
