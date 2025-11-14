#!/bin/bash
#
# Linux Node Deployment Script
# Adapted for Fedora/RHEL-based systems
#

set -e

echo "🐧 Linux Node Deployment"
echo "========================"
echo ""

# Detect if we're on Linux
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "❌ This script is for Linux systems only"
    exit 1
fi

# Get node ID from argument or detect from hostname
if [ -n "$1" ]; then
    NODE_ID="$1"
else
    # Default to 'fedora' or derive from hostname
    HOSTNAME=$(hostname -s)
    NODE_ID="${HOSTNAME,,}"  # Lowercase
fi

echo "📍 Node ID: $NODE_ID"
echo ""

# Determine installation directory
if [ -d "/mnt/ssdraid0/agentic-system" ]; then
    # Network-mounted shared storage available
    CLUSTER_BASE="/mnt/ssdraid0/agentic-system"
    echo "✅ Using network-mounted cluster storage: $CLUSTER_BASE"
elif [ -w "/opt" ]; then
    # System-wide installation
    CLUSTER_BASE="/opt/agentic-system"
    echo "⚠️  Using local installation: $CLUSTER_BASE"
    echo "   Note: You'll need network access to shared cluster databases"
else
    # User-space installation
    CLUSTER_BASE="$HOME/agentic-system"
    echo "⚠️  Using user-space installation: $CLUSTER_BASE"
fi
echo ""

# Check Python version
echo "Step 1: Checking Python version"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '(?<=Python )[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.11"
if (( $(echo "$PYTHON_VERSION >= $REQUIRED_VERSION" | bc -l) )); then
    echo "✅ Python $PYTHON_VERSION (>= $REQUIRED_VERSION required)"
else
    echo "❌ Python $PYTHON_VERSION found, but $REQUIRED_VERSION or higher required"
    echo "   Install with: sudo dnf install python3.11"
    exit 1
fi
echo ""

# Install Python dependencies
echo "Step 2: Installing Python dependencies"
pip3 install --user --quiet fastmcp anthropic openai mcp qdrant-client sentence-transformers chromadb temporalio prometheus-client psutil zeroconf pydantic
echo "✅ Python dependencies installed"
echo ""

# Create directory structure
echo "Step 3: Creating directory structure"
mkdir -p "$HOME/.claude"
mkdir -p "$HOME/.local/share/agentic-system/logs"
mkdir -p "$CLUSTER_BASE/cluster-deployment"
echo "✅ Directories created"
echo ""

# Check network mount or set up paths
echo "Step 4: Configuring storage paths"
if [ -d "/mnt/ssdraid0/agentic-system/databases/cluster" ]; then
    SHARED_DB="/mnt/ssdraid0/agentic-system/databases/cluster/shared_memories.db"
    REGISTRY_DB="/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db"
    PERSONAL_DB="/mnt/ssdraid0/agentic-system/databases/cluster/nodes/$NODE_ID/personal_memories.db"
    PERSONA_CONFIG="/mnt/ssdraid0/agentic-system/databases/cluster/nodes/$NODE_ID/persona_state.json"
    echo "✅ Using network-mounted cluster databases"
else
    echo "⚠️  Network mount not available - you'll need to set up SMB/NFS mount"
    echo "   See FEDORA_NODE_SETUP.md for instructions"
    SHARED_DB="$CLUSTER_BASE/databases/cluster/shared_memories.db"
    REGISTRY_DB="$CLUSTER_BASE/databases/cluster/node_registry.db"
    PERSONAL_DB="$CLUSTER_BASE/databases/cluster/nodes/$NODE_ID/personal_memories.db"
    PERSONA_CONFIG="$CLUSTER_BASE/databases/cluster/nodes/$NODE_ID/persona_state.json"
fi
echo ""

