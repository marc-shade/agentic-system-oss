# Complete Cluster Status & Coordination Plan
**Updated**: 2025-11-23 22:52
**Active Nodes**: 4 (all operational)

## Active Cluster Nodes

### 1. mac-studio (Orchestrator) - 192.168.1.16
**Role**: Primary orchestrator and coordination
**Platform**: macOS (Apple Silicon)
**Status**: ✅ Online (Current Node)

**Services**:
- ✅ Temporal Server (port 7233, UI 8233)
- ❌ Temporal Workers (0 running - sandbox issues)
- ✅ Grafana (port 9500)
- ✅ Prometheus (port 9700)
- ✅ Loki (port 9900)

**Storage**: /Volumes/SSDRAID0/agentic-system/
**Workflows**: 18 available
**Priority**: 1 (highest)

**Assigned Workflows**:
1. cluster-memory-sync (every 15 min)
2. cluster-task-orchestration (continuous)
3. cluster-health-monitoring (every 5 min)
4. system-optimization (on-demand)
5. memory-manager (hourly)

---

### 2. macbook-air (Researcher) - 192.168.1.76
**Role**: Research, analysis, documentation
**Platform**: macOS (Apple M3)
**Status**: ✅ Online

**Services**:
- ✅ Temporal Server (port 7233) - *Should stop and use orchestrator*
- ❌ Temporal Workers (0 running)

**Storage**: ~/agentic-system/
**Workflows**: 14 available
**Priority**: 4 (mobile/lightweight)

**Assigned Workflows**:
1. overnight-research (10PM-7AM)
2. pattern-learning (daily)
3. goal-decomposition (on-demand)
4. memory-consolidation (nightly)

**Notes**:
- Mobile researcher (MacBook Air M3)
- Can use remote Ollama from completeu-server or macpro51
- Should connect to mac-studio Temporal, not run own server

---

### 3. completeu-server (AI Inference) - 192.168.1.186
**Role**: AI model inference and LLM operations
**Platform**: macOS
**Status**: ✅ Online - **NEWLY DISCOVERED**

**Services**:
- ✅ Temporal Server (port 7233) - *Should stop and use orchestrator*
- ✅ Ollama (port 11434) - **23 models loaded**
- ❌ Temporal Workers (0 running)
- ✅ temporalio SDK installed

**Storage**: ~/agentic-system/ (on /Volumes/FILES)
**Workflows**: 0 (need deployment)
**Priority**: 2 (inference specialist)

**Assigned Workflows**:
1. deep-learning-optimizer (inference optimization)
2. recursive-self-improvement (model selection)
3. AI model routing and selection
4. Inference-heavy research tasks

**Notes**:
- Primary Ollama server for cluster
- All nodes can use http://completeu-server.local:11434
- Workflows need to be deployed from orchestrator

---

### 4. macpro51 (Builder) - 192.168.1.183
**Role**: Build, test, compile, containerization
**Platform**: Linux (Fedora 43)
**Status**: ✅ Online

**Services**:
- ✅ Builder API (port 9000) - Healthy
- ✅ Redis (port 6379)
- ✅ Artifact Storage
- ✅ Hardware Broadcast (port 8888)
- ✅ Ollama (port 11434) - Linux models
- N/A Temporal (Linux - API-based coordination)

**Hardware**:
- Dual Intel Xeon X5680 (24 threads @ 3.33 GHz)
- 126 GB RAM
- 930 GB NVMe RAID10

**Storage**: /home/marc/agentic-system/
**Priority**: 3 (build specialist)

**Assigned Tasks** (via Builder API):
1. Compilation and builds
2. Test execution
3. Container operations (Docker/Podman)
4. Performance benchmarking
5. Linux-specific workflows

**Notes**:
- Does NOT run Temporal (Linux - uses Builder API)
- Receives tasks from cluster-task-orchestration
- Dual network interfaces (.87 and .183)

---

## Cluster Architecture

### Temporal Topology (Unified)

```
mac-studio (Primary Temporal Server)
    ├─ port 7233 (gRPC endpoint)
    └─ port 8233 (Web UI)

All worker connections to mac-studio:7233:
    ├─ mac-studio workers → orchestrator workflows
    ├─ macbook-air workers → researcher workflows
    ├─ completeu-server workers → AI inference workflows
    └─ macpro51 → Builder API (no Temporal)

Inference Services (Distributed):
    ├─ completeu-server:11434 → Primary Ollama (23 models)
    └─ macpro51:11434 → Linux Ollama
```

### Network Map

```
192.168.1.1 (Router)
    ├─ 192.168.1.16 → mac-studio [orchestrator]
    ├─ 192.168.1.76 → macbook-air [researcher]
    ├─ 192.168.1.186 → completeu-server [AI inference]
    └─ 192.168.1.183 → macpro51 [builder]
```

### Data Flow

