#!/bin/bash
# One-liner bootstrap for mac-studio after macOS reinstall
# Run: curl -sSL http://macpro51.local:9000/bootstrap/mac-studio.sh | bash

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

echo "=== Mac-Studio Quick Reconnect ==="
echo "This script reconnects mac-studio to the agentic cluster after OS reinstall"
echo ""

# Check if running on mac-studio
if [[ "$(hostname)" != *"Mac-Studio"* ]] && [[ "$(hostname)" != *"studio"* ]]; then
    echo "Warning: This doesn't appear to be mac-studio"
    echo "Hostname: $(hostname)"
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Check for Homebrew
echo "[1/6] Checking Homebrew..."
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Step 2: Install essentials
echo "[2/6] Installing essential packages..."
brew install python3 node git sqlite jq 2>/dev/null || true

# Step 3: Check external drives
echo "[3/6] Checking external drives..."
if [ ! -d "$STORAGE_BASE" ]; then
    echo "ERROR: SSDRAID0 not mounted or agentic-system not found"
    echo "Please mount SSDRAID0 and ensure /Volumes/SSDRAID0/agentic-system exists"
    exit 1
fi
echo "  ✓ SSDRAID0 found"

# Step 4: Setup Python environment
echo "[4/6] Setting up Python environment..."
cd /Volumes/SSDRAID0/agentic-system

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r mcp-servers/enhanced-memory-mcp/requirements.txt -q 2>/dev/null || true

# Step 5: Setup Claude Code config
echo "[5/6] Configuring Claude Code..."
mkdir -p ~/.claude

if [ ! -f ~/.claude.json ]; then
    # Try to restore from backup
    if [ -f "$STORAGE_BASE/.claude.json.backup" ]; then
        cp $STORAGE_BASE/.claude.json.backup ~/.claude.json
    else
        # Create minimal config
        cat > ~/.claude.json << 'CLAUDEJSON'
{
  "version": "1.0",
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["$STORAGE_BASE/mcp-servers/enhanced-memory-mcp/server.py"],
      "env": {},
      "disabled": false
    },
    "agent-runtime": {
      "command": "python3",
      "args": ["$STORAGE_BASE/mcp-servers/agent-runtime-mcp/server.py"],
      "env": {},
      "disabled": false
    }
  }
}
CLAUDEJSON
    fi
    echo "  Created ~/.claude.json"
fi

# Step 6: Restore SSH keys from cluster
echo "[6/6] Restoring SSH keys..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

SURVIVING_NODES=("macpro51.local" "completeu-server.local" "Marcs-MacBook-Air.local")
SSH_RESTORED=false

for node in "${SURVIVING_NODES[@]}"; do
    if ping -c 1 -W 2 "$node" &>/dev/null; then
        echo "  Trying to get SSH keys from $node..."
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
            "marc@$node:~/.ssh/id_ed25519" ~/.ssh/ 2>/dev/null && SSH_RESTORED=true
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
            "marc@$node:~/.ssh/id_ed25519.pub" ~/.ssh/ 2>/dev/null || true
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
            "marc@$node:~/.ssh/authorized_keys" ~/.ssh/ 2>/dev/null || true
        chmod 600 ~/.ssh/id_ed25519 2>/dev/null || true
        if [ "$SSH_RESTORED" = true ]; then
            echo "  ✓ SSH keys restored from $node"
            break
        fi
    fi
done

if [ "$SSH_RESTORED" = false ]; then
    echo "  ⚠ Could not restore SSH keys automatically"
    echo "  Please manually copy SSH keys or generate new ones"
fi

# Verify
echo ""
echo "=== Verification ==="
echo ""

# Check cluster connectivity
echo "Cluster nodes:"
for node in "${SURVIVING_NODES[@]}"; do
    if ping -c 1 -W 1 "$node" &>/dev/null; then
        echo "  ✓ $node - reachable"
    else
        echo "  ✗ $node - unreachable"
    fi
done

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Mac-studio is reconnected to the cluster!"
echo ""
echo "Next steps:"
echo "  1. cd /Volumes/SSDRAID0/agentic-system"
echo "  2. source .venv/bin/activate"
echo "  3. python3 system_health_check.py"
echo ""
echo "To reclaim orchestrator role:"
echo "  cd cluster-deployment && python3 resilient_cluster.py --status"
echo ""
