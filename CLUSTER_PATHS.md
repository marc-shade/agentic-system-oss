# Cluster File Locations - Canonical Reference

**Last Updated**: 2025-11-20
**Migration Status**: ✅ Complete

## Master Configuration

All cluster coordination files are located on **SSDRAID0** for the Mac Studio orchestrator:

```
/Volumes/SSDRAID0/agentic-system/
├── cluster-deployment/          # Cluster Python modules and scripts
│   ├── cluster-node-api.py     # Flask API (port 5100)
│   ├── cluster_config.py       # TOON config loader
│   ├── simple_cluster_config.py # JSON config loader
│   ├── cluster_memory.py       # Memory utilities
│   ├── distributed_task_router.py
│   ├── orchestrator_hive_mind.py
│   ├── orchestrator_remote_exec.py
│   ├── toon_serialization.py
│   ├── cluster-nodes.json      # Master node registry
│   └── deploy_*.sh             # Deployment scripts
│
├── databases/cluster/           # Cluster databases
│   ├── node_registry.db        # Node registration (16KB)
│   ├── node_messages.db        # Inter-node messages (28KB)
│   ├── shared_memories.db      # Shared cluster memory (80KB)
│   ├── task_queue.db           # Distributed task queue (20KB)
│   ├── comm_log.db             # Communication logs
│   ├── node_learning.db        # Learning patterns
│   └── nodes/                  # Per-node local databases
│       ├── mac-studio/
│       ├── macbook-air-m3/
│       └── macpro51/
│
├── logs/                        # Cluster logs
│   ├── cluster-node-api.log
│   ├── cluster-self-x.log
│   └── github-daemon.log
│
└── claude-flow/                 # Claude Flow cluster config
    └── cluster-config.json      # Node definitions with paths
```

## Platform-Specific Paths

### macOS Nodes (Mac Studio, MacBook Air M3)
```bash
BASE_PATH="/Volumes/SSDRAID0/agentic-system"
CLUSTER_DEPLOYMENT="$BASE_PATH/cluster-deployment"
CLUSTER_DATABASES="$BASE_PATH/databases/cluster"
CLUSTER_LOGS="$BASE_PATH/logs"
```

### Linux Nodes (MacPro51)
```bash
BASE_PATH="/mnt/agentic-system"
CLUSTER_DEPLOYMENT="$BASE_PATH/cluster-deployment"
CLUSTER_DATABASES="$BASE_PATH/databases/cluster"
CLUSTER_LOGS="$BASE_PATH/logs"
```

## Configuration Files

### 1. Claude Code Node Config
**Location**: `/Users/marc/.claude/node-config.json`
**Purpose**: Defines local node identity and paths

```json
{
  "node_id": "mac-studio",
  "storage": {
    "base": "/Volumes/SSDRAID0/agentic-system",
    "databases": "/Volumes/SSDRAID0/agentic-system/databases",
    "logs": "/Volumes/SSDRAID0/agentic-system/logs"
  },
  "memory": {
    "local_db": "/Volumes/SSDRAID0/agentic-system/databases/cluster/nodes/mac-studio/local_memory.db",
    "shared_db": "/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db",
    "node_registry": "/Volumes/SSDRAID0/agentic-system/databases/cluster/node_registry.db"
  }
}
```

### 2. Cluster Nodes Registry
**Location**: `/Volumes/SSDRAID0/agentic-system/cluster-deployment/cluster-nodes.json`
**Purpose**: Master registry of all cluster nodes

Defines 3 nodes:
- `mac-studio` (orchestrator) - `/Volumes/SSDRAID0/agentic-system`
- `macpro51` (builder) - `/mnt/agentic-system`
- `macbook-air-m3` (researcher) - `/Volumes/SSDRAID0/agentic-system`

### 3. Claude Flow Cluster Config
**Location**: `/Volumes/SSDRAID0/agentic-system/claude-flow/cluster-config.json`
**Purpose**: Claude Flow specific node configurations

## Migration Notes

**Completed**: 2025-11-20
- ✅ Migrated 43MB from `/Users/marc/agentic-system` → `/Volumes/SSDRAID0/agentic-system`
- ✅ Updated 7 code files with new paths
- ✅ Verified all 8020 files transferred
- ✅ Tested cluster services operational
- ✅ No `/Users/marc/agentic-system` references remain in code

**Old Location**: `/Users/marc/agentic-system` ❌ DO NOT USE - Safe to delete
**New Location**: `/Volumes/SSDRAID0/agentic-system` ✅ Active and operational

## Service Status

**cluster-node-api**: Running (PID 12538, port 5100)
**Databases**: All accessible and functional
**Sync Status**: Operational

## Quick Reference

```python
# Import cluster config
from cluster_deployment.simple_cluster_config import get_cluster_config, get_local_node_id

# Get local node
node_id = get_local_node_id()  # Returns: "mac-studio"

# Load configuration
config = get_cluster_config()
# Searches: /Volumes/SSDRAID0/agentic-system/cluster-deployment/cluster-nodes.json first

# Access databases
import sqlite3
conn = sqlite3.connect('/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db')
```

## See Also

- `/Users/marc/.claude/FILE_LOCATION_POLICY.md` - Overall file location policy
- `/Users/marc/.claude/DRIVE_CONFIGURATION.md` - Drive usage guidelines
- `/Users/marc/.claude/node-config.json` - This node's configuration
