# Cluster Awareness API - Real-Time Environmental Data

## Two-Layer Architecture for Complete Awareness

### Layer 1: Coordination State (ClusterStateManager)
**What**: Who is doing what, task assignments, resource allocations
**Persistence**: SQLite database `cluster_state.db`
**Update frequency**: Event-driven (registrations, heartbeats, task changes)
**Use for**: Agent discovery, task routing, resource coordination

### Layer 2: Real-Time Telemetry (ClusterTelemetryCollector)
**What**: Current system metrics, process info, availability
**Persistence**: In-memory with 5-second cache
**Update frequency**: Sub-second updates, polled on demand
**Use for**: Load-based routing decisions, capacity planning, health monitoring

---

## How ANY Controller Gets Complete Awareness

### Simple API - Two Function Calls

```python
from cluster_telemetry_collector import get_cluster_awareness, get_best_execution_node
from cluster_state_manager import ClusterStateManager

# Get real-time metrics for ALL nodes
cluster_telemetry = get_cluster_awareness()

# Get coordination state for ALL agents
csm = ClusterStateManager()
cluster_state = csm.get_cluster_state()

# Now you know EVERYTHING about the cluster
```

---

## Use Case Examples

### Example 1: Claude Code Session Deciding Where to Execute

```python
# Claude Code session via MCP cluster_bash tool

from cluster_telemetry_collector import get_best_execution_node
from cluster_state_manager import ClusterStateManager

csm = ClusterStateManager()

# Register self
my_agent_id = csm.register_agent(
    node_id="macpro51",
    agent_type="claude-code-session",
    role="interactive",
    capabilities=["tool_use", "cluster_execution"],
    priority=10
)

# User: "Run pytest tests/"

# Step 1: Find best node based on REAL-TIME metrics
best_node = get_best_execution_node()

print(f"Best node: {best_node.node_id}")
print(f"  CPU: {best_node.cpu_percent:.1f}% (available: {best_node.available_cpu_percent:.1f}%)")
print(f"  Memory: {best_node.memory_percent:.1f}% (available: {best_node.available_memory_gb:.1f} GB)")
print(f"  Load: {best_node.load_1m:.2f}")

# Step 2: Create task in coordination state
task_id = csm.create_task(
    created_by_agent=my_agent_id,
    task_type="shell",
    command="pytest tests/",
    priority=7
)

# Step 3: Assign to best node
csm.assign_task(task_id, best_node.node_id, my_agent_id)

# Execute on remote node...
```

### Example 2: Background Daemon Checking Cluster Health

```python
# cluster-self-x-daemon monitoring loop

from cluster_telemetry_collector import get_cluster_awareness
from cluster_state_manager import ClusterStateManager

csm = ClusterStateManager()

# Get complete awareness
telemetry = get_cluster_awareness()
state = csm.get_cluster_state()

# Check for problems
for node_id, metrics in telemetry.items():
    if metrics.is_overloaded:
        print(f"⚠ {node_id} is overloaded!")
        print(f"  CPU: {metrics.cpu_percent:.1f}%")
        print(f"  Memory: {metrics.memory_percent:.1f}%")

        # Check what agents are running there
        agents = csm.discover_agents(node_id=node_id, status=AgentStatus.ACTIVE)
        print(f"  Active agents: {len(agents)}")

        # Check what tasks are assigned there
        tasks = csm.get_tasks(TaskStatus.RUNNING)
        node_tasks = [t for t in tasks if t.assigned_to_node == node_id]
        print(f"  Running tasks: {len(node_tasks)}")

        # Decision: Maybe move some tasks to other nodes?
```

### Example 3: Auto Task Interceptor Detecting Heavy Process

```python
# auto_task_interceptor.py monitoring local processes

from cluster_telemetry_collector import get_cluster_awareness, ClusterTelemetryCollector
from cluster_state_manager import ClusterStateManager

collector = ClusterTelemetryCollector()
csm = ClusterStateManager()

# Get LOCAL detailed telemetry
local_telemetry = collector.collect_local_telemetry()

# Check top CPU processes
for proc in local_telemetry.top_processes_cpu:
    if proc.cpu_percent > 30:
        print(f"Heavy process detected: {proc.name} (PID {proc.pid})")
        print(f"  CPU: {proc.cpu_percent:.1f}%")
        print(f"  Memory: {proc.memory_mb:.1f} MB")
        print(f"  Command: {proc.cmdline}")

        # Should we offload this?
        if "pytest" in proc.cmdline or "make" in proc.cmdline:
            # Get cluster awareness
            cluster = get_cluster_awareness()

            # Find better node
            best = None
            for node_id, metrics in cluster.items():
                if node_id != local_telemetry.node_id and metrics.can_accept_work:
                    if best is None or metrics.cpu_percent < best.cpu_percent:
                        best = metrics

            if best:
                print(f"  → Offloading to {best.node_id} (CPU: {best.cpu_percent:.1f}%)")

                # Create task
                task_id = csm.create_task(
                    created_by_agent=self.agent_id,
                    task_type="shell",
                    command=proc.cmdline,
                    priority=7
                )

                # Assign to best node
                csm.assign_task(task_id, best.node_id, self.agent_id)

                # Kill local process
                import os, signal
                os.kill(proc.pid, signal.SIGTERM)
```

