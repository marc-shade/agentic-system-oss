# Fedora Node Integration Checklist

**Status:** Prepared by Mac Studio (Orchestrator)
**Node IP:** 192.168.1.183
**Node ID:** fedora
**Persona:** Builder

## Master Node Preparation Complete ✅

- [x] Personal database directory created
- [x] Persona state configuration created
- [x] Node pre-registered in cluster registry
- [x] Linux deployment script created
- [x] Comprehensive documentation provided
- [x] Welcome message prepared

## What the Fedora Node Needs to Do

### 1. Mount Shared Storage (CRITICAL)
```bash
sudo mkdir -p /mnt/ssdraid0
sudo mount -t cifs //192.168.1.XXX/SSDRAID0 /mnt/ssdraid0 -o username=marc,password=XXX

# Verify mount
ls -la /mnt/ssdraid0/agentic-system/
```

### 2. Run Deployment Script
```bash
cd /mnt/ssdraid0/agentic-system/cluster-deployment
chmod +x deploy-to-linux.sh
./deploy-to-linux.sh fedora
```

### 3. Start Heartbeat Service
```bash
# The deployment script will guide you through this
# Heartbeat must run every 30 seconds or node marked inactive
```

### 4. Verify Integration
```bash
# Check cluster status
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py status

# Should see:
# - mac-studio (Orchestrator)
# - macbook-air (Researcher)
# - macbook-pro (Developer)
# - fedora (Builder) ← YOU
```

## Files Waiting for Fedora Node

**Configuration:**
- `/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/persona_state.json`
- `~/.claude/node-config.json` (will be created by deployment)

**Documentation:**
- `/mnt/ssdraid0/agentic-system/cluster-deployment/FEDORA_NODE_SETUP.md`
- `/mnt/ssdraid0/agentic-system/cluster-deployment/FEDORA_WELCOME.md`
- `/mnt/ssdraid0/agentic-system/cluster-deployment/FEDORA_INTEGRATION_CHECKLIST.md` (this file)

**Scripts:**
- `/mnt/ssdraid0/agentic-system/cluster-deployment/deploy-to-linux.sh`
- `/mnt/ssdraid0/agentic-system/cluster-deployment/cluster_memory.py`
- `/mnt/ssdraid0/agentic-system/scripts/node-registry-service.py`

**Databases:**
- Personal: `/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/personal_memories.db`
- Shared: `/mnt/ssdraid0/agentic-system/databases/cluster/shared_memories.db`
- Registry: `/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db`

## Current Cluster State

```
┌─────────────────────────────────────┐
│    Mac Studio (192.168.1.XXX)       │
│    Orchestrator - Priority 1        │
│    Status: Active ✅                │
└──────────────┬──────────────────────┘
               │
               ├── MacBook Air (192.168.1.76)
               │   Researcher - Priority 2
               │   Status: Active ✅
               │
               ├── MacBook Pro (192.168.1.XXX)
               │   Developer - Priority 2
               │   Status: Registered
               │
               └── Fedora (192.168.1.183)
                   Builder - Priority 3
                   Status: Pending ⏳ ← Awaiting connection
```

## First Heartbeat Expected

Once the Fedora node:
1. Mounts shared storage
2. Runs deployment script
3. Starts heartbeat service

The orchestrator will receive the first heartbeat and activate the node, changing status from "pending" to "active".

## Network Requirements

**Must be accessible from Fedora node:**
- SMB/CIFS share on Mac Studio (port 445)
- Avahi/mDNS discovery (port 5353/udp)
- MCP servers (ports 8101, 8102, 8200) if needed

**Optional (for monitoring):**
- Prometheus node exporter (port 9100)
- Grafana dashboard access (port 9500)

## What Happens After Integration

1. **Task Assignment** - Builder receives compilation and testing tasks
2. **Memory Sync** - Can read/write to shared cluster memory
3. **Collaboration** - Coordinates with other nodes on multi-node tasks
4. **Monitoring** - Mac Studio tracks health and performance
5. **Persona Execution** - Operates according to Builder characteristics

## Troubleshooting

**If node doesn't appear in cluster:**
- Check network mount is working
- Verify deployment script completed successfully
- Check heartbeat service is running
- Look for errors in `/var/log/agentic-system/`

**If database access fails:**
- Verify SMB/CIFS mount permissions
- Check SQLite database isn't locked
- Ensure user has write access to cluster databases

**If mDNS discovery fails:**
- Check Avahi daemon is running: `systemctl status avahi-daemon`
- Verify firewall allows port 5353/udp
- Test discovery: `avahi-browse -a`

## Support

For issues during integration, the Fedora node should:
1. Review FEDORA_NODE_SETUP.md troubleshooting section
2. Check log files for error messages
3. Verify all prerequisites are met
4. Test each component individually

---

**Master Node Status:** Ready and waiting 🤝
**Next Step:** Fedora node runs deployment script
**Expected Time:** 5-10 minutes for full integration
