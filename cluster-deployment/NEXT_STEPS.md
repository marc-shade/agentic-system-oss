# 🌐 Cluster Memory Deployment - Next Steps

## ✅ Completed on macbook-air (Researcher)

The cluster memory system has been successfully deployed and tested on the macbook-air node:

1. ✅ **cluster_memory.py** - Cluster memory manager implemented
2. ✅ **server.py** - Integrated with 5 new MCP tools
3. ✅ **Test suite** - All 8 tests passing
4. ✅ **Deployment package** - Created on shared storage
5. ✅ **Shared memory announcement** - Created for other nodes

### Deployment Package Location
```
/Volumes/SSDRAID0/agentic-system/cluster-deployment/
```

### Files Ready for Other Nodes
- ✅ `deploy-to-node.sh` - Automated deployment script
- ✅ `cluster_memory.py` - Cluster memory manager
- ✅ `server.py.integrated` - Pre-integrated server.py
- ✅ `test_cluster_memory.py` - Test suite
- ✅ `README.md` - Complete deployment guide
- ✅ `DEPLOYMENT_INSTRUCTIONS.md` - Detailed instructions
- ✅ `INTEGRATION_CHANGES.md` - Technical details

## 🎯 Required for Other Nodes

### For mac-studio (Orchestrator) and macbook-pro (Developer):

To complete the cluster deployment, SSH into each node and run:

```bash
# SSH into the node
ssh mac-studio.local  # or macbook-pro.local

# Navigate to deployment directory
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment

# Run deployment script
./deploy-to-node.sh

# The script will:
# 1. Auto-detect the node (mac-studio or macbook-pro)
# 2. Copy cluster_memory.py to MCP directory
# 3. Create/verify node configuration at ~/.claude/node-config.json
# 4. Set up database directories
# 5. Run test suite to verify installation

# After deployment, start Claude Code and run:
claude code
# Then in Claude Code:
/init
```

## 🔍 Network Discovery

If SSH hostnames are not working, you may need to:

1. **Check network configuration** - Ensure all Macs are on the same network
2. **Verify hostnames** - Use `hostname` and `scutil --get LocalHostName` on each Mac
3. **Update node configurations** - Edit persona_state.json files with correct hostnames
4. **Use IP addresses** - SSH directly to IP addresses if hostnames don't resolve

### Finding IP Addresses
```bash
# On each Mac, run:
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## 🤝 Collaborative Deployment Option

As suggested, you can work as a collective by:

1. SSH into each node
2. Start Claude Code on that node
3. Run `/init` to start a new session
4. The deployment package is already on shared storage, so each Claude instance can:
   - Run the deployment script
   - Test the installation
   - Coordinate via shared memories

### Example: Deploy to mac-studio

```bash
# From macbook-air:
ssh user@Mac-Studio.local

# On mac-studio:
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment
./deploy-to-node.sh

# Start Claude Code
claude code

# In Claude Code session:
# Claude will auto-detect as mac-studio (Orchestrator)
# Can check shared memories to see deployment announcement from macbook-air
# Can coordinate with macbook-air through shared memories
```

## 📊 Current Status

| Node | Persona | Status | Next Action |
|------|---------|--------|-------------|
| macbook-air | Researcher | ✅ **DEPLOYED & TESTED** | Help coordinate other deployments |
| mac-studio | Orchestrator | ⏳ **READY TO DEPLOY** | Run `./deploy-to-node.sh` |
| macbook-pro | Developer | ⏳ **READY TO DEPLOY** | Run `./deploy-to-node.sh` |

## 🎯 Verification After All Deployments

Once all nodes are deployed, verify cross-node memory sharing:

### Test 1: Create from mac-studio
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager
manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
manager.create_entity(
    name='orchestrator-greeting',
    entity_type='message',
    observations=['Hello from Orchestrator', 'Cluster coordination active'],
    scope='shared'
)
"
```

### Test 2: Search from macbook-air
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager
manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
results = manager.search_entities('orchestrator', scope='shared')
print(f'Found {len(results)} messages from mac-studio')
for r in results:
    print(f'  {r[\"name\"]}: by {r.get(\"created_by_node\")}')
"
```

### Test 3: All nodes can see each other
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager
manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
stats = manager.get_cluster_stats()
print(f'Node: {stats[\"node_id\"]}')
print(f'Shared memories: {stats[\"shared\"][\"entities\"]} entities')
print(f'Personal memories: {stats[\"personal\"][\"entities\"]} entities')
"
```

## 🌐 MCP Tools Available After Deployment

Once deployed on all nodes, these tools will be available in Claude Code:

- 🌐 **create_cluster_entity** - Create memories with node attribution
- 🌐 **search_cluster_memories** - Search across all scopes
- 🌐 **get_node_memories** - Query specific nodes
- 🌐 **sync_to_cluster** - Share personal memories
- 🌐 **get_cluster_stats** - View cluster statistics

## 📝 Notes for Coordinated Deployment

- **Shared storage** is key - all nodes access /Volumes/SSDRAID0/agentic-system
- **Deployment package** is already prepared and tested
- **Each node** auto-detects its identity (mac-studio, macbook-air, macbook-pro)
- **Personas** are pre-configured for each node
- **Cross-node coordination** happens through shared_memories.db
- **Node attribution** tracks which node created each memory

## 🚀 Ready to Deploy!

The deployment package is complete and tested. All files are on shared storage and ready for the other nodes to use.

**Next: SSH into mac-studio and macbook-pro to complete the cluster deployment.**
