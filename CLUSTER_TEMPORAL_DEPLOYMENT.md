# Cluster-Wide Temporal Deployment Plan
**Date**: 2025-11-23 22:48
**Objective**: Coordinate all nodes for distributed agentic functionality

## Current Cluster State

### mac-studio (Orchestrator) - 192.168.1.16
**Status**: ✅ Online (Current Node)
- **Temporal Server**: ✅ Running (port 7233, UI 8233)
- **Temporal Workers**: ❌ Not running (sandbox issues)
- **Storage**: /Volumes/SSDRAID0/agentic-system/
- **Workflows**: 18 available
- **Role**: Coordination, cluster memory sync, task orchestration

### macbook-air (Researcher) - 192.168.1.76
**Status**: ✅ Online
- **Temporal Server**: ✅ Running (separate instance)
- **Temporal Workers**: ❌ Not running (0 workers)
- **Storage**: ~/agentic-system/
- **Workflows**: 14 available
- **Role**: Research, analysis, overnight operations
- **Note**: Running its own Temporal server (should connect to orchestrator)

### macpro51 (Builder) - 192.168.1.183
**Status**: ✅ Online
- **Platform**: Linux (Fedora 43)
- **Temporal**: N/A (Linux - uses Builder API)
- **Builder API**: ✅ Healthy (port 9000)
- **Services**: Redis, Artifact Storage
- **Role**: Build, test, compile, containerization

### macbook-pro (Developer) - Unknown
**Status**: ❓ Not found on network
- **Action**: Need to identify or provision alternative

## Distributed Architecture Strategy

### Temporal Topology (Hub & Spoke)

```
mac-studio (Hub - Temporal Server)
    ├─ port 7233 (gRPC)
    └─ port 8233 (UI)

Workers connect to mac-studio:7233:
    ├─ mac-studio workers (orchestrator workflows)
    ├─ macbook-air workers (researcher workflows)
    └─ [future] macbook-pro workers (developer workflows)

macpro51: Standalone Builder API
    └─ Called by cluster-task-orchestration workflow
```

### Workflow Assignment by Node

**mac-studio (Priority: Coordination)**
1. `cluster-memory-sync` - Sync memories across nodes (15 min)
2. `cluster-task-orchestration` - Route tasks to optimal nodes (continuous)
3. `cluster-health-monitoring` - Monitor all nodes (5 min)
4. `system-optimization` - System-wide optimization (on-demand)
5. `memory-manager` - Memory tier management (hourly)

**macbook-air (Priority: Research & Analysis)**
1. `overnight-research` - Deep research (10PM-7AM)
2. `pattern-learning` - Extract patterns from data (daily)
3. `goal-decomposition` - Break down complex goals (on-demand)
4. `memory-consolidation` - Sleep-like consolidation (nightly)

**macbook-pro (Priority: Development - When Available)**
1. `recursive-self-improvement` - Self-improvement cycles (weekly)
2. `deep-learning-optimizer` - Code optimization (6h intervals)
3. Developer-specific workflows

**macpro51 (Priority: Build & Test - API-based)**
- Builder API receives tasks from cluster-task-orchestration
- No Temporal workers (Linux)
- HTTP endpoints for orchestrator control

## Deployment Steps

### Phase 1: Fix Workflow Issues (mac-studio)

**Issue 1: Temporal Sandbox Restrictions**
- **Problem**: `Path.resolve()` not allowed in workflows
- **Files**: memory_consolidation_workflow.py, others
- **Fix**: Move path resolution to activities or use strings

**Issue 2: Missing Functions**
- **Problem**: claude_deep_learning_optimizer.py missing functions
- **Fix**: Implement missing activities or remove from config

**Issue 3: Import Errors**
- **Status**: ✅ Fixed (get_memory_usage_patterns, get_consolidation_statistics)

### Phase 2: Configure macbook-air Workers

**Current State**: Temporal server running, but no workers

**Actions**:
1. Stop local Temporal server on macbook-air
2. Configure to connect to mac-studio:7233
3. Start researcher-specific workers
4. Test workflow execution

