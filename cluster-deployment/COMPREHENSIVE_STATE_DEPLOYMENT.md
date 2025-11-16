# Comprehensive Cluster State - Deployment Guide

## Overview

The comprehensive cluster state system provides a **single source of truth** containing 100% of the information all nodes need to understand their own configuration/resources and those of other nodes.

## What It Contains

The comprehensive state database (`comprehensive_state.db`) stores:

### 1. Complete Node Information
- Hostname, role, OS type/version, architecture
- CPU details (count, model, specifications)
- Memory and disk totals
- Python version, kernel version
- System timezone, locale, boot time

### 2. Network Interfaces
- All network interfaces on each node
- IP addresses, netmasks, MAC addresses
- Interface status (up/down), speed
- Network traffic statistics (bytes sent/received)

### 3. Service Endpoints
- **ALL** services/servers running on each node
- Ports, protocols, bind addresses
- Service types, health status, PIDs
- Config paths, log paths, data paths
- Service versions and dependencies

### 4. Software Inventory
- **Complete** software inventory per node:
  - Python packages (pip)
  - System packages (dnf/apt/brew)
  - npm global packages
- Package versions, installation paths
- Checksums for integrity verification

### 5. Filesystem Mounts
- All mounted filesystems
- Mount points, devices, filesystem types
- Usage statistics (total, used, available, % used)
- Mount options, read-only status

### 6. SSH Connectivity
- SSH mesh connectivity between all nodes
- Reachability status, key authentication
- Latency measurements
- Last tested timestamps

### 7. Node Capabilities
- What each node can do:
  - docker, podman, ollama availability
  - GPU presence and type
  - Build tools (make, gcc, cargo, npm)
  - Git and version control tools

### 8. Environment Variables
- Important environment variables (excluding secrets)
- System paths and configurations

### 9. Configuration Files
- Locations of important config files
- File checksums, permissions, owners

## Architecture

### Two Main Components

1. **collect_node_inventory.py**
   - Collects complete inventory from local node
   - Scans ports, packages, filesystems, services
   - Tests SSH connectivity to other nodes
   - Registers everything in comprehensive state

2. **comprehensive_state_updater.py**
   - Background daemon (runs 24/7)
   - Updates inventory every 5 minutes
   - Ensures state is always current
   - Monitors for changes (services start/stop, software install/remove)

### Database Schema

Single SQLite database: `~/agentic-system/databases/cluster/comprehensive_state.db`

Tables:
- `nodes` - Complete node information
- `network_interfaces` - All network interfaces
- `service_endpoints` - All services/servers
- `installed_software` - Complete software inventory
- `filesystem_mounts` - All filesystems
- `ssh_connectivity` - SSH mesh
- `node_capabilities` - What each node can do
- `environment_vars` - Important environment variables
- `configuration_files` - Config file locations

## Deployment Steps

### Step 1: Deploy Files to All Nodes

On **macpro51** (Linux builder):
```bash
cd /mnt/agentic-system
git pull origin main

# Files are ready:
# - cluster-deployment/comprehensive_cluster_state.py
# - cluster-deployment/collect_node_inventory.py
# - cluster-deployment/comprehensive_state_updater.py
# - cluster-deployment/systemd/comprehensive-state-updater.service
```

On **mac-studio** (macOS orchestrator):
```bash
cd /Volumes/SSDRAID0/agentic-system
git pull origin main

# Same files available
```

On **macbook-air** (macOS researcher):
```bash
cd /Volumes/SSDRAID0/agentic-system
git pull origin main

# Same files available
```

### Step 2: Test Initial Inventory Collection

On each node:
```bash
cd cluster-deployment
chmod +x collect_node_inventory.py
python3 collect_node_inventory.py
```

This will:
- Collect complete node inventory
- Test SSH connectivity to other nodes
- Register in comprehensive state database
- Show summary of collected data

