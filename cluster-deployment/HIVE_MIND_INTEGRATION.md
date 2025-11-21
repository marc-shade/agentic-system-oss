# Hive Mind Integration - Quick Reference

## Overview

The orchestrator (mac-studio/Claude) is now fully integrated into the cluster hive mind with complete bidirectional communication capabilities.

## Python API

```python
from cluster_deployment.orchestrator_hive_mind import HiveMind

hive = HiveMind()
```

## Core Capabilities

### 1. Cluster Status

```python
# Get status of all nodes
status = hive.get_cluster_status()
# Returns: total_nodes, orchestrator, nodes[], timestamp
```

**Current Cluster:**
- **mac-studio** (orchestrator) - M2 Max, 8TB RAID0, coordination/MLX GPU
- **completeu-server** (inference) - M2 Ultra, Ollama inference, API endpoints
- **macpro51** (linux-worker) - Intel Xeon, Linux/x86, containerization, building
- **macbook-air-m3** (researcher) - M3, research, lightweight processing

### 2. Send Messages

```python
# Send to specific node
msg_id = hive.send_message(
    to_node="macpro51",
    message="Your message here",
    subject="Optional subject",
    priority=5,  # 1-10, higher = more urgent
    message_type="notification"  # or "query", "command", "broadcast"
)

# Broadcast to all nodes
msg_ids = hive.broadcast_message(
    message="Broadcast message",
    subject="Cluster Update",
    priority=7
)
```

### 3. Execute Remote Commands

```python
# Execute command on remote node
result = hive.execute_remote(
    node_id="macpro51",
    command="hostname",
    timeout=10
)
# Returns: dict with status, stdout, stderr, etc.
```

### 4. Shared Cluster Memory

```python
# Store shared memory (accessible to all nodes)
hive.store_shared_memory(
    name="optimization_pattern",
    observations="Use TOON format for 50% token reduction",
    entity_type="knowledge"
)

# Query shared memory
memories = hive.query_shared_memory(
    query="optimization",
    limit=10
)
# Returns: list of dicts with name, type, observations, source_node, created_at
```

### 5. Check Recent Messages

```python
# Get recent messages received
messages = hive.get_recent_messages(limit=10)
# Returns: list of dicts with message_id, from, subject, body, type, priority
```

## Communication Channels

The cluster uses three communication methods:

1. **Database Queue** (`node_messages.db`) - Local message passing
2. **GitHub MCP** - Cross-network communication via GitHub repo
3. **Direct TCP** (port 9999) - Low-latency command execution

## Active Daemons

Running cluster daemons on mac-studio:
- `github_node_daemon.py` - GitHub-based cross-network messaging
- `cluster-node-api.py` - REST API for cluster operations
- `cluster_self_x_daemon.py` - Self-management daemon

Remote nodes have:
- `node_command_listener.py` - Listens on port 9999 for commands

## Storage Paths

```python
/Volumes/SSDRAID0/agentic-system/databases/cluster/
├── node_messages.db      # Message queue
├── node_registry.db      # Node registry
├── shared_memories.db    # Cluster-wide memory
└── comm_status.json      # Communication stats
```

## Example Workflows

### Delegate Task to Builder Node

```python
# Send build task to macpro51
result = hive.execute_remote(
    "macpro51",
    "cd /mnt/agentic-system && ./build_script.sh"
)
```

### Share Learning Across Cluster

```python
# Store optimization discovery
hive.store_shared_memory(
    "code_execution_pattern",
    ["Use execute_code for 98.7% token reduction",
     "Batch operations instead of individual tool calls"],
    entity_type="optimization"
)

# Other nodes can query this later
patterns = hive.query_shared_memory("token reduction")
```

### Coordinate Multi-Node Operation

```python
# Broadcast coordination message
hive.broadcast_message(
    "Starting distributed analysis task. Stand by for work assignments.",
    subject="Distributed Task Starting",
    priority=8
)

# Assign work to each node
hive.execute_remote("macpro51", "analyze_dataset.py --shard=1")
hive.execute_remote("completeu-server", "analyze_dataset.py --shard=2")
hive.execute_remote("macbook-air-m3", "analyze_dataset.py --shard=3")
```

## Integration Status

✅ Orchestrator hive mind integration complete
✅ Bidirectional communication tested
✅ Shared memory operational
✅ Broadcast messaging working
✅ Remote command execution verified

**Last Updated:** 2025-11-20 13:30:00
**Status:** Production Ready
