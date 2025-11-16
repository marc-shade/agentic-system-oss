# Cluster Deployment Package

## 🌐 Multi-Node Agentic Cluster System

This package enables distributed memory management and automatic task execution across all nodes in the agentic cluster.

## ✨ What's Included

### 🚀 Distributed Task Execution (NEW!)
**Status**: ✅ FULLY OPERATIONAL - 7/7 tests passed

Automatic workload distribution across cluster nodes with aggressive offloading:
- **Automatic routing** - Tasks route to optimal node based on OS, architecture, and capabilities
- **Aggressive offloading** - Keeps active node free (0 local tasks, 10 remote tasks in testing)
- **Smart distribution** - Linux → macpro51, macOS → Mac Studio/MacBook Air
- **Simple API** - One-line task submission: `offload("command")`
- **Parallel execution** - Distribute multiple tasks across cluster

See `DISTRIBUTED_EXECUTION.md` for complete documentation.

### 🧠 Cluster Memory System
Shared memory management across all Mac nodes in the cluster.

## Package Contents

```
cluster-deployment/
├── README.md                          # This file
├── DISTRIBUTED_EXECUTION.md           # 🚀 Distributed execution guide
├── WORKLOAD_DISTRIBUTION_DESIGN.md    # Architecture and design
├── distributed_task_router.py         # Core routing engine
├── cluster_offload.py                 # Simple task offload API
├── test_distributed_execution.py      # Test suite (7/7 passing)
├── DEPLOYMENT_INSTRUCTIONS.md         # Detailed setup guide
├── INTEGRATION_CHANGES.md             # Technical integration details
├── deploy-to-node.sh                  # Automated deployment script
├── cluster_memory.py                  # Cluster memory manager
├── test_cluster_memory.py             # Memory test suite
└── server.py.integrated               # Pre-integrated server.py
```

## Quick Start

### 🚀 Distributed Task Execution (Ready to Use!)

**From any node**, automatically offload tasks to the cluster:

```python
from cluster_offload import offload

# Just submit - automatic routing!
result = offload("echo 'Hello' && hostname")
print(f"Executed on: {result['assigned_to']}")

# Linux-specific tasks → macpro51
offload("make build && make test", requires_os="linux")

# Parallel execution
from cluster_offload import offload_many
results = offload_many([
    "python3 test_1.py",
    "python3 test_2.py",
    "python3 test_3.py"
])
```

**CLI Usage:**
```bash
cd ~/agentic-system/cluster-deployment
python3 distributed_task_router.py submit "echo 'Test' && hostname"
python3 distributed_task_router.py cluster-status
```

### 🧠 Cluster Memory (On macOS Nodes)

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

Each node has a specialized persona for automatic task routing:

- **🏗️ macpro51 (Builder)** - Linux x86_64
  - Compilation, testing, containerization, benchmarking
  - Capabilities: docker, podman, raid, nvme
  - Priority: 3 (preferred for heavy workloads)
  - **Status: ✅ DISTRIBUTED EXECUTION DEPLOYED**

- **🎯 mac-studio (Orchestrator)** - macOS ARM64
  - System coordination and high-level planning
  - Capabilities: orchestration, coordination, temporal
  - Priority: 1 (keep free for interactive work)
  - **Status: ✅ DISTRIBUTED EXECUTION DEPLOYED**

- **🔬 macbook-air (Researcher)** - macOS ARM64
  - Analysis, documentation, investigation
  - Capabilities: research, documentation, analysis
  - Priority: 2
  - **Status: ✅ DISTRIBUTED EXECUTION DEPLOYED**

- **💻 macbook-pro (Developer)** - macOS x86_64 (2010 model)
  - **Status: ❌ TOO OLD** (macOS 10.13.6, cannot run Claude Code)

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

### 🚀 Distributed Task Execution

| Node | Status | Test Results | Notes |
|------|--------|--------------|-------|
| macpro51 | ✅ OPERATIONAL | 7/7 passing | Linux builder, aggressive offloading working |
| mac-studio | ✅ OPERATIONAL | 7/7 passing | Orchestrator, receives offloaded tasks |
| macbook-air | ✅ OPERATIONAL | 7/7 passing | Researcher, receives offloaded tasks |
| macbook-pro | ❌ NOT SUPPORTED | - | Too old (2010 model, macOS 10.13.6) |

**Key Metrics**:
- Aggressive offloading: 100% (0 local, 10 remote tasks)
- Linux routing accuracy: 100%
- macOS routing accuracy: 100%
- Parallel execution: 5/5 tasks completed

### 🧠 Cluster Memory

| Node | Status | Persona | Deployed By |
|------|--------|---------|-------------|
| macbook-air | ✅ COMPLETE | Researcher | Researcher |
| mac-studio | ⏳ PENDING | Orchestrator | - |
| macbook-pro | ❌ NOT SUPPORTED | - | Too old |

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
