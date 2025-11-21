# MacBook Air M3 - Hive Mind Integration Setup Instructions

## Quick Start

On the MacBook Air M3, run:

```bash
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment
./setup_macbook_air_hive_mind.sh
```

**OR** if the shared drive is not accessible:

```bash
# On mac-studio, copy the package
scp macbook-air-hive-mind-package.tar.gz marc@192.168.1.76:~/

# On macbook-air, extract and run
cd ~
tar -xzf macbook-air-hive-mind-package.tar.gz
./setup_macbook_air_hive_mind.sh
```

## What Gets Installed

### 1. Directory Structure
```
~/agentic-system/
├── cluster-deployment/
│   ├── researcher_hive_mind.py       (Main API)
│   ├── orchestrator_hive_mind.py     (Core module)
│   ├── distributed_task_router.py    (Task routing)
│   ├── toon_serialization.py         (Token optimization)
│   └── cluster_memory.py             (Memory management)
├── databases/cluster/
│   ├── node_messages.db              (Message queue)
│   ├── shared_memories.db            (Shared knowledge)
│   └── node_registry.db              (Node registry)
└── logs/
```

### 2. Configuration
```
~/.claude/macbook-air-node-config.json
```

Contains node-specific settings:
- Node ID: macbook-air-m3
- Role: researcher
- Capabilities
- Storage paths
- Cluster connection info

### 3. Documentation
```
~/agentic-system/RESEARCHER_HIVE_MIND.md
```

Quick reference for using the hive mind API.

## Verification

After running setup, test the integration:

```bash
cd ~/agentic-system/cluster-deployment
python3 researcher_hive_mind.py
```

You should see:
- Node ID and role
- Sync status with cluster
- Recent messages (if any)
- Shared memories (if any)

## Using in Claude Code

### Import and Initialize

```python
from cluster_deployment.researcher_hive_mind import hive

# Check status
status = hive.get_sync_status()
print(status)
```

### Send Messages

```python
# Send to orchestrator
hive.send_message(
    "mac-studio",
    "Research completed on distributed systems optimization",
    subject="Research Update"
)

# Messages are queued locally and will sync to cluster
```

### Store Research Findings

```python
# Store in shared cluster memory
hive.store_shared_memory(
    name="distributed_optimization_research_2025_11_20",
    observations=[
        "Token reduction through code execution: 98.7%",
        "Parallel tool execution: 10x speedup",
        "TOON format: 50% token savings"
    ],
    entity_type="research_finding"
)
```

### Query Cluster Knowledge

```python
# Search shared memories
results = hive.query_shared_memory("optimization")

for mem in results:
    print(f"{mem['name']} ({mem['source_node']})")
    print(f"  {mem['observations']}")
```

### Check Messages

```python
# Get recent messages
messages = hive.get_recent_messages(10)

for msg in messages:
    print(f"[{msg['from']}] {msg['subject']}")
    if msg['body']:
        print(f"  {msg['body']}")
```

## Cluster Nodes

You can communicate with:

1. **mac-studio** (orchestrator)
   - Role: Orchestration, coordination
   - IP: 192.168.1.16
   - Capabilities: heavy-processing, MLX GPU, temporal workflows

2. **completeu-server** (inference)
   - Role: Model inference
   - IP: 192.168.1.186
   - Capabilities: Ollama, model serving, API endpoints

3. **macpro51** (linux-worker)
   - Role: Building, compilation
   - IP: 192.168.1.183
   - Capabilities: Linux operations, x86 tasks, containerization

4. **macbook-air-m3** (researcher - YOU!)
   - Role: Research, documentation
   - IP: 192.168.1.76
   - Capabilities: Research, analysis, lightweight processing

## Database Sync

The researcher node maintains local copies of cluster databases.

### Auto-Sync (Recommended)

Databases sync automatically via:
- GitHub-based message queue (cross-network)
- Direct TCP for low-latency (local network)

### Manual Sync

If needed, you can manually sync:

```bash
# Copy latest shared memories from orchestrator
scp marc@192.168.1.16:/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db \
    ~/agentic-system/databases/cluster/

# Or use rsync for incremental updates
rsync -avz marc@192.168.1.16:/Volumes/SSDRAID0/agentic-system/databases/cluster/ \
          ~/agentic-system/databases/cluster/
```

## Troubleshooting

### Database Lock Errors

If you get "database is locked" errors:

```bash
# Close any open connections
pkill -f researcher_hive_mind

# Wait a moment and retry
sleep 2
python3 researcher_hive_mind.py
```

### Connection Errors

If you can't reach other nodes:

1. Check network connectivity:
   ```bash
   ping 192.168.1.16  # orchestrator
   ```

2. Verify SSH access:
   ```bash
   ssh marc@192.168.1.16 "echo OK"
   ```

3. Check if node is registered:
   ```python
   from cluster_deployment.researcher_hive_mind import hive
   status = hive.get_sync_status()
   ```

### Missing Dependencies

If imports fail:

```bash
# Ensure Python 3 is installed
python3 --version

# Check required modules
python3 -c "import sqlite3, json, uuid; print('OK')"
```

## Advanced Usage

### Custom Message Types

```python
# Research query
hive.send_message(
    "mac-studio",
    "Need access to MLX GPU for model testing",
    subject="Resource Request",
    message_type="query",
    priority=7
)

# Task completion
hive.send_message(
    "mac-studio",
    "Document analysis complete. 47 papers processed.",
    subject="Task Complete",
    message_type="notification"
)
```

### Research Workflow Example

```python
from cluster_deployment.researcher_hive_mind import hive

# 1. Check cluster knowledge before starting
existing = hive.query_shared_memory("distributed systems")

# 2. Do research work
# ... your research code ...

# 3. Store findings
hive.store_shared_memory(
    f"research_{topic}_{date}",
    findings_list,
    entity_type="research_finding"
)

# 4. Notify orchestrator
hive.send_message(
    "mac-studio",
    f"Research on {topic} complete. Findings stored in shared memory.",
    subject=f"Research Complete: {topic}"
)
```

## Integration with Claude Code

Add to your Claude Code workspace:

```python
# In .claude/commands/research.md
from cluster_deployment.researcher_hive_mind import hive

# Your research command logic here
# Auto-store findings in cluster memory
```

## Next Steps

1. ✅ Complete setup
2. Test communication with orchestrator
3. Store your first research finding
4. Query cluster knowledge base
5. Participate in distributed research tasks

## Support

For issues or questions:
- Check orchestrator logs: `~/agentic-system/logs/`
- View recent messages: `hive.get_recent_messages()`
- Contact orchestrator: Send message to "mac-studio"

---

**Status:** Ready for deployment
**Last Updated:** 2025-11-20
**Package:** macbook-air-hive-mind-package.tar.gz (16KB)
