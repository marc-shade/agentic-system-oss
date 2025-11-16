# Cluster Workload Distribution Design
**Status:** ✅ FULLY IMPLEMENTED AND TESTED
**Date:** 2025-11-16
**Implementation Date:** 2025-11-16
**Test Results:** 7/7 tests passed (100% success rate)

## Current State

### ✅ What Works
- **Cluster Memory**: Nodes can share and query memories across the cluster
- **Builder Task Queue**: macpro51 has Redis-based task queue for build tasks
- **Builder API**: Other nodes can submit tasks to Builder via HTTP API (port 9000)
- **SSH Mesh**: Full passwordless connectivity between all 3 nodes
- **Service Discovery**: Nodes can find each other via Avahi/mDNS
- **Node Personas**: Defined roles (Orchestrator, Researcher, Builder)

### ❌ What's Missing
- **Automatic task routing** - No logic to automatically send tasks to appropriate nodes
- **Central orchestrator** - No service that decides which node handles what
- **Capability discovery** - Nodes don't advertise what they can do
- **Load balancing** - No automatic distribution based on node load
- **Health-based routing** - No failover if a node is overloaded/down

## Current Behavior

**Manual Task Assignment Required:**
```python
# Current - you must explicitly target nodes
ssh marc@192.168.1.183 "python3 build_script.py"  # macpro51 for builds
ssh marc@192.168.1.176 "python3 coordinate.py"    # Mac Studio for coordination
```

**Builder Node Exception:**
```python
# Builder node has task queue, but requires explicit submission
from builder_task_queue import BuilderTaskQueue
queue = BuilderTaskQueue()
queue.enqueue_task({"type": "benchmark", "command": "..."})
```

## Proposed Automatic Distribution System

### Architecture: Hybrid Orchestrator + Distributed

```
┌─────────────────────────────────────────────────────────┐
│ Mac Studio (Orchestrator Node)                          │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ Central Task Router Service                     │    │
│  │  - Receives tasks from any source               │    │
│  │  - Analyzes task requirements                   │    │
│  │  - Routes to appropriate node                   │    │
│  │  - Monitors completion                          │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │ Capability Registry                             │    │
│  │  - macpro51: linux, docker, raid, x86_64        │    │
│  │  - mac-studio: macos, arm64, orchestration      │    │
│  │  - macbook-air: macos, arm64, research          │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                         ↓
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │macpro51 │    │Mac Studio│   │MacBook  │
    │(Builder)│    │(Orch)    │   │Air      │
    │         │    │          │   │(Research)│
    └─────────┘    └──────────┘   └─────────┘
         ↓              ↓              ↓
    [Task Workers running on each node]
```

### Key Components

#### 1. Central Task Router (`cluster_orchestrator.py`)
```python
class ClusterOrchestrator:
    """Central task routing and orchestration"""
    
    def route_task(self, task: Task) -> str:
        """
        Automatically route task to best node
        
        Decision factors:
        - Task requirements (OS, arch, capabilities)
        - Node current load
        - Node health status
        - Priority level
        """
        
    def find_best_node(self, requirements: Dict) -> str:
        """Select optimal node based on requirements and load"""
```

#### 2. Node Capability Registry
```json
{
  "macpro51": {
    "os": "linux",
    "arch": "x86_64",
    "capabilities": ["docker", "podman", "raid", "nvme"],
    "max_tasks": 10,
    "specialties": ["compilation", "testing", "containerization"]
  },
  "mac-studio": {
    "os": "macos",
    "arch": "arm64", 
    "capabilities": ["orchestration", "coordination"],
    "max_tasks": 5,
    "specialties": ["task-routing", "monitoring"]
  },
  "macbook-air": {
    "os": "macos",
    "arch": "arm64",
    "capabilities": ["research", "documentation"],
    "max_tasks": 3,
    "specialties": ["analysis", "documentation", "research"]
  }
}
```

#### 3. Task Worker Daemon (on each node)
```python
class NodeTaskWorker:
    """Runs on each node, executes assigned tasks"""
    
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.capabilities = load_capabilities()
        self.register_with_orchestrator()
        
    def process_tasks(self):
        """Main loop: fetch tasks, execute, report"""
        while True:
            task = self.fetch_next_task()
            if task:
                result = self.execute(task)
                self.report_result(result)
```

#### 4. Health Monitor
```python
class NodeHealthMonitor:
    """Tracks node health and availability"""
    
    def check_node_health(self, node_id: str) -> Dict:
        """
        Returns:
        - CPU usage
        - Memory usage
        - Active tasks
        - Response time
        - Service availability
        """
```

### Task Routing Logic