### Example 4: Self-Improvement Agent Finding Capabilities

```python
# autonomous_self_improvement_agent.py analyzing cluster

from cluster_telemetry_collector import get_cluster_awareness
from cluster_state_manager import ClusterStateManager

csm = ClusterStateManager()

# Get complete cluster awareness
telemetry = get_cluster_awareness()
nodes = csm.get_nodes()

# Analyze capabilities across cluster
capabilities_by_node = {}
for node_id, metrics in telemetry.items():
    capabilities_by_node[node_id] = {
        "docker": metrics.has_docker,
        "podman": metrics.has_podman,
        "gpu": metrics.has_gpu,
        "os": metrics.os_type,
        "arch": metrics.architecture
    }

# Find gaps
# Example: Only macpro51 has docker, should we install on others?
docker_nodes = [n for n, c in capabilities_by_node.items() if c["docker"]]
non_docker_nodes = [n for n, c in capabilities_by_node.items() if not c["docker"]]

if len(non_docker_nodes) > 0:
    print(f"Gap detected: {len(non_docker_nodes)} nodes without docker")
    print(f"  With docker: {docker_nodes}")
    print(f"  Without docker: {non_docker_nodes}")

    # Use Ollama AI to decide if we should install
    decision = ollama_agent.analyze_improvement({
        "gap": "docker_missing",
        "affected_nodes": non_docker_nodes,
        "impact": "Cannot run containerized workloads on these nodes"
    })

    if decision.decision_type == "improve":
        # Install docker on non_docker_nodes
        for node_id in non_docker_nodes:
            node_telemetry = telemetry[node_id]
            if node_telemetry.os_type == "darwin":
                print(f"  → Installing Docker Desktop on {node_id}...")
                # SSH and install
```

### Example 5: MCP Server Checking Available Resources

```python
# cluster-execution-mcp server.py

from cluster_telemetry_collector import get_best_execution_node
from cluster_state_manager import ClusterStateManager

csm = ClusterStateManager()

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "cluster_bash":
        command = arguments["command"]

        # Get real-time awareness to find best node
        best_node = get_best_execution_node(
            require_os=arguments.get("requires_os"),
            require_arch=arguments.get("requires_arch")
        )

        if not best_node:
            return TextContent(
                type="text",
                text="No suitable node available for execution"
            )

        # Create and assign task
        task_id = csm.create_task(
            created_by_agent=self.agent_id,
            task_type="shell",
            command=command,
            priority=7,
            metadata={
                "requires_os": arguments.get("requires_os"),
                "requires_arch": arguments.get("requires_arch")
            }
        )

        csm.assign_task(task_id, best_node.node_id, self.agent_id)

        # Execute...
```

---

## Granular Data Structure

### NodeTelemetry - Complete Real-Time Metrics

```python
@dataclass
class NodeTelemetry:
    # Identity
    node_id: str
    hostname: str
    ip_address: str
    timestamp: float

    # CPU metrics (real-time)
    cpu_percent: float          # Current CPU usage
    cpu_count: int              # Number of cores
    cpu_freq_mhz: float         # Current frequency
    load_1m: float              # 1-minute load average
    load_5m: float              # 5-minute load average
    load_15m: float             # 15-minute load average

    # Memory metrics (real-time)
    memory_total_gb: float      # Total RAM
    memory_available_gb: float  # Available RAM
    memory_used_gb: float       # Used RAM
    memory_percent: float       # % RAM used
    swap_total_gb: float        # Total swap
    swap_used_gb: float         # Used swap
    swap_percent: float         # % swap used

    # Disk metrics
    disks: List[DiskInfo]       # All mounted disks with usage

    # Network metrics
    network_interfaces: List[NetworkInfo]  # All interfaces with traffic stats

    # Process information
    top_processes_cpu: List[ProcessInfo]     # Top 10 by CPU
    top_processes_memory: List[ProcessInfo]  # Top 10 by memory
    total_processes: int        # Total process count

    # Service status
    services: List[ServiceInfo]  # Status of key services

    # Capabilities
    os_type: str                # linux or darwin
    architecture: str           # x86_64 or arm64
    python_version: str
    has_docker: bool
    has_podman: bool
    has_gpu: bool
    gpu_info: Optional[str]

    # Availability (computed)
    available_cpu_percent: float     # 100 - cpu_percent
    available_memory_gb: float       # Free RAM
    is_overloaded: bool             # CPU > 80% or Memory > 85%
    can_accept_work: bool           # CPU < 70% and Memory < 80%
```

