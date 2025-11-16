# Single Source of Truth - Cluster State Manager

## Problem We Solved

Previously, cluster state was fragmented across:
- `node_registry.db` - Node tracking
- `agent_registry.db` - Agent discovery
- `shared_memories.db` - Cluster memories
- `agent_runtime.db` - Task management
- SQLite task queue in `distributed_task_router.py`

**This caused**:
- Sync issues between databases
- Inconsistent state
- Complex coordination
- Race conditions
- No single view of cluster truth

## Solution: Cluster State Manager

**ONE database** - `cluster_state.db` - contains ALL cluster coordination state:

```
cluster_state.db
├── nodes           # All cluster hardware
├── agents          # All running processes
├── tasks           # All work units
├── resources       # All allocations
└── event_log       # All cluster events
```

## Who Uses It

**Everything** queries ClusterStateManager for truth:

### Background System Agents
- ✅ `cluster-self-x-daemon.py` - Register as orchestrator agent
- ✅ `performance_optimizer.py` - Update node metrics, create tasks
- ✅ `auto_task_interceptor.py` - Discover nodes, submit tasks
- ✅ `autonomous_self_improvement_agent.py` - Discover agents, coordinate
- ✅ `ollama_persistent_agent.py` - Query cluster state for decisions

### Interactive Sessions
- ✅ Claude Code sessions - Register as agent, submit tasks via MCP
- ✅ MCP servers - Query state, coordinate resources
- ✅ Intelligent agents - Discover other agents, coordinate

### Infrastructure
- ✅ `distributed_task_router.py` - Use ClusterStateManager for task queue
- ✅ Node discovery - All nodes register on boot
- ✅ Resource allocation - CPU, memory, ports tracked centrally

## API Examples

### Register a Node
```python
from cluster_state_manager import ClusterStateManager, NodeStatus

csm = ClusterStateManager()

csm.register_node(
    node_id="macpro51",
    hostname="macpro51",
    ip_address="192.168.1.154",
    os_type="linux",
    architecture="x86_64",
    role="builder",
    capabilities=["docker", "podman", "build"]
)
```

### Register an Agent
```python
agent_id = csm.register_agent(
    node_id="macpro51",
    agent_type="claude-code-session",
    role="interactive",
    capabilities=["tool_use", "file_edit", "cluster_execution"],
    priority=10  # Highest - user-facing
)

# Send heartbeats to stay alive
csm.agent_heartbeat(agent_id, AgentStatus.ACTIVE)
```

### Create and Assign a Task
```python
# Create task
task_id = csm.create_task(
    created_by_agent=agent_id,
    task_type="shell",
    command="pytest tests/",
    priority=7
)

# Assign to best node
nodes = csm.get_nodes(status=NodeStatus.ONLINE)
best_node = min(nodes, key=lambda n: n.cpu_percent)

csm.assign_task(task_id, best_node.node_id, agent_id)
```

### Discover Other Agents
```python
# Find all code protector agents
protectors = csm.discover_agents(
    agent_type="code-evolution-protector",
    status=AgentStatus.ACTIVE
)

# Find agents with specific capability
cluster_aware = csm.discover_agents(
    capability="cluster_execution"
)

# Find agents on specific node
local_agents = csm.discover_agents(node_id="macpro51")
```

### Query Cluster State
```python
# Get complete snapshot
state = csm.get_cluster_state()
# {
#   "nodes": 3,
#   "agents": 12,
#   "tasks_pending": 5,
#   "tasks_running": 3,
#   "timestamp": 1700000000.0
# }

# Get all online nodes
online_nodes = csm.get_nodes(status=NodeStatus.ONLINE)

# Get pending tasks
pending = csm.get_tasks(TaskStatus.PENDING)
```

## Migration from Old Systems

### Step 1: Update cluster-self-x-daemon.py
```python
from cluster_state_manager import ClusterStateManager, AgentStatus

class ClusterSelfXDaemon:
    def __init__(self):
        self.csm = ClusterStateManager()
        self.agent_id = None

    def start(self):
        # Register as orchestrator
        self.agent_id = self.csm.register_agent(
            node_id=self.local_node_id,
            agent_type="cluster-orchestrator",
            role="coordination",
            capabilities=["self_improvement", "optimization", "discovery"],
            priority=8
        )

    def _heartbeat_loop(self):
        while self.running:
            self.csm.agent_heartbeat(self.agent_id, AgentStatus.ACTIVE)
            time.sleep(30)
```

### Step 2: Update distributed_task_router.py
```python
class DistributedTaskRouter:
    def __init__(self):
        self.csm = ClusterStateManager()

    def submit_task(self, task_def):
        # Create task in central state
        task_id = self.csm.create_task(
            created_by_agent=self.agent_id,
            task_type=task_def["type"],
            command=task_def["command"],
            priority=task_def.get("priority", 5)
        )

        # Route to best node
        node = self._select_best_node(task_def)
        self.csm.assign_task(task_id, node.node_id, self.agent_id)

        return task_id
```

### Step 3: Update MCP servers
```python
class ClusterExecutionServer:
    def __init__(self):
        self.csm = ClusterStateManager()

        # Register as MCP server agent
        self.agent_id = self.csm.register_agent(
            node_id=self.local_node_id,
            agent_type="mcp-server",
            role="tool_serving",
            capabilities=["cluster_bash", "cluster_status"],
            priority=8
        )

    def execute_cluster_bash(self, command: str):
        # Create task via central state
        task_id = self.csm.create_task(
            created_by_agent=self.agent_id,
            task_type="shell",
            command=command,
            priority=7
        )

        # Route and execute...
```

## Benefits

✅ **Single source of truth** - No more sync issues
✅ **Consistent state** - Everyone sees the same reality
✅ **Simple coordination** - One API for everything
✅ **Complete visibility** - See entire cluster at once
✅ **Event history** - Full audit log of cluster events
✅ **Resource tracking** - Know what's allocated where
✅ **Agent discovery** - Find who can do what
✅ **Task management** - Unified task queue
✅ **Real-time metrics** - Current load on all nodes
✅ **Scalable** - Add nodes/agents without complexity

## Deprecations

These are NO LONGER USED:
- ❌ `node_registry.db` → Use `nodes` table in cluster_state.db
- ❌ `agent_registry.db` → Use `agents` table in cluster_state.db
- ❌ SQLite task queue in router → Use `tasks` table in cluster_state.db
- ❌ Separate resource tracking → Use `resources` table in cluster_state.db

## Rollout Plan

1. ✅ Create `cluster_state_manager.py` - DONE
2. ⏳ Update `cluster-self-x-daemon.py` to register agents
3. ⏳ Update `distributed_task_router.py` to use central task queue
4. ⏳ Update MCP servers to register and use cluster state
5. ⏳ Update intelligent agents to discover via cluster state
6. ⏳ Deploy to all nodes
7. ⏳ Remove old database files after migration

## Database Location

**The Truth**: `/home/marc/agentic-system/databases/cluster/cluster_state.db`

- macpro51 (Linux): `/home/marc/agentic-system/databases/cluster/cluster_state.db`
- mac-studio (macOS): `/Users/marc/agentic-system/databases/cluster/cluster_state.db`
- macbook-air (macOS): `/Users/marc/agentic-system/databases/cluster/cluster_state.db`

All nodes sync via shared network filesystem (SMB/Avahi).

---

**Everything queries THIS for truth. No exceptions.**
