# Adding completeu-server to Cluster

## Node Information

- **Node ID**: completeu-server
- **Hostname**: completeu-server.local
- **IP Address**: 192.168.1.186
- **Role**: ai-inference (Ollama Cloud inference with separate account for quota isolation)
- **Status**: Operational (confirmed in DISTRIBUTED_CLOUD_DEPLOYMENT_COMPLETE.md)

## Steps to Add completeu-server to Comprehensive Cluster State

### 1. Verify Network Connectivity

From macpro51 (or any cluster node):
```bash
ping -c 2 192.168.1.186
# Should get responses
```

### 2. Set Up SSH Key Authentication

If SSH keys aren't already set up, run from macpro51:

```bash
# Generate SSH key if needed (skip if already exists)
test -f ~/.ssh/id_ed25519 || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""

# Copy SSH key to completeu-server
ssh-copy-id marc@192.168.1.186

# Test passwordless SSH
ssh marc@192.168.1.186 "echo 'SSH working'"
```

### 3. Deploy Comprehensive State System to completeu-server

SSH into completeu-server and deploy:

```bash
ssh marc@192.168.1.186

# Navigate to agentic-system repo
cd ~/agentic-system  # Or wherever your repo is

# Pull latest changes
git pull origin main

# Install dependencies if needed
cd cluster-deployment
pip3 install psutil  # Required for inventory collection

# Test inventory collection
python3 collect_node_inventory.py

# Expected output:
# 🚀 Collecting inventory for completeu-server (ai-inference)
# 🔍 Collecting complete inventory for completeu-server...
#   📦 Collecting Python packages...
#   📦 Collecting system packages...
# ✅ Inventory collected: X interfaces, Y services, Z packages
```

### 4. Install Comprehensive State Updater Service

#### For macOS (if completeu-server is macOS):

```bash
# Create LaunchAgent
cat > ~/Library/LaunchAgents/com.agentic.comprehensive-state-updater.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic.comprehensive-state-updater</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>~/agentic-system/cluster-deployment/comprehensive_state_updater.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>~/agentic-system/logs/comprehensive-state-updater.log</string>
    <key>StandardErrorPath</key>
    <string>~/agentic-system/logs/comprehensive-state-updater-error.log</string>
    <key>WorkingDirectory</key>
    <string>~/agentic-system/cluster-deployment</string>
</dict>
</plist>
EOF

# Load and start
launchctl load ~/Library/LaunchAgents/com.agentic.comprehensive-state-updater.plist
launchctl start com.agentic.comprehensive-state-updater

# Verify
launchctl list | grep comprehensive
tail -f ~/agentic-system/logs/comprehensive-state-updater.log
```

#### For Linux (if completeu-server is Linux):

```bash
# Copy service file
sudo cp ~/agentic-system/cluster-deployment/systemd/comprehensive-state-updater.service /etc/systemd/system/

# Update paths if needed (replace /mnt/agentic-system with actual path)
sudo systemctl daemon-reload
sudo systemctl enable comprehensive-state-updater.service
sudo systemctl start comprehensive-state-updater.service

# Verify
sudo systemctl status comprehensive-state-updater.service
sudo journalctl -u comprehensive-state-updater.service -f
```

### 5. Verify completeu-server in Cluster State

From any cluster node:

```bash
cd ~/agentic-system/cluster-deployment

# Query cluster state
python3 -c "
from comprehensive_cluster_state import get_complete_state
import json

state = get_complete_state()
print(f'Total nodes: {len(state[\"nodes\"])}')
print('Nodes:')
for node_id in state['nodes'].keys():
    print(f'  - {node_id}')
"

# Should show:
# Total nodes: 2 (or more)
# Nodes:
#   - macpro51
#   - completeu-server
```

### 6. Verify SSH Connectivity from All Nodes

The comprehensive state system tests SSH connectivity automatically. Check the database:

```bash
sqlite3 ~/agentic-system/databases/cluster/comprehensive_state.db << 'EOF'
SELECT source_node_id, target_node_id, is_reachable, has_key_auth, latency_ms
FROM ssh_connectivity
WHERE target_node_id = 'completeu-server' OR source_node_id = 'completeu-server';
EOF
```

## What Gets Cataloged for completeu-server

Once integrated, the comprehensive cluster state will automatically catalog:

### Node Information
- Hostname, OS type, architecture
- CPU count, model, memory, disk
- Python version, kernel
- Role: ai-inference

### Network Interfaces
- All network interfaces with IPs, MACs, speeds
- Traffic statistics (bytes sent/received)

### Services
- **Ollama** (port 11434) - AI inference with separate account
- Any other services running on the node
- Port bindings, protocols, health status

### Software Inventory
- All pip packages
- All system packages (brew/apt/dnf)
- npm global packages
- Versions and installation paths

### Capabilities
- ollama availability and version
- docker/podman if installed
- GPU if available
- Build tools

### SSH Connectivity
- Connectivity tests to all other nodes
- Latency measurements
- Key authentication status

## completeu-server's Role in Cluster

**Primary Role**: AI Inference with Quota Isolation
- Dedicated Ollama Cloud account for completeu-server
- Separate from main cluster quota
- Load balancing target for cloud inference
- 20B parameter model access

**Integration with Multi-AI System**:
- Claude, Codex, and Gemini agents can query completeu-server's state
- Completeu-server participates in cluster-wide orchestration
- Performance metrics feed into Gemini's analysis
- Package inventory feeds into Codex's security audits

## Testing the Integration

```bash
# From macpro51, test that completeu-server is in cluster
cd ~/agentic-system/intelligent-agents/specialized
python3 cluster_multi_ai_guardian.py

# Should show completeu-server in cluster state queries
```

## Troubleshooting

### SSH Connection Issues

If SSH isn't working:
```bash
# Check SSH connectivity
ssh -v marc@192.168.1.186

# Verify SSH keys
ls -la ~/.ssh/id_ed25519*

# Re-add key if needed
ssh-copy-id marc@192.168.1.186
```

### Service Not Starting

Check logs:
```bash
# macOS
tail -100 ~/agentic-system/logs/comprehensive-state-updater-error.log

# Linux
sudo journalctl -u comprehensive-state-updater.service --no-pager | tail -100
```

### Inventory Collection Fails

Test manually:
```bash
cd ~/agentic-system/cluster-deployment
python3 collect_node_inventory.py

# Check for errors in output
```

## Expected Result

After completing these steps:

✅ completeu-server added to comprehensive cluster state
✅ Automatic inventory updates every 5 minutes
✅ SSH connectivity tested and working
✅ All AI agents (Claude, Codex, Gemini) can query completeu-server state
✅ Cluster now has 4 nodes (macpro51, mac-studio, macbook-air, completeu-server)

---

*completeu-server node configuration: ai-inference role with Ollama Cloud quota isolation*