### All Agents Get This Information

**Before making ANY decision about cluster operations:**

```python
# Option 1: Get complete cluster telemetry
from cluster_telemetry_collector import get_cluster_awareness

telemetry = get_cluster_awareness()
# Returns: Dict[node_id -> NodeTelemetry]

# Now you know:
for node_id, metrics in telemetry.items():
    print(f"{node_id}:")
    print(f"  CPU: {metrics.cpu_percent:.1f}%")
    print(f"  Available: {metrics.available_cpu_percent:.1f}%")
    print(f"  Can accept work: {metrics.can_accept_work}")
    print(f"  OS: {metrics.os_type}")
    print(f"  Arch: {metrics.architecture}")
    print(f"  Docker: {metrics.has_docker}")
    print(f"  GPU: {metrics.has_gpu}")

    # Detailed process info
    print(f"  Top processes:")
    for proc in metrics.top_processes_cpu[:3]:
        print(f"    - {proc.name}: {proc.cpu_percent:.1f}% CPU")

# Option 2: Get best node for specific requirements
from cluster_telemetry_collector import get_best_execution_node

# Need Linux with docker
best = get_best_execution_node(
    require_os="linux",
    require_capability="docker"
)

if best:
    print(f"Best node: {best.node_id}")
    print(f"  Available CPU: {best.available_cpu_percent:.1f}%")
    print(f"  Available memory: {best.available_memory_gb:.1f} GB")
```

---

## Integration Pattern for All Controllers

**Every controller/agent should follow this pattern:**

```python
from cluster_telemetry_collector import ClusterTelemetryCollector, get_cluster_awareness
from cluster_state_manager import ClusterStateManager, AgentStatus

class MyController:
    def __init__(self):
        # Coordination state
        self.csm = ClusterStateManager()

        # Real-time telemetry
        self.telemetry_collector = ClusterTelemetryCollector()

        # Register self as agent
        self.agent_id = self.csm.register_agent(
            node_id=self.node_id,
            agent_type="my-controller",
            role="my_role",
            capabilities=["my", "capabilities"],
            priority=7
        )

    def make_decision(self):
        # Step 1: Get real-time environmental awareness
        telemetry = get_cluster_awareness()

        # Step 2: Get coordination state
        state = self.csm.get_cluster_state()
        agents = self.csm.discover_agents(capability="needed_capability")

        # Step 3: Make informed decision
        # You now know:
        # - Real-time metrics for all nodes
        # - What agents are running where
        # - What tasks are pending/running
        # - What resources are allocated

        # Step 4: Take action
        if decision_to_create_task:
            best_node = get_best_execution_node()
            task_id = self.csm.create_task(...)
            self.csm.assign_task(task_id, best_node.node_id, self.agent_id)

    def heartbeat_loop(self):
        while self.running:
            # Send heartbeat to stay registered
            self.csm.agent_heartbeat(self.agent_id, AgentStatus.ACTIVE)
            time.sleep(30)
```

---

## Performance Characteristics

### ClusterTelemetryCollector Caching

- **Local telemetry**: Cached for 5 seconds
- **Remote telemetry**: Cached for 5 seconds per node
- **First call**: ~0.5-1 second (collects full metrics)
- **Cached calls**: < 1ms (returns cached data)

### Best Practices

1. **Cache cluster awareness**: Don't call `get_cluster_awareness()` in tight loops
   ```python
   # Good
   telemetry = get_cluster_awareness()  # Cache for 5 seconds
   for task in tasks:
       # Use cached telemetry
       decide_routing(task, telemetry)

   # Bad
   for task in tasks:
       telemetry = get_cluster_awareness()  # Re-fetches every time!
       decide_routing(task, telemetry)
   ```

2. **Use convenience functions**: They handle caching automatically
   ```python
   # Simple - just get best node
   best = get_best_execution_node()

   # Detailed - get full awareness if you need it
   telemetry = get_cluster_awareness()
   ```

3. **Heartbeat regularly**: Keep your agent registration alive
   ```python
   # Every 30 seconds
   csm.agent_heartbeat(agent_id, AgentStatus.ACTIVE)
   ```

---

## Summary

**Every controller in the cluster now has two APIs:**

1. **`ClusterStateManager`** - Who, what, where (coordination)
2. **`ClusterTelemetryCollector`** - Current metrics, availability (real-time)

**Any agent can call these to get complete environmental awareness of the entire cluster in real-time.**

No more blind decisions. Every controller knows:
- ✅ What nodes exist and their capabilities
- ✅ Current load on every node (CPU, memory, processes)
- ✅ What agents are running where
- ✅ What tasks are pending/running
- ✅ Resource availability
- ✅ Service health
- ✅ Who can do what

**Complete cluster self-awareness for autonomous decision making.**