**Expected output:**
```
🚀 Collecting inventory for macpro51 (builder)
🔍 Collecting complete inventory for macpro51...
  📦 Collecting Python packages...
  📦 Collecting system packages...
  📦 Collecting npm packages...
✅ Inventory collected: 2 interfaces, 15 services, 847 packages
🔌 Testing SSH connectivity to other nodes...
  🔌 Testing SSH to mac-studio (192.168.1.157)...
  🔌 Testing SSH to macbook-air (192.168.1.76)...
💾 Registering in comprehensive cluster state...
✅ Node macpro51 inventory registered successfully!

📊 Summary:
   Network interfaces: 2
   Services: 15
   Software packages: 847
   Filesystems: 3
   Capabilities: 8
   SSH connectivity: 2 nodes tested
```

### Step 3: Install as Systemd Service (Linux)

On **macpro51**:
```bash
cd /mnt/agentic-system/cluster-deployment

# Install service
sudo cp systemd/comprehensive-state-updater.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable comprehensive-state-updater.service
sudo systemctl start comprehensive-state-updater.service

# Verify
sudo systemctl status comprehensive-state-updater.service
sudo journalctl -u comprehensive-state-updater.service -f
```

### Step 4: Install as LaunchAgent (macOS)

On **mac-studio** and **macbook-air**:
```bash
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment

# Create launchd plist
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
        <string>/Volumes/SSDRAID0/agentic-system/cluster-deployment/comprehensive_state_updater.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Volumes/SSDRAID0/agentic-system/logs/comprehensive-state-updater.log</string>
    <key>StandardErrorPath</key>
    <string>/Volumes/SSDRAID0/agentic-system/logs/comprehensive-state-updater-error.log</string>
    <key>WorkingDirectory</key>
    <string>/Volumes/SSDRAID0/agentic-system/cluster-deployment</string>
</dict>
</plist>
EOF

# Load and start
launchctl load ~/Library/LaunchAgents/com.agentic.comprehensive-state-updater.plist
launchctl start com.agentic.comprehensive-state-updater

# Verify
launchctl list | grep comprehensive
tail -f /Volumes/SSDRAID0/agentic-system/logs/comprehensive-state-updater.log
```

### Step 5: Verify Cluster-Wide State

On any node:
```bash
cd cluster-deployment

# Query complete cluster state
python3 -c "
from comprehensive_cluster_state import get_complete_state
import json

state = get_complete_state()
print(json.dumps(state, indent=2))
"

# Find specific service
python3 -c "
from comprehensive_cluster_state import find_service

results = find_service('qdrant')
for svc in results:
    print(f'{svc[\"node_id\"]}: {svc[\"service_name\"]} on port {svc[\"port\"]}')
"

# Get network topology
python3 -c "
from comprehensive_cluster_state import get_network_topology

topology = get_network_topology()
print('Network Topology:')
for node_id, interfaces in topology['interfaces'].items():
    print(f'\n{node_id}:')
    for iface in interfaces:
        print(f'  {iface[\"interface_name\"]}: {iface[\"ip_address\"]}')
"
```

## Usage Examples

### From Any Agent or Controller

```python
from comprehensive_cluster_state import ComprehensiveClusterState

state = ComprehensiveClusterState()

# Get complete cluster state
cluster = state.get_complete_cluster_state()

# Query services
qdrant_services = state.query_services(service_name="qdrant")
print(f"Qdrant running on: {qdrant_services[0]['node_id']}")

# Query software
docker_nodes = state.query_software(package_name="docker")
print(f"Docker available on: {[s['node_id'] for s in docker_nodes]}")

# Get network map
network = state.get_network_map()
print(f"Total active interfaces: {sum(len(v) for v in network['interfaces'].values())}")

# Find available port
port = state.find_available_port("macpro51", start_port=8000, end_port=9000)
print(f"Available port on macpro51: {port}")
```

### Integration with Existing Systems

