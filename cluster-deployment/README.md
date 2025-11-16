# Cluster Memory Deployment Package

## 🌐 Multi-Node Agentic Cluster Memory System

This package enables distributed memory management across all Mac nodes in the agentic cluster.

## Package Contents

```
cluster-deployment/
├── README.md                      # This file
├── DEPLOYMENT_INSTRUCTIONS.md     # Detailed setup guide
├── INTEGRATION_CHANGES.md         # Technical integration details
├── deploy-to-node.sh             # Automated deployment script
├── cluster_memory.py             # Cluster memory manager
├── test_cluster_memory.py        # Test suite
└── server.py.integrated          # Pre-integrated server.py (from macbook-air)
```

## Quick Start

### On Each Node (mac-studio, macbook-air, macbook-pro):

```bash
# Navigate to deployment directory
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment

# Run deployment script
./deploy-to-node.sh
```

The script will:
1. ✅ Auto-detect current node (mac-studio, macbook-air, or macbook-pro)
2. ✅ Copy cluster_memory.py to MCP directory
3. ✅ Create/verify node configuration
4. ✅ Set up database directories
5. ✅ Run test suite

### Manual Integration (if needed)

If the deployment script doesn't apply server.py changes:

**Option 1: Copy integrated version**
```bash
cp server.py.integrated ~/Documents/Cline/MCP/enhanced-memory-mcp/server.py
```

**Option 2: Manual integration**
Follow the detailed instructions in `INTEGRATION_CHANGES.md`

## Node Personas

Each Mac has a specialized persona:

- **🎯 mac-studio (Orchestrator)**
  - System coordination and high-level planning
  - Priority: 1 (highest for conflict resolution)

- **🔬 macbook-air (Researcher)**
  - Analysis, documentation, investigation
  - Priority: 2
  - **Status: ✅ DEPLOYED AND TESTED**

- **💻 macbook-pro (Developer)**
  - Implementation, testing, debugging
  - Priority: 2

## Memory Architecture

```
Personal Memories (node-specific):
/Volumes/SSDRAID0/agentic-system/databases/cluster/nodes/{node-id}/personal_memories.db

Shared Memories (cluster-wide):
/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db

Node Registry (cluster coordination):
/Volumes/SSDRAID0/agentic-system/databases/cluster/node_registry.db
```

## Testing

After deployment on all nodes, test cross-node memory sharing:

**On mac-studio (or any node):**
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager

manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
manager.create_entity(
    name='orchestrator-announcement',
    entity_type='cluster-message',
    observations=['Hello from Orchestrator', 'Cluster is ready'],
    scope='shared'
)
print(f'✅ Created shared memory from {manager.node_id}')
"
```

**On macbook-air (or any other node):**
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager

manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
results = manager.search_entities('orchestrator', scope='shared')
print(f'📡 Found {len(results)} messages from other nodes:')
for r in results:
    print(f'   - {r[\"name\"]} (from {r.get(\"created_by_node\", \"unknown\")})')
"
```

## MCP Tools Available

Once integrated, each node will have these MCP tools:

- 🌐 `create_cluster_entity` - Create memories with scope (personal/shared)
- 🌐 `search_cluster_memories` - Search across scopes (personal/shared/all)
- 🌐 `get_node_memories` - Get memories from specific nodes
- 🌐 `sync_to_cluster` - Promote personal memories to shared
- 🌐 `get_cluster_stats` - View cluster memory statistics

## Verification Checklist

- [ ] Deployment script runs without errors on all nodes
- [ ] Each node can create personal memories
- [ ] Each node can create shared memories
- [ ] Each node can see memories from other nodes
- [ ] Sync operations work correctly
- [ ] Claude Code recognizes cluster memory tools
- [ ] Cross-node memory queries return expected results

## Deployment Status

| Node | Status | Persona | Deployed By |
|------|--------|---------|-------------|
| macbook-air | ✅ COMPLETE | Researcher | Researcher |
| mac-studio | ⏳ PENDING | Orchestrator | - |
| macbook-pro | ⏳ PENDING | Developer | - |

## Next Steps

1. **Deploy to mac-studio** (Orchestrator)
   - Run deployment script
   - Test cluster coordination features

2. **Deploy to macbook-pro** (Developer)
   - Run deployment script
   - Test development workflows with cluster memory

3. **Cross-Node Testing**
   - Verify all nodes can see each other's memories
   - Test memory sync operations
   - Validate conflict resolution

4. **Integration Testing**
   - Test with actual MCP tools in Claude Code
   - Verify node attribution
   - Test concurrent memory operations

## Support

For issues or questions:
- See `DEPLOYMENT_INSTRUCTIONS.md` for detailed setup
- See `INTEGRATION_CHANGES.md` for technical details
- Check troubleshooting section in deployment instructions

## Architecture Overview

```
┌─────────────────┐
│   mac-studio    │
│  (Orchestrator) │
│   Priority: 1   │
└────────┬────────┘
         │
         │ Shared Memory
         │ (/Volumes/SSDRAID0/.../shared_memories.db)
         │
    ┌────┴────┬────────────┐
    │         │            │
┌───┴────┐ ┌──┴──────┐ ┌──┴──────────┐
│macbook-│ │macbook- │ │   Node      │
│  air   │ │  pro    │ │  Registry   │
│(Research│ │(Developer│ │  Service    │
└────────┘ └─────────┘ └─────────────┘

Each node:
- Personal memories (node-specific)
- Access to shared memories (cluster-wide)
- Node attribution for all memories
- Persona-based specialization
```

---

🎉 **Ready to deploy!** Run `./deploy-to-node.sh` on each Mac to set up the cluster memory system.
