# Cluster Memory System Deployment

## Overview
This deployment package sets up cluster-aware memory management across all nodes in the agentic cluster.

## Node Configuration

### Current Nodes:
- **mac-studio** (Orchestrator) - System coordination, high-level planning
- **macbook-air** (Researcher) - Analysis, documentation, investigation
- **macbook-pro** (Developer) - Implementation, testing, debugging

## Deployment Steps

### On Each Node:

#### 1. Copy cluster_memory.py to MCP server directory
```bash
cp /Volumes/SSDRAID0/agentic-system/cluster-deployment/cluster_memory.py ~/Documents/Cline/MCP/enhanced-memory-mcp/
```

#### 2. Verify node configuration exists
```bash
cat ~/.claude/node-config.json
```

Expected structure:
```json
{
  "node_id": "mac-studio",  // or "macbook-air" or "macbook-pro"
  "persona_config": "/Volumes/SSDRAID0/agentic-system/databases/cluster/nodes/{node-id}/persona_state.json",
  "memory": {
    "local_db": "~/Documents/Cline/MCP/enhanced-memory-mcp/memory.db",
    "personal_db": "/Volumes/SSDRAID0/agentic-system/databases/cluster/nodes/{node-id}/personal_memories.db",
    "shared_db": "/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db",
    "node_registry_db": "/Volumes/SSDRAID0/agentic-system/databases/cluster/node_registry.db"
  },
  "cluster": {
    "enabled": true,
    "discovery": {
      "method": "bonjour",
      "broadcast_interval": 30,
      "service_name": "_agentic-cluster._tcp"
    }
  }
}
```

#### 3. Apply server.py updates
The server.py file needs to be updated with cluster memory integration. See INTEGRATION_CHANGES.md for details.

#### 4. Test cluster memory
```bash
cd ~/Documents/Cline/MCP/enhanced-memory-mcp
python3 /Volumes/SSDRAID0/agentic-system/cluster-deployment/test_cluster_memory.py
```

#### 5. Restart Claude Code
Restart Claude Code to load the updated MCP server with cluster memory support.

## Verification

After deployment on all nodes, verify:

1. **Each node can create personal memories**
2. **Each node can create shared memories**
3. **Each node can see memories from other nodes**
4. **Sync operations work correctly**

## Testing Cross-Node Memory

Run this on one node:
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager

manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')

# Create a shared memory
manager.create_entity(
    name='test-from-' + manager.node_id,
    entity_type='test',
    observations=['Created by ' + manager.node_id, 'Testing cluster sync'],
    scope='shared'
)

print(f'✅ Created test memory from {manager.node_id}')
"
```

Then on another node, search for it:
```bash
python3 -c "
from pathlib import Path
from cluster_memory import ClusterMemoryManager

manager = ClusterMemoryManager(Path.home() / '.claude' / 'node-config.json')
results = manager.search_entities('test-from-', scope='shared')
print(f'Found {len(results)} memories from other nodes:')
for r in results:
    print(f'  - {r[\"name\"]} (created by {r.get(\"created_by_node\", \"unknown\")})')
"
```

## Troubleshooting

### Database not found
- Ensure `/Volumes/SSDRAID0/agentic-system/databases/cluster/` exists
- Check node configuration paths are correct

### No shared memories visible
- Verify shared_db path points to the same file on all nodes
- Check file permissions on shared storage

### Personal database errors
- Delete and recreate: `rm {personal_db_path} && python3 test_cluster_memory.py`

## Architecture

```
/Volumes/SSDRAID0/agentic-system/databases/cluster/
├── shared_memories.db              # All nodes share this
├── node_registry.db                # Node discovery and health
└── nodes/
    ├── mac-studio/
    │   ├── personal_memories.db
    │   └── persona_state.json
    ├── macbook-air/
    │   ├── personal_memories.db
    │   └── persona_state.json
    └── macbook-pro/
        ├── personal_memories.db
        └── persona_state.json
```

## Status

- ✅ macbook-air (Researcher) - DEPLOYED AND TESTED
- ⏳ mac-studio (Orchestrator) - PENDING
- ⏳ macbook-pro (Developer) - PENDING