# Create node configuration
echo "Step 5: Creating node configuration"
NODE_CONFIG="$HOME/.claude/node-config.json"
cat > "$NODE_CONFIG" <<EOF
{
  "node_id": "$NODE_ID",
  "persona_config": "$PERSONA_CONFIG",
  "memory": {
    "local_db": "$HOME/.local/share/agentic-system/memory.db",
    "personal_db": "$PERSONAL_DB",
    "shared_db": "$SHARED_DB",
    "node_registry_db": "$REGISTRY_DB"
  },
  "cluster": {
    "enabled": true,
    "discovery": {
      "method": "avahi",
      "broadcast_interval": 30,
      "service_name": "_agentic-cluster._tcp"
    }
  },
  "sync": {
    "enabled": true,
    "strategy": "eventual_consistency",
    "conflict_resolution": "last_write_wins_with_node_priority",
    "node_priority": {
      "mac-studio": 1,
      "macbook-air": 2,
      "macbook-pro": 2,
      "$NODE_ID": 3
    }
  }
}
EOF
echo "✅ Node configuration created at $NODE_CONFIG"
echo ""

# Copy cluster memory module (if available)
if [ -f "/mnt/ssdraid0/agentic-system/cluster-deployment/cluster_memory.py" ]; then
    echo "Step 6: Installing cluster memory module"
    cp /mnt/ssdraid0/agentic-system/cluster-deployment/cluster_memory.py "$HOME/.local/share/agentic-system/"
    echo "✅ Cluster memory module installed"
else
    echo "⚠️  Cluster memory module not found - will need to copy manually"
fi
echo ""

# Check Avahi
echo "Step 7: Checking mDNS discovery (Avahi)"
if systemctl is-active --quiet avahi-daemon; then
    echo "✅ Avahi daemon is running"
else
    echo "⚠️  Avahi daemon not running"
    echo "   Start with: sudo systemctl start avahi-daemon"
    echo "   Enable on boot: sudo systemctl enable avahi-daemon"
fi
echo ""

# Firewall configuration
echo "Step 8: Checking firewall configuration"
if command -v firewall-cmd &> /dev/null; then
    echo "⚠️  Firewall detected - you may need to open ports:"
    echo "   sudo firewall-cmd --permanent --add-port=8101-8102/tcp"
    echo "   sudo firewall-cmd --permanent --add-port=8200/tcp"
    echo "   sudo firewall-cmd --permanent --add-port=5353/udp"
    echo "   sudo firewall-cmd --reload"
else
    echo "✅ No firewall-cmd detected"
fi
echo ""

# Registration
echo "Step 9: Hardware discovery"
if [ -f "/mnt/ssdraid0/agentic-system/cluster-deployment/discover-hardware.py" ]; then
    echo "Running hardware discovery..."
    python3 /mnt/ssdraid0/agentic-system/cluster-deployment/discover-hardware.py "$NODE_ID"
    echo "✅ Hardware profile created"
else
    echo "⚠️  Hardware discovery script not found"
fi
echo ""

echo "Step 10: Node registration"
if [ -f "$REGISTRY_DB" ]; then
    # Try to register using the registry service
    if [ -f "/mnt/ssdraid0/agentic-system/scripts/node-registry-service.py" ]; then
        python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py register || echo "⚠️  Registration failed - may need manual intervention"
        echo "✅ Node registration attempted"
    else
        echo "⚠️  Registry service not found - manual registration required"
    fi
else
    echo "⚠️  Registry database not accessible - cannot auto-register"
    echo "   Ensure network mount is working"
fi
echo ""

# Summary
echo "===================================="
echo "📊 Deployment Summary"
echo "===================================="
echo "Node ID: $NODE_ID"
echo "Platform: Linux ($(cat /etc/redhat-release 2>/dev/null || echo 'Unknown'))"
echo "Installation: $CLUSTER_BASE"
echo "Config: $NODE_CONFIG"
echo ""
echo "Next steps:"
echo "1. Verify network mount is working: ls -la /mnt/ssdraid0/"
echo "2. Start heartbeat service (see FEDORA_NODE_SETUP.md)"
echo "3. Test cluster connectivity"
echo "4. Install and configure MCP servers (if needed)"
echo ""
echo "✅ Deployment complete!"
