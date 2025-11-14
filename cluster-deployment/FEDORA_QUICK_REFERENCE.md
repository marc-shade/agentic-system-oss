# Fedora Node Quick Reference Card

**Your Role:** Builder | **Your IP:** 192.168.1.183 | **Priority:** 3

## Essential Commands

### Initial Setup (Run Once)
```bash
# 1. Mount shared storage
sudo mkdir -p /mnt/ssdraid0
sudo mount -t cifs //MAC_STUDIO_IP/SSDRAID0 /mnt/ssdraid0 -o username=marc

# 2. Run deployment
cd /mnt/ssdraid0/agentic-system/cluster-deployment
./deploy-to-linux.sh fedora

# 3. Verify integration
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py status
```

### Daily Operations
```bash
# Check cluster status
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py status

# Send heartbeat manually
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py heartbeat

# View your hardware profile
cat ~/.local/share/agentic-system/hardware_profile.json

# Check if heartbeat service is running
ps aux | grep heartbeat

# View logs
tail -f ~/.local/share/agentic-system/logs/*.log
```

## Critical Paths

### Your Configuration
```
~/.claude/node-config.json
```

### Your Databases
```
Personal:  /mnt/ssdraid0/.../nodes/fedora/personal_memories.db
Shared:    /mnt/ssdraid0/.../cluster/shared_memories.db
Registry:  /mnt/ssdraid0/.../cluster/node_registry.db
```

### Your Documentation
```
/mnt/ssdraid0/agentic-system/cluster-deployment/
  ├── FEDORA_NODE_SETUP.md           (Complete guide)
  ├── FEDORA_WELCOME.md              (Your role explained)
  ├── FEDORA_INTEGRATION_CHECKLIST.md
  └── FEDORA_QUICK_REFERENCE.md      (This file)
```

## Your Capabilities (Builder Persona)

**You specialize in:**
- Linux binary compilation
- Cross-platform testing
- Container operations (Podman)
- Performance benchmarking
- Long-running batch jobs
- CI/CD execution

**Available tools detected by hardware discovery:**
- cmake, make, gcc, g++, clang
- python3, node, npm, cargo, go
- podman, buildah (container runtimes)
- perf, valgrind (profiling)

## Task Types You'll Receive

1. **Build Tasks** - Compile projects for Linux targets
2. **Test Tasks** - Run comprehensive test suites
3. **Container Tasks** - Build and manage containers
4. **Benchmark Tasks** - Profile and measure performance
5. **Validation Tasks** - Cross-platform compatibility checks

## Cluster Communication

**Heartbeat:** Every 30 seconds → `/mnt/ssdraid0/.../node_registry.db`
**Discovery:** Avahi broadcasts on `_agentic-cluster._tcp`
**Task Queue:** Via shared database (eventual consistency)
**Priority:** 3 (mac-studio=1, macbook-air/pro=2, you=3)

## Network Ports

**MCP Servers (on Mac Studio):**
- 8101 - enhanced-memory-mcp
- 8102 - agent-runtime-mcp
- 8200 - arduino-surface

**Discovery:**
- 5353/udp - mDNS/Avahi

**Your Firewall Rules:**
```bash
sudo firewall-cmd --permanent --add-port=8101-8102/tcp
sudo firewall-cmd --permanent --add-port=8200/tcp
sudo firewall-cmd --permanent --add-port=5353/udp
sudo firewall-cmd --reload
```

## Troubleshooting Quick Fixes

**"Cannot access databases"**
```bash
# Check mount
mount | grep ssdraid0
# Remount if needed
sudo mount -t cifs //MAC_STUDIO_IP/SSDRAID0 /mnt/ssdraid0 -o username=marc
```

**"Node not showing in cluster"**
```bash
# Check heartbeat is running
ps aux | grep heartbeat
# Restart if needed
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py register
```

**"Permission denied on shared storage"**
```bash
# Check SELinux
sudo setenforce 0  # Temporary
# Or configure properly:
sudo chcon -R -t container_file_t /mnt/ssdraid0/
```

## Your Performance Score

After hardware discovery completes, you'll have a score like:
```
Performance Score: 85.2

Based on:
- CPU cores × 10
- RAM (GB) × 2
- Storage speed bonus
- Available tools bonus
```

This score determines task assignment priority.

## Integration Status Checklist

- [ ] Shared storage mounted
- [ ] Deployment script completed
- [ ] Hardware profile generated
- [ ] Node registered (status: pending → active)
- [ ] Heartbeat service running
- [ ] Can read/write cluster databases
- [ ] Avahi discovery broadcasting
- [ ] First task received and completed

## Getting Help

**Documentation:** All `.md` files in `/mnt/ssdraid0/agentic-system/cluster-deployment/`
**Logs:** `~/.local/share/agentic-system/logs/`
**Cluster Status:** `python3 .../node-registry-service.py status`
**Hardware Info:** `cat ~/.local/share/agentic-system/hardware_profile.json`

---

**Welcome to the cluster, Builder! 🐧🔧**