```
Cluster Memory:
    ├─ Shared DB: mac-studio:/databases/cluster/shared_memories.db
    ├─ Node-specific DBs: /databases/cluster/nodes/{node-id}/
    └─ Sync: cluster-memory-sync workflow (every 15 min)

Task Queue:
    ├─ agent-runtime-mcp on mac-studio
    ├─ cluster-task-orchestration routes to nodes
    └─ macpro51 receives via Builder API

AI Inference:
    ├─ completeu-server primary (23 Ollama models)
    ├─ All nodes can call completeu-server:11434
    └─ Fallback to macpro51:11434 for Linux models
```

## Deployment Strategy

### Phase 1: Centralize Temporal Server ✅ READY
**Action**: Stop Temporal servers on macbook-air and completeu-server, use mac-studio as hub

**macbook-air**:
```bash
ssh marc@192.168.1.76 "pkill -f 'temporal server'"
```

**completeu-server**:
```bash
ssh marc@192.168.1.186 "pkill -f 'temporal server'"
```

### Phase 2: Fix mac-studio Workflows ⚠️ IN PROGRESS
**Issues**:
1. ✅ Import errors fixed
2. ❌ Temporal sandbox restrictions (Path.resolve())
3. ❌ Missing functions in claude_deep_learning_optimizer

**Action**: Refactor workflows to be sandbox-safe

### Phase 3: Deploy Workflows to All Nodes 📋 PLANNED

**completeu-server** (needs workflows):
```bash
# From mac-studio, sync workflows to completeu-server
rsync -av workflows/temporal/ marc@192.168.1.186:~/agentic-system/workflows/temporal/
```

**All nodes** (start workers):
```bash
# mac-studio
nohup python3 workflows/temporal/start_orchestrator_workers.py &

# macbook-air
ssh marc@192.168.1.76 "cd ~/agentic-system && nohup python3 workflows/temporal/start_researcher_workers.py &"

# completeu-server
ssh marc@192.168.1.186 "cd ~/agentic-system && nohup python3 workflows/temporal/start_inference_workers.py &"
```

### Phase 4: Integrate macpro51 Builder API ✅ READY

**Test integration**:
```bash
curl http://192.168.1.183:9000/api/v1/status
```

**cluster-task-orchestration** will route build tasks to macpro51

## Workflow Distribution

| Workflow | Primary Node | Backup | Frequency |
|----------|-------------|---------|-----------|
| cluster-memory-sync | mac-studio | - | 15 min |
| cluster-task-orchestration | mac-studio | - | continuous |
| cluster-health-monitoring | mac-studio | - | 5 min |
| system-optimization | mac-studio | macbook-air | on-demand |
| memory-manager | All macOS | - | hourly |
| overnight-research | macbook-air | completeu-server | 10PM-7AM |
| pattern-learning | macbook-air | - | daily |
| goal-decomposition | macbook-air | mac-studio | on-demand |
| memory-consolidation | All macOS | - | nightly |
| deep-learning-optimizer | completeu-server | - | 6h |
| recursive-self-improvement | completeu-server | - | weekly |
| Build/Test tasks | macpro51 (API) | - | on-demand |

## Resource Allocation

### CPU/Memory by Node

**mac-studio**: Orchestration (lightweight workflows)
- Cluster coordination
- Memory sync
- Health monitoring

**macbook-air**: Research (medium workflows)
- Overnight research
- Pattern analysis
- Goal decomposition

**completeu-server**: AI Inference (heavy workflows)
- LLM inference via Ollama (23 models)
- Deep learning optimization
- Self-improvement with model access

**macpro51**: Build/Test (heavy tasks)
- Compilation (24 threads)
- Test suites (126 GB RAM)
- Container builds (RAID10 storage)

## Node-Specific Worker Scripts Needed

### Create These Files:

1. `workflows/temporal/start_orchestrator_workers.py` (mac-studio)
2. `workflows/temporal/start_researcher_workers.py` (macbook-air)
3. `workflows/temporal/start_inference_workers.py` (completeu-server)

Each imports only relevant workflows for that node's role.

## Immediate Next Actions

1. **Fix sandbox issues** in workflows (remove Path.resolve())
2. **Stop redundant Temporal servers** on macbook-air and completeu-server
3. **Create node-specific worker scripts**
4. **Deploy workflows to completeu-server**
5. **Test Builder API integration** with macpro51
6. **Start all workers** across cluster
7. **Monitor Temporal UI** at http://192.168.1.16:8233

## Success Criteria

- ✅ All 4 nodes visible and reachable
- ✅ Single Temporal server (mac-studio)
- ✅ Workers running on 3 macOS nodes
- ✅ Builder API integrated with orchestrator
- ✅ Cluster memory sync operational
- ✅ At least 9 workflows running
- ✅ Tasks routing to optimal nodes
- ✅ AI inference via completeu-server Ollama

## Monitoring Dashboard

Access points:
- **Temporal UI**: http://192.168.1.16:8233
- **Grafana**: http://192.168.1.16:9500
- **Builder API**: http://192.168.1.183:9000/api/v1/status
- **Ollama**: http://192.168.1.186:11434/api/tags