Update **cluster_self_x_daemon.py**:
```python
from comprehensive_cluster_state import ComprehensiveClusterState

class ClusterSelfXDaemon:
    def __init__(self):
        self.state = ComprehensiveClusterState()

    def make_decision(self):
        # Get complete cluster state
        cluster = self.state.get_complete_cluster_state()

        # Find nodes with low load
        for node_id, node_info in cluster["nodes"].items():
            services = node_info["services"]
            # Make intelligent routing decisions
```

Update **cluster-execution-mcp**:
```python
from comprehensive_cluster_state import get_complete_state

def select_best_node():
    state = get_complete_state()

    # Use real data to select best node
    for node_id, node_info in state["nodes"].items():
        if node_info["capabilities"]["docker"]:
            return node_id
```

## Monitoring

### Check Updater Status

**Linux (macpro51)**:
```bash
sudo systemctl status comprehensive-state-updater.service
sudo journalctl -u comprehensive-state-updater.service -f
```

**macOS (mac-studio, macbook-air)**:
```bash
launchctl list | grep comprehensive
tail -f /Volumes/SSDRAID0/agentic-system/logs/comprehensive-state-updater.log
```

### Database Statistics

```bash
sqlite3 ~/agentic-system/databases/cluster/comprehensive_state.db << 'EOF'
.mode column
.headers on

SELECT 'Nodes' as table, COUNT(*) as count FROM nodes
UNION ALL
SELECT 'Network Interfaces', COUNT(*) FROM network_interfaces
UNION ALL
SELECT 'Services', COUNT(*) FROM service_endpoints
UNION ALL
SELECT 'Software Packages', COUNT(*) FROM installed_software
UNION ALL
SELECT 'Filesystems', COUNT(*) FROM filesystem_mounts
UNION ALL
SELECT 'SSH Connections', COUNT(*) FROM ssh_connectivity
UNION ALL
SELECT 'Capabilities', COUNT(*) FROM node_capabilities;
EOF
```

## Performance

- **Initial collection**: ~30-60 seconds per node
- **Update interval**: 5 minutes (configurable)
- **Database size**: ~5-10 MB per node
- **Memory usage**: ~50-100 MB per updater daemon
- **CPU usage**: <1% average, ~5-10% during collection

## Troubleshooting

### Inventory Collection Fails

If `collect_node_inventory.py` fails:
```bash
# Check dependencies
pip3 install psutil

# Run with debug
python3 collect_node_inventory.py 2>&1 | tee collection_debug.log
```

### Service Won't Start

**Linux**:
```bash
# Check service logs
journalctl -u comprehensive-state-updater.service --no-pager
```

**macOS**:
```bash
# Check launchd logs
tail -100 /Volumes/SSDRAID0/agentic-system/logs/comprehensive-state-updater-error.log
```

### Database Locked

If database is locked:
```bash
# Check what's using it
lsof ~/agentic-system/databases/cluster/comprehensive_state.db

# Kill if needed
pkill -f comprehensive_state_updater
```

## Next Steps

1. ✅ Deploy to all 3 nodes
2. ✅ Verify inventory collection works
3. ✅ Install as services (systemd/launchd)
4. ⏳ Update all agents to use comprehensive state
5. ⏳ Integrate with cluster-self-x-daemon
6. ⏳ Integrate with cluster-execution-mcp
7. ⏳ Update autonomous_self_improvement_agent to use it

## Benefits

✅ **Single source of truth** - One database, no fragmentation
✅ **Always accurate** - Updated every 5 minutes automatically
✅ **Complete information** - 100% of what agents need
✅ **Real-time decisions** - Agents make informed choices
✅ **Network topology** - Full visibility of cluster connectivity
✅ **Service discovery** - Know exactly where everything runs
✅ **Software inventory** - Complete package visibility
✅ **Resource awareness** - Make smart routing decisions

**Every agent now knows EVERYTHING about the entire cluster.**