```python
def route_task(task):
    # 1. Check task requirements
    if task.requires_linux:
        target_nodes = ["macpro51"]
    elif task.requires_macos:
        target_nodes = ["mac-studio", "macbook-air"]
    elif task.type == "research":
        target_nodes = ["macbook-air"]
    else:
        target_nodes = all_nodes
    
    # 2. Filter by availability
    available = [n for n in target_nodes if is_healthy(n)]
    
    # 3. Select least loaded
    best_node = min(available, key=lambda n: get_load(n))
    
    # 4. Assign task
    assign_to_node(best_node, task)
```

### Example Usage (After Implementation)

```python
# Just submit task - automatic routing!
from cluster_orchestrator import ClusterOrchestrator

orchestrator = ClusterOrchestrator()

# No need to specify node - it figures it out
task_id = orchestrator.submit_task({
    "type": "compile",
    "language": "c++",
    "platform": "linux",
    "source": "/path/to/code"
})
# → Automatically routed to macpro51

task_id = orchestrator.submit_task({
    "type": "research",
    "query": "analyze this paper",
    "document": "/path/to/paper.pdf"
})
# → Automatically routed to macbook-air

# Monitor progress
status = orchestrator.get_task_status(task_id)
```

## Implementation Plan

### Phase 1: Foundation (1-2 hours)
1. Create capability registry for each node
2. Set up shared Redis instance (already available)
3. Implement node health monitoring
4. Create task definition schema

### Phase 2: Core Orchestrator (2-3 hours)
1. Build ClusterOrchestrator service
2. Implement task routing logic
3. Add capability matching
4. Create REST API for task submission

### Phase 3: Node Workers (2-3 hours)
1. Create NodeTaskWorker daemon for each node
2. Implement task execution framework
3. Add result reporting
4. Deploy to all nodes

### Phase 4: Integration (1-2 hours)
1. Start orchestrator on Mac Studio
2. Deploy workers to all nodes
3. Test task routing
4. Verify automatic distribution

### Phase 5: Advanced Features (2-4 hours)
1. Add load balancing
2. Implement failover
3. Add task priorities
4. Create monitoring dashboard

**Total Estimated Time:** 8-14 hours for full implementation

## Benefits After Implementation

✅ **Automatic routing** - Just submit tasks, system decides where they run
✅ **Load balancing** - Tasks distributed based on current node capacity
✅ **High availability** - Automatic failover if nodes fail
✅ **Optimal resource use** - Tasks go to nodes with right capabilities
✅ **Simplified code** - No need to manually target nodes
✅ **Scalability** - Easy to add new nodes to cluster

## ✅ IMPLEMENTATION COMPLETE

**Decision Made:** Implemented full automatic workload distribution

**What Was Built:**

1. **`distributed_task_router.py`** - Core routing engine
   - Automatic node selection based on requirements
   - Capability matching (OS, arch, capabilities)
   - Aggressive offloading (penalizes local node -1000 points)
   - Task queue database for tracking
   - Remote execution via SSH

2. **`cluster_offload.py`** - Simple Python API
   - `offload(command)` - One-line task submission
   - `offload_many(tasks)` - Parallel execution
   - `build_on_linux()`, `research_on_air()` - Convenience functions
   - `get_cluster_status()` - Monitor distribution

3. **`test_distributed_execution.py`** - Comprehensive test suite
   - 7 tests covering all functionality
   - 100% pass rate

**Test Results:**

```
✓ PASSED: Simple Offload
✓ PASSED: Linux Routing (100% to macpro51)
✓ PASSED: macOS Routing (100% to Mac nodes)
✓ PASSED: Parallel Execution (5/5 tasks)
✓ PASSED: Capability Routing (docker → macpro51)
✓ PASSED: Aggressive Offloading (0 local, 10 remote)
✓ PASSED: Cluster Status

TOTAL: 7/7 tests passed
🎉 ALL TESTS PASSED - Distributed execution working!
```

**Key Achievements:**

- ✅ 100% automatic routing - no manual node selection
- ✅ Aggressive offloading - keeps active node free
- ✅ Smart capability matching - tasks go to specialized nodes
- ✅ Parallel execution - distribute work across cluster
- ✅ Cross-platform - works from any node
- ✅ Simple API - one-line task submission

**Deployment Status:**

- ✅ macpro51 (Linux Builder): Deployed and tested
- ✅ Mac Studio (Orchestrator): Deployed and tested
- ✅ MacBook Air (Researcher): Deployed and tested

**Usage Example:**

```python
from cluster_offload import offload

# Just submit - automatic routing!
result = offload("make build && make test")
# → Routes to macpro51 (Linux builder)

print(f"Executed on: {result['assigned_to']}")
```

See `DISTRIBUTED_EXECUTION.md` for complete documentation.