**Commands for macbook-air**:
```bash
# Stop local Temporal server
pkill -f "temporal server"

# Configure connection to orchestrator
export TEMPORAL_ADDRESS="192.168.1.16:7233"

# Start researcher workers
cd ~/agentic-system
nohup python3 workflows/temporal/start_researcher_workers.py > logs/temporal-workers.log 2>&1 &
```

### Phase 3: Integrate macpro51 Builder API

**Current State**: Builder API healthy and ready

**Integration Points**:
1. cluster-task-orchestration calls Builder API
2. Builder executes compile/test/build tasks
3. Results returned to orchestrator
4. Metrics logged to cluster memory

**Test Commands**:
```bash
# From mac-studio
curl http://192.168.1.183:9000/api/v1/status
curl -X POST http://192.168.1.183:9000/api/v1/build \
  -H "Content-Type: application/json" \
  -d '{"project": "test", "type": "compile"}'
```

### Phase 4: Create Node-Specific Worker Scripts

**File**: `workflows/temporal/start_orchestrator_workers.py`
```python
# For mac-studio - orchestrator workflows only
WORKFLOWS = [
    "cluster-memory-sync",
    "cluster-task-orchestration",
    "cluster-health-monitoring",
    "system-optimization",
    "memory-manager"
]
```

**File**: `workflows/temporal/start_researcher_workers.py`
```python
# For macbook-air - research workflows only
WORKFLOWS = [
    "overnight-research",
    "pattern-learning",
    "goal-decomposition",
    "memory-consolidation"
]
```

## Coordination Protocol

### 1. Cluster Memory Sync (Every 15 min)
- mac-studio collects shared memories
- Syncs to all nodes via cluster database
- macbook-air writes research findings
- macpro51 writes build results

### 2. Task Orchestration (Continuous)
- Tasks added to agent-runtime-mcp queue
- cluster-task-orchestration analyzes requirements
- Routes to optimal node:
  - Research → macbook-air
  - Build/Test → macpro51
  - Coordination → mac-studio

### 3. Health Monitoring (Every 5 min)
- Ping all nodes
- Check service health
- Update node registry
- Trigger failover if needed

## Inter-Node Communication

### Discovery
- **Avahi/mDNS**: All nodes advertise .local addresses
- **Node Registry**: SQLite database on orchestrator
- **Heartbeat**: Every 60 seconds via HTTP ping

### Data Sharing
- **Shared Memories**: SQLite at `/databases/cluster/shared_memories.db`
- **Personal Memories**: Per-node in `/databases/cluster/nodes/{node-id}/`
- **Task Queue**: agent-runtime-mcp on orchestrator

### API Endpoints
- **mac-studio**: Temporal UI (8233), Grafana (9500)
- **macpro51**: Builder API (9000), Hardware Broadcast (8888)
- **macbook-air**: TBD (researcher endpoints)

## Success Metrics

### Immediate (Phase 1-2)
- ✅ Workflows start without errors on mac-studio
- ✅ macbook-air workers connect to orchestrator
- ✅ At least 3 workflows running

### Short-term (Phase 3-4)
- ✅ Task routing to macpro51 works
- ✅ Cross-node memory sync operational
- ✅ All core workflows running

### Long-term
- ✅ Autonomous 24/7 operation
- ✅ Self-healing on failures
- ✅ Performance optimization cycles

## Next Actions

1. **Fix sandbox issues** on mac-studio workflows
2. **SSH to macbook-air** and configure workers
3. **Test Builder API** integration from orchestrator
4. **Create node-specific** worker scripts
5. **Deploy and monitor** all workflows

## Rollback Plan

If distributed deployment fails:
1. Stop all workers on all nodes
2. Run single-node mode on mac-studio
3. Debug issues in isolation
4. Re-deploy incrementally

## Monitoring

- **Temporal UI**: http://192.168.1.16:8233
- **Grafana**: http://192.168.1.16:9500
- **Logs**: `/Volumes/SSDRAID0/agentic-system/logs/temporal-*.log`
- **Health Check**: `python3 system_health_check.py`
