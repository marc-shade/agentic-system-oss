# Fedora Node Integration Guide

**Node Details:**
- IP: 192.168.1.183
- MAC: e8:06:88:ca:da:a5
- Platform: Fedora Linux on Apple Hardware
- Status: Auto-discovering and installing from network

## Critical Path Differences (macOS → Linux)

### Storage Paths
**macOS uses:**
```bash
/Volumes/SSDRAID0/agentic-system/  # Hot tier - active execution
/Volumes/FILES/agentic-system/     # Cold tier - backups only
```

**Linux should use:**
```bash
# If SSDRAID0 is network-mounted via SMB/NFS:
/mnt/ssdraid0/agentic-system/      # Remote hot tier access

# OR if local storage:
/opt/agentic-system/               # Local installation
~/agentic-system/                  # User-space installation

# Shared databases MUST be network accessible:
/mnt/ssdraid0/agentic-system/databases/cluster/
```

### Home Directory
```bash
# macOS: /Users/marc/
# Linux: /home/marc/
```

## Required Network Mounts

The Fedora node MUST have access to shared cluster databases:

```bash
# Mount SSDRAID0 (Mac Studio's shared volume)
sudo mkdir -p /mnt/ssdraid0
sudo mount -t cifs //192.168.1.XXX/SSDRAID0 /mnt/ssdraid0 -o username=marc

# OR via NFS if configured:
sudo mount -t nfs 192.168.1.XXX:/Volumes/SSDRAID0 /mnt/ssdraid0

# Add to /etc/fstab for persistence:
//192.168.1.XXX/SSDRAID0 /mnt/ssdraid0 cifs credentials=/home/marc/.smbcreds,uid=1000,gid=1000 0 0
```

## Required System Dependencies

```bash
# Python 3.11+ (required for MCP servers)
sudo dnf install python3.11 python3.11-pip python3.11-devel

# SQLite 3.35+ (for cluster databases)
sudo dnf install sqlite sqlite-devel

# Network discovery
sudo dnf install avahi avahi-tools nss-mdns

# Development tools
sudo dnf install gcc gcc-c++ make cmake git

# Optional but recommended
sudo dnf install htop iotop nethogs
```

## Python Dependencies

```bash
# Core MCP and agent runtime
pip3 install --user fastmcp anthropic openai mcp qdrant-client

# Memory system
pip3 install --user sentence-transformers chromadb

# Workflows
pip3 install --user temporalio

# Monitoring
pip3 install --user prometheus-client

# Utilities
pip3 install --user psutil zeroconf pydantic
```

## Node Configuration Template

Create `/home/marc/.claude/node-config.json`:

```json
{
  "node_id": "fedora",
  "persona_config": "/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/persona_state.json",
  "memory": {
    "local_db": "/home/marc/.local/share/agentic-system/memory.db",
    "personal_db": "/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/personal_memories.db",
    "shared_db": "/mnt/ssdraid0/agentic-system/databases/cluster/shared_memories.db",
    "node_registry_db": "/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db"
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
      "fedora": 3
    }
  }
}
```

## Suggested Persona: "Builder"

```json
{
  "node_id": "fedora",
  "persona": {
    "name": "Builder",
    "persona_id": "builder",
    "specialty": "Compilation, testing, and cross-platform validation",
    "description": "Linux-native build environment for cross-platform testing",
    "traits": [
      "methodical",
      "thorough",
      "platform-aware",
      "optimization-focused"
    ]
  },
  "capabilities": [
    "native-linux-builds",
    "container-runtime",
    "cross-platform-testing",
    "performance-profiling",
    "package-building"
  ],
  "preferred_tasks": [
    "Building Linux binaries",
    "Running test suites",
    "Docker/Podman container operations",
    "Performance benchmarking",
    "Cross-platform compatibility validation"
  ]
}
```

## Port Requirements

**Ensure these ports are accessible:**
```bash
# Cluster communication
8101  # enhanced-memory-mcp
8102  # agent-runtime-mcp
8200  # arduino-surface (relay)

# Monitoring (if running local collectors)
9100  # Node exporter
9187  # Process exporter

# Discovery
5353  # mDNS/Avahi

# SSH (for orchestration)
22    # Standard SSH
```

## Service Registration

After installation, register with cluster:

```bash
# From Fedora node:
cd /opt/agentic-system/scripts
python3 node-registry-service.py register

# Or remotely from Mac Studio:
ssh marc@192.168.1.183 "cd /opt/agentic-system/scripts && python3 node-registry-service.py register"
```

## MCP Server Compatibility Notes

### Enhanced Memory MCP
- ✅ Fully compatible (Python-based)
- Path adjustment: Use `/mnt/ssdraid0/...` for shared databases

### Agent Runtime MCP
- ✅ Fully compatible (Python-based)
- Shares task queue via cluster database

### Sequential Thinking
- ✅ Fully compatible (Python-based)

### Voice Mode MCP
- ⚠️ May require PulseAudio/PipeWire setup for TTS/STT
- Can run headless with network audio forwarding

### Arduino Surface MCP
- ❌ Not directly available (USB serial on Mac Studio)
- ✅ Can relay commands via network proxy

### Ember MCP
- ✅ Fully compatible (Python-based)

## Avahi/mDNS Discovery Setup

```bash
# Enable and start Avahi
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon

# Test discovery
avahi-browse -a

# Should see: _agentic-cluster._tcp from other nodes
```

## Firewall Configuration

```bash
# Allow cluster communication
sudo firewall-cmd --permanent --add-port=8101-8102/tcp
sudo firewall-cmd --permanent --add-port=8200/tcp
sudo firewall-cmd --permanent --add-port=5353/udp
sudo firewall-cmd --reload
```

## Critical Services to Start

```bash
# 1. Ensure shared storage is mounted
mount | grep ssdraid0

# 2. Start node registry heartbeat
cd /opt/agentic-system/scripts
nohup python3 -c "
import time
import sys
sys.path.insert(0, '.')
from node_registry_service import NodeRegistry
registry = NodeRegistry('/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db')
while True:
    registry.heartbeat('fedora')
    time.sleep(30)
" > /tmp/heartbeat.log 2>&1 &

# 3. Start MCP servers (if running local instances)
# Usually MCP servers run on Mac Studio and are accessed via network
```

## Testing Cluster Integration

```bash
# 1. Verify database access
sqlite3 /mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db "SELECT * FROM nodes WHERE node_id='fedora';"

# 2. Test shared memory access
python3 << EOF
from cluster_memory import ClusterMemoryManager
manager = ClusterMemoryManager(node_id='fedora')
manager.create_entity(
    name='fedora-test',
    entity_type='test',
    observations=['Hello from Fedora node'],
    scope='shared'
)
print("✅ Cluster memory access working")
EOF

# 3. Verify network connectivity to other nodes
ping -c 3 192.168.1.XXX  # Mac Studio IP
avahi-browse -t _agentic-cluster._tcp

# 4. Test MCP connectivity
curl http://192.168.1.XXX:8101/health
```

## Key Differences to Be Aware Of

### 1. **No Native Docker - Use Podman**
```bash
# Podman is Docker-compatible
sudo dnf install podman podman-compose
alias docker=podman
alias docker-compose=podman-compose
```

### 2. **SELinux May Block Access**
```bash
# If permission denied on mounted volumes:
sudo setenforce 0  # Temporary
# OR configure SELinux contexts properly
sudo chcon -R -t container_file_t /mnt/ssdraid0/
```

### 3. **SystemD for Service Management**
```bash
# Create systemd service for heartbeat
sudo systemctl enable agentic-heartbeat
sudo systemctl start agentic-heartbeat
```

### 4. **Log Locations**
```bash
# Linux logs:
/var/log/agentic-system/
/home/marc/.local/share/agentic-system/logs/

# NOT the macOS location:
# /Volumes/SSDRAID0/agentic-system/logs/
```

## Deployment Checklist

- [ ] Network mount to SSDRAID0 configured
- [ ] System dependencies installed
- [ ] Python dependencies installed
- [ ] Node configuration created
- [ ] Persona state created
- [ ] Avahi/mDNS running
- [ ] Firewall rules configured
- [ ] Node registered in cluster
- [ ] Heartbeat service running
- [ ] Cluster memory access tested
- [ ] Can see other nodes via discovery

## Troubleshooting

### "Permission denied" on shared databases
```bash
# Check mount permissions
ls -la /mnt/ssdraid0/agentic-system/databases/cluster/
# Should be owned by marc:marc or writable by your user
```

### "Cannot connect to MCP servers"
```bash
# MCP servers run on Mac Studio, access via network
# Check Mac Studio firewall allows connections
# Test: curl http://MAC_STUDIO_IP:8101/health
```

### "Node not appearing in cluster"
```bash
# Verify registration
python3 /opt/agentic-system/scripts/node-registry-service.py status
# Check heartbeat is running
ps aux | grep heartbeat
```

### "Database locked" errors
```bash
# SQLite doesn't handle network filesystems well
# Ensure only one process writes at a time
# Consider using WAL mode:
sqlite3 /mnt/ssdraid0/.../shared_memories.db "PRAGMA journal_mode=WAL;"
```

## Advantages of Linux Node

1. **Native container runtime** - Better than macOS Docker Desktop
2. **True multi-user** - Can run multiple agent sessions
3. **Better process isolation** - cgroups, namespaces
4. **Package ecosystem** - Direct access to Linux tools
5. **Performance** - Native Linux filesystem performance

## Recommended Workloads

The Fedora "Builder" node should focus on:
- Building and testing Python packages
- Running containerized workloads
- Long-running batch processing
- Cross-platform validation
- Performance benchmarking
- CI/CD pipeline tasks

## Important Notes

1. **ALWAYS use network paths for shared databases** - `/mnt/ssdraid0/...`
2. **Local databases for node-specific data** - `/home/marc/.local/share/...`
3. **Heartbeat every 30 seconds** - Or node marked inactive
4. **Node priority is 3** - Mac Studio (1) takes precedence in conflicts
5. **Test cluster memory before production use**
