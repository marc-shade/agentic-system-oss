# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **24/7 autonomous agentic system** running on distributed Mac/Linux hardware. Provides persistent AI through Temporal workflows, MCP servers, intelligent agents, and physical hardware integration via Arduino.

## TL;DR - Essential Commands

```bash
# Storage path (ALWAYS source first)
source scripts/detect-storage.sh && cd $STORAGE_BASE

# Health check
python3 system_health_check.py

# Run AGI demo (~0.5s)
python3 demo_agi_workflow.py

# Cluster status
python3 cluster-deployment/distributed_task_router.py cluster-status

# Distributed execution (Python API)
from cluster_offload import offload
result = offload("make build")  # Auto-routes to optimal node

# Distributed execution (MCP - preferred)
mcp__cluster-execution-mcp__cluster_bash(command="make build")
mcp__cluster-execution-mcp__offload_to(node_id="macpro51", command="docker build .")

# AGI orchestrator (Python)
from agi_orchestrator import AGIOrchestrator
result = await AGIOrchestrator().execute_goal("Build a REST API")
```

## System Architecture

### Storage Path Detection

**Auto-detect correct paths for your platform**:

```bash
# Source detection script to set $STORAGE_BASE
source scripts/detect-storage.sh

# Verify
echo $STORAGE_BASE
# macOS output: /Volumes/SSDRAID0/agentic-system/
# Linux output: /home/marc/agentic-system/
```

**Important**: Always use `$STORAGE_BASE` in scripts instead of hardcoded paths. This ensures compatibility across all cluster nodes.

### Container Runtime Preference

Container runtime preference varies by platform:

**macOS Nodes** (mac-studio, macbook-air, macbook-pro):
- **Primary**: Apple Container (`container` command) - Native macOS, optimized for Apple silicon
- **Fallback**: Docker - Cross-platform compatibility
- **Apple Container**: Swift-based, OCI-compatible, requires macOS 26+, see `INSTALL_APPLE_CONTAINER.md`

**Linux Nodes** (macpro51):
- **Primary**: Podman - Rootless containers, native on Fedora/RHEL
- **Fallback**: Docker - Standard containerization
- **Benefits**: Native systemd integration, rootless by default, OCI-compatible

All sandboxed testing environments automatically detect and prefer the optimal runtime for the platform.

### Storage Architecture

Storage paths vary by node:

**macOS Nodes** (mac-studio, macbook-air, macbook-pro):
- **Hot Tier (SSDRAID0)**: `/Volumes/SSDRAID0/agentic-system/` - Active execution and databases
- **Cold Tier (FILES)**: `/Volumes/FILES/agentic-system/` - Backups only, **NEVER run code from here**
- **CRITICAL**: All code execution must use SSDRAID0 paths. The FILES drive is backup-only.

**Linux Nodes** (macpro51):
- **Primary Storage**: `/home/marc/agentic-system/` - Active execution and databases
- **Mount Point**: `/mnt/agentic-system/` - RAID10 array mount (symlinked to ~/agentic-system)
- **NVMe RAID10**: 930GB high-performance storage for workloads (mdadm /dev/md0)
- **Cluster Sync**: Shared memories synced to orchestrator via SMB/Avahi
- **Auto-detection**: Use `scripts/detect-storage.sh` to automatically determine correct paths

**Backup Sync**: Automated hourly backup via `backup-sync.sh` (macOS nodes only)

### Multi-Node Cluster Architecture

**macOS Nodes**:
- **mac-studio (Orchestrator)**: System coordination, priority 1, Apple Silicon
- **macbook-air (Researcher)**: Analysis and documentation, priority 2, Apple Silicon
- **macbook-pro (Developer)**: Implementation and testing, priority 2, Apple Silicon

**Linux Nodes**:
- **macpro51 (Builder)**: Compilation, testing, containerization, priority 3
  - Dual Intel Xeon X5680 (24 threads @ 3.33 GHz)
  - 126 GB RAM, 930 GB NVMe RAID10
  - Fedora 43, Docker/Podman native
  - Specialized for: Linux builds, test execution, performance benchmarking, CI/CD

Each node has:
- Personal memories (node-specific storage in `databases/cluster/nodes/{node-id}/`)
- Shared memories (cluster-wide access in `databases/cluster/shared_memories.db`)
- Node attribution for all operations
- Specialized persona-based workflows
- Avahi discovery and heartbeat monitoring

### Core Components

**Autonomous Workflows**:
- **Temporal**: Long-running workflows with state persistence (port 7233, UI on 8233)
- **AutoKitteh**: Event-driven workflows and real-time orchestration (port 9980)
- **n8n**: Visual workflow automation (port 5678)

**MCP Servers** (Essential - Always Active):
- `enhanced-memory-mcp` (port 8101): Compressed memory with versioning, 4-tier architecture
- `agent-runtime-mcp` (port 8102): Persistent task management across sessions
- `sequential-thinking`: Deep reasoning with chain-of-thought
- `voice-mode`: TTS/STT integration for voice communication
- `arduino-surface` (port 8200): Physical hardware control interface
- `ember-mcp`: Production-only policy enforcement and quality guardian
- `cluster-execution-mcp`: Distributed task routing and parallel execution across cluster
- `node-chat-mcp`: Inter-node agent communication and AGI coordination
- `safla-mcp`: Hybrid memory with 1.75M+ ops/sec embeddings

**MCP Servers** (Research & Knowledge):
- `research-paper-mcp`: arXiv/Semantic Scholar paper search and analysis
- `video-transcript-mcp`: YouTube transcript extraction and concept mining

**Intelligent Agents** (replaces polling scripts):
- Multi-provider support: Claude Code, OpenAI Codex, Gemini CLI
- Autonomous reasoning and decision-making
- Adaptive check intervals based on system state
- Evolution-aware protection systems
- Claude Code Skills for automatic AI routing (`codex-consultant`, `gemini-analyst`, `ai-orchestrator`)
- Programmatic CLI execution (formerly "headless"): `claude -p "task" --output-format json` or `gemini "task"` with image support

**AGI Orchestrator** (6-phase unified workflow):
- Goal Decomposition → Context Synthesis → Multi-Agent Coordination → Meta-Learning → Skill Evolution → Darwin Gödel
- Entry point: `from agi_orchestrator import AGIOrchestrator; await orchestrator.execute_goal("...")`
- Demo: `python3 demo_agi_workflow.py` (~0.5s for full workflow)

**Distributed Task Execution** (7/7 tests passing):
- Automatic routing based on OS, architecture, capabilities
- Aggressive offloading (100% offload rate)
- Parallel execution across cluster
- Simple API: `from cluster_offload import offload; result = offload("command")`
- MCP API: `mcp__cluster-execution-mcp__cluster_bash(command="...")`

**Inter-Node Communication** (via node-chat-mcp):
- Agent-to-agent messaging across cluster nodes
- Persona-aware conversations with context preservation
- AGI coordination tools: goal decomposition, research pipelines, improvement cycles
- Cluster awareness and relationship tracking

**Monitoring Stack**:
- **Prometheus** (port 9700): Metrics collection (30-day retention)
- **Loki** (port 9900): Log aggregation (7-day retention)
- **Grafana** (port 9500): Unified visualization dashboard

**Physical Integration** (macOS nodes only):
- **Arduino Surface**: LCD display, RGB LEDs, servo, buzzer, sensors, buttons
- Enables human-in-the-loop workflows and ambient system monitoring
- Serial port: `/dev/tty.usbmodem*` (varies when replugged - use `ls /dev/tty.usbmodem*`)

**Builder Node Services** (Linux nodes):
- **Builder API**: HTTP API on port 9000 for orchestrator control
- **Hardware Broadcast**: System metrics on port 8888
- **Service Discovery**: Avahi/mDNS announcing `_agentic-builder._tcp`
- **Port Management**: Automated port tracking and firewall configuration

### Port Reference (All Services)

| Service | Port | Protocol | Nodes |
|---------|------|----------|-------|
| Temporal gRPC | 7233 | gRPC | macOS |
| Temporal UI | 8233 | HTTP | macOS |
| AutoKitteh | 9980 | HTTP | All |
| n8n | 5678 | HTTP | All |
| Prometheus | 9700 | HTTP | All |
| Loki | 9900, 9901 | HTTP/gRPC | All |
| Grafana | 9500 | HTTP | All |
| Qdrant REST | 6333 | HTTP | All |
| Qdrant gRPC | 6334 | gRPC | All |
| Redis | 6379 | TCP | All |
| enhanced-memory-mcp | 8101 | HTTP | All |
| agent-runtime-mcp | 8102 | HTTP | All |
| arduino-surface | 8200 | HTTP | macOS |
| cluster-execution-mcp | - | stdio | All |
| node-chat-mcp | - | stdio | All |
| safla-mcp | - | stdio | All |
| Builder API | 9000 | HTTP | Linux |
| Hardware Info | 8888 | HTTP | Linux |
| Ollama | 11434 | HTTP | Linux |

## Development Workflows

### Python Environment Setup

**Install dependencies for intelligent agents**:

```bash
cd $STORAGE_BASE/intelligent-agents
pip3 install -r requirements.txt

# Verify installation
python3 -c "import anthropic, openai; print('✓ AI SDKs installed')" 2>/dev/null || echo "Install anthropic and openai packages"
```

**Set API keys** (required for intelligent agents):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AIza..."

# Verify
echo $ANTHROPIC_API_KEY | grep -q "sk-ant" && echo "✓ Keys set"
```

**Install MCP server dependencies**:

```bash
cd $STORAGE_BASE/mcp-servers/enhanced-memory-mcp
pip3 install -r requirements.txt

cd $STORAGE_BASE/mcp-servers/agent-runtime-mcp
pip3 install -r requirements.txt
```

### Node Initialization

When setting up a new cluster node, use the `/init-node` command to:
- Detect node identity and configure persona
- Create directory structure for cluster databases
- Install Python dependencies for intelligent agents
- Test cluster memory connectivity
- Verify MCP server configuration

This ensures proper node registration and cluster integration.

### Starting Core Services

**Note**: Service paths vary by platform. Use `$STORAGE_BASE` which resolves to:
- macOS: `/Volumes/SSDRAID0/agentic-system/`
- Linux: `/home/marc/agentic-system/` (or auto-detect with `source scripts/detect-storage.sh`)

**Temporal Server** (macOS nodes):
```bash
cd $STORAGE_BASE/scripts
./start-temporal.sh
# Access UI at http://localhost:8233
```

**Temporal Workers** (macOS nodes):
```bash
./start-temporal-workers.sh
```

**AutoKitteh** (all nodes):
```bash
cd $STORAGE_BASE/scripts
./start-autokitteh.sh
# Runs in background, logs to logs/autokitteh.log
```

**Monitoring Stack** (all nodes):
```bash
cd $STORAGE_BASE/monitoring
# macOS: ./start-all.sh
# Linux: ./install-monitoring-podman.sh (first time), then systemctl commands
```

**Qdrant (Vector Database)** (all nodes):
```bash
# macOS: cd $STORAGE_BASE/scripts && ./start-qdrant.sh
# Linux: docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant
# Port 6333 (REST), 6334 (gRPC)
```

**Builder Node API** (Linux nodes only):
```bash
systemctl --user status builder-node-api.service
systemctl --user start builder-node-api.service
# Access at http://localhost:9000/api/v1/status
```

### Container Management

```bash
# Use podman (Linux) or docker (macOS) - commands are identical
RUNTIME="podman"  # or "docker"

$RUNTIME ps                      # List containers
$RUNTIME logs -f redis           # View real-time logs
$RUNTIME restart qdrant          # Restart container
$RUNTIME stats                   # Resource usage
$RUNTIME stop redis && $RUNTIME rm redis  # Remove container
```

### MCP Server Management

MCP servers are configured in:
- **User-level**: `~/.claude.json` (main configuration)
- **Project-level**: `.mcp.json` (shared via git)

**NEVER** modify:
- `~/.claude/settings.json` (permissions only, not MCP config)
- `~/.claude/claude_desktop_config.json` (Desktop app only)

### Running Tests

```bash
# Run a single test file
python3 path/to/test_file.py

# AGI system demo (~0.5s, full 6-phase workflow)
python3 demo_agi_workflow.py

# System health check
python3 system_health_check.py

# MCP servers
cd $STORAGE_BASE/mcp-servers/enhanced-memory-mcp && python3 comprehensive_test.py
cd $STORAGE_BASE/mcp-servers/agent-runtime-mcp && python3 test_agent_runtime.py

# Cluster/distributed execution (7/7 tests)
cd $STORAGE_BASE/cluster-deployment && python3 test_distributed_execution.py
cd $STORAGE_BASE/cluster-deployment && python3 test_cluster_memory.py

# Intelligent agents
cd $STORAGE_BASE/intelligent-agents && python3 specialized/code_evolution_protector.py
cd $STORAGE_BASE/intelligent-agents && python3 cluster_health_monitor.py
cd $STORAGE_BASE/intelligent-agents && python3 agent_eval_framework.py

# Arduino hardware (macOS only)
cd $STORAGE_BASE/arduino-surface && python3 test_hardware.py /dev/tty.usbmodem*

# Linux benchmarks
cd $STORAGE_BASE/scripts && ./run-baseline-benchmarks.sh

# Check RAG status
python3 check_rag_status.py

# Check learning progress
python3 check_learning_progress.py
```

### Additional Entry Points

```bash
# Autonomous recursive AGI loop (long-running)
python3 autonomous_recursive_agi_loop.py

# Cognitive runtime integration
python3 cognitive_runtime_integration.py

# Cluster health dashboard
python3 cluster_health_dashboard.py

# System status dashboard
python3 system_status_dashboard.py
```

### Port Management (Linux Builder Node)

```bash
cd $STORAGE_BASE/scripts
python3 port-manager.py              # List all ports
python3 port-manager.py --agentic    # Agentic services only
python3 port-manager.py --check      # Verify required ports
python3 port-manager.py --suggest    # Firewall suggestions
```

### Web Worker Orchestrator

Distributed code execution across Claude Code instances:

```bash
cd $STORAGE_BASE/web-worker-orchestrator
npm install              # First time only
npm run build            # Compile TypeScript
npm start                # Start orchestrator
npm run logs             # View orchestration logs
npm run status           # Check system status
npm run sessions         # View active sessions
```

## Key Databases

Databases are stored at `$STORAGE_BASE/databases/`:

- `temporal/` - Temporal workflow state
- `qdrant/` - Vector embeddings for memory
- `cluster/` - Multi-node cluster memory
  - `shared_memories.db` - Cluster-wide memories
  - `node_registry.db` - Node coordination
  - `nodes/{node-id}/personal_memories.db` - Node-specific memories
- `mcp/` - MCP server data
- `claude/` - Claude Code learning data
- `voice_notifications.db` - Voice system logs
- `sensory/` - Sensor data from Arduino

## Common Development Tasks

### Adding a New MCP Server

1. Create server in `mcp-servers/{server-name}/`
2. Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "python3",
      "args": ["$STORAGE_BASE/mcp-servers/server-name/server.py"],
      "env": {},
      "disabled": false
    }
  }
}
```
3. Restart Claude Code to load server

Note: Use absolute paths for your node's storage location.

### Creating a Temporal Workflow

1. Add workflow to `workflows/temporal/`
2. Register in worker: `scripts/start-temporal-workers.sh`
3. Deploy:
```bash
temporal workflow start --type YourWorkflow --task-queue your-queue
```

### Creating an Intelligent Agent

1. Choose SDK base: `intelligent-agents/sdk_agents/{claude|codex|gemini}_agent.py`
2. Define purpose and decision criteria
3. Implement `gather_observations()` and `execute_decision()`
4. Test standalone before integrating with workflows

```python
from sdk_agents.claude_agent import ClaudeAgent, AgentPurpose

purpose = AgentPurpose(
    name="My Agent",
    description="What it does",
    primary_goal="Main objective",
    decision_criteria=["When to act", "What to prioritize"],
    tools_needed=["tool1", "tool2"]
)

class MyAgent(ClaudeAgent):
    async def gather_observations(self) -> Dict[str, Any]:
        return {"metric": get_metric()}  # AI decides what to do

    async def execute_decision(self, decision) -> Dict[str, Any]:
        if decision.tool_used == "alert":
            send_alert(decision.decision)
        return {"status": "executed"}

agent = MyAgent(purpose)
await agent.start(check_interval=60)  # Adapts based on observations
```

**Key difference from scripts**: Agents THINK (AI reasoning), scripts just RUN (fixed logic)

### Working with Cluster Memory

```python
from cluster_memory import ClusterMemoryManager

# Create personal memory (node-specific)
manager.create_entity(name="task", entity_type="work",
                      observations=["data"], scope="personal")

# Create shared memory (cluster-wide)
manager.create_entity(name="finding", entity_type="knowledge",
                      observations=["insight"], scope="shared")

# Search across all nodes
results = manager.search_entities("query", scope="all")

# Get memories from specific node
node_memories = manager.get_node_memories("macbook-air")
```

### Self-Optimization Workflows

The system can autonomously optimize its own configuration using the agentic marker system:

```bash
# Simple optimizer (no dependencies)
cd $STORAGE_BASE/workflows
python3 simple_optimizer.py --dry-run  # See proposed changes
python3 simple_optimizer.py            # Apply optimizations

# View optimization markers
tail ~/.claude/.config_modifications.jsonl | jq .

# Verify with watchdog
python3 $STORAGE_BASE/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### AGI Workflows

The system includes a complete AGI orchestrator with 6-phase workflow execution:

```python
from agi_orchestrator import AGIOrchestrator

orchestrator = AGIOrchestrator()

# Execute a goal with full AGI workflow
result = await orchestrator.execute_goal(
    goal_description="Build a REST API for user authentication",
    context={"language": "Python", "framework": "FastAPI"},
    record_learning=True,
    propose_improvements=True
)

# Check learning progress
summary = orchestrator.meta_learning.get_learning_summary()
print(f"Success rate: {summary['overall_success_rate']:.1%}")
```

**6-Phase Workflow**:
1. **Goal Decomposition** - Parse natural language into hierarchical tasks
2. **Context Synthesis** - Gather relevant information from memory/codebase
3. **Multi-Agent Coordination** - Execute tasks in parallel with specialized agents
4. **Meta-Learning** - Record outcomes for continuous improvement
5. **Skill Evolution** - Track successful patterns, run A/B tests
6. **Darwin Gödel** - Self-improvement proposals based on performance

**Quick usage**: `python3 demo_agi_workflow.py` runs the full workflow in ~0.5s

### Distributed Task Execution

```python
from cluster_offload import offload, offload_many

# Simple offload - automatic routing
result = offload("echo 'Hello' && hostname")

# Linux-specific task
result = offload("make build", requires_os="linux")

# Parallel execution across cluster
results = offload_many([
    "python3 test_1.py",
    "python3 test_2.py",
    "python3 test_3.py"
])
```

**CLI**:
```bash
cd $STORAGE_BASE/cluster-deployment
python3 distributed_task_router.py submit "hostname"
python3 distributed_task_router.py cluster-status
```

### Inter-Node Communication (node-chat-mcp)

```python
# Send message to another node's AI persona
mcp__node-chat-mcp__send_message_to_node(to_node="builder", message="Start compilation")

# Check for incoming messages
mcp__node-chat-mcp__check_for_new_messages()

# Get cluster awareness (all nodes, their capabilities, status)
mcp__node-chat-mcp__get_cluster_awareness()

# Prepare context before conversation (loads persona, history, relationship)
mcp__node-chat-mcp__prepare_conversation_context(with_node="orchestrator")

# AGI coordination tools
mcp__node-chat-mcp__decompose_goal(goal="Optimize memory consolidation 10x")
mcp__node-chat-mcp__initiate_research_pipeline(research_topic="efficient graph neural networks")
mcp__node-chat-mcp__start_improvement_cycle(target_metric="task_routing_latency")
```

### Ember Policy Enforcement (ember-mcp)

Ember is the production-only policy enforcer. Consult before risky operations:

```python
# Check if action violates production-only policy
mcp__ember-mcp__ember_check_violation(
    action="Write",
    params={"file_path": "/path/to/file", "content": "..."},
    context="implementing user authentication"
)

# Get quality feedback on recent work
mcp__ember-mcp__ember_get_feedback(timeframe="session")

# Consult Ember for decision guidance
mcp__ember-mcp__ember_consult(
    question="Should we use JWT or session-based auth?",
    options=["JWT tokens", "Session cookies", "OAuth2"],
    context="Building user authentication system"
)

# Report outcomes for Ember's learning
mcp__ember-mcp__ember_learn_from_outcome(
    action="implemented_jwt_auth",
    success=True,
    outcome="Authentication working, all tests passing"
)
```

### SAFLA Hybrid Memory (safla-mcp)

High-performance embeddings and hybrid memory:

```python
# Generate embeddings (1.75M+ ops/sec)
mcp__safla-mcp__generate_embeddings(texts=["concept 1", "concept 2", "concept 3"])

# Store in hybrid memory (episodic, semantic, or procedural)
mcp__safla-mcp__store_memory(content="Learned optimization pattern", memory_type="semantic")

# Retrieve from memory
mcp__safla-mcp__retrieve_memories(query="optimization patterns", limit=5)

# Get SAFLA performance metrics
mcp__safla-mcp__get_performance()
```

### Research and Knowledge Tools

```python
# Search academic papers (arXiv, Semantic Scholar)
mcp__research-paper-mcp__search_arxiv(query="recursive self-improvement AGI", max_results=10)
mcp__research-paper-mcp__search_semantic_scholar(query="meta-learning", limit=10)

# Analyze citations
mcp__research-paper-mcp__analyze_citations(paper_id="arxiv:2301.xxxxx", depth=2)

# Extract insights from papers
mcp__research-paper-mcp__extract_insights(paper_text="...", focus_areas=["methodology", "results"])

# YouTube transcript extraction
mcp__video-transcript-mcp__fetch_youtube_transcript(url="https://youtube.com/watch?v=...")
mcp__video-transcript-mcp__extract_concepts(transcript="...", focus_domains=["AI", "AGI"])
```

## Directory Structure

```
agentic-system/
├── arduino-surface/          # Physical hardware interface (macOS only)
├── cluster-deployment/       # Multi-node deployment tools
├── databases/                # All persistent data (hot tier)
│   ├── cluster/              # Multi-node cluster databases
│   │   ├── shared_memories.db
│   │   ├── node_registry.db
│   │   └── nodes/{node-id}/  # Node-specific data
│   ├── temporal/             # Temporal workflow state
│   ├── qdrant/               # Vector database storage
│   └── mcp/                  # MCP server databases
├── intelligent-agents/       # AI-powered autonomous agents
├── intelligent-self-healing/ # Self-optimization and protection
├── mcp-servers/              # MCP protocol servers
│   ├── enhanced-memory-mcp/  # 4-tier memory with RAG
│   ├── agent-runtime-mcp/    # Persistent task management
│   ├── ember-mcp/            # Quality and policy enforcement
│   └── SAFLA/                # Hybrid memory architecture
├── monitoring/               # Prometheus + Loki + Grafana
├── persistent-agent-sdk/     # Multi-provider agent runtime
├── scripts/                  # Service startup scripts
│   ├── hooks/                # Claude Code lifecycle hooks
│   ├── detect-storage.sh     # Auto-detect storage paths
│   ├── port-manager.py       # Port tracking and firewall
│   └── init-node.sh          # Node initialization
├── services/                 # Service implementations
│   ├── builder-node-api.py   # Builder orchestrator API (Linux)
│   └── kutiraai/             # Kutira AI platform
├── workflows/                # Autonomous optimization workflows
│   ├── temporal/             # Long-running workflows
│   └── autokitteh/           # Event-driven workflows
├── web-worker-orchestrator/  # Distributed execution
├── logs/                     # All system logs
└── tmp-workspace/            # Temporary working directory
```

## Critical Implementation Notes

1. **Platform Awareness**: Use node-appropriate paths and container runtimes
   - macOS: `/Volumes/SSDRAID0/agentic-system/`, Apple Container preferred
   - Linux: `/home/marc/agentic-system/`, Podman preferred
2. **Storage Tiers** (macOS only): Always use SSDRAID0 for execution, FILES for backups only
3. **Serial Port Autodiscovery** (macOS nodes): Arduino port changes when replugged - use `ls /dev/tty.usbmodem*`
4. **MCP Configuration**: User config in `~/.claude.json`, NOT in settings.json
5. **Memory Tiers**: Use appropriate scope (personal/shared/all) for cluster operations
6. **Node Personas**: Respect node specializations (Orchestrator, Researcher, Developer, Builder)
7. **Cluster Discovery**: Nodes auto-discover via Avahi and heartbeat to orchestrator
8. **Intelligent Agents**: Prefer agent-based solutions over polling scripts
9. **Production-Only Policy**: Ember enforces no POCs, no demos, no placeholder content
10. **Parallel Execution**: Leverage native parallel tool calls for performance
11. **Context Preservation**: Use `/continue` for complex multi-session projects
12. **Voice Communication** (macOS nodes): Always use Voice Mode MCP for user communication
13. **Marker System**: Use agentic markers for self-improvements to prevent watchdog rollbacks
14. **Node Initialization**: Use `/init-node` to set up new cluster nodes
15. **Storage Path Variables**: Always source `scripts/detect-storage.sh` to set `$STORAGE_BASE`

## Protected vs Modifiable Configuration Keys

**Protected (Never Modify)**:
- `statusLine.command`
- `hooks.*.path`
- `apiKeys.*`
- `credentials.*`
- `mcpServers.*.command`

**Modifiable (Safe for Optimization)**:
- `maxTokens`
- `parallelToolCalls`
- `cachingStrategy`
- `mcpServers.*.timeout`
- `loggingLevel`
- Memory and performance settings

## Performance Expectations

**Resource Usage**:
- Temporal: ~150-250MB RAM
- Monitoring stack: ~300-600MB RAM (Prometheus + Loki + Grafana)
- MCP servers: ~50-100MB RAM each
- Intelligent agents: ~50MB RAM each

**Storage**:
- Prometheus metrics: ~100MB/day (30-day retention = ~3GB)
- Loki logs: Varies by volume (7-day retention)
- Databases: ~500MB-2GB active working set
- Backups: ~5-10GB (cold tier)

**Note**: See "Port Reference (All Services)" table in System Architecture section for complete port list.

## Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| Temporal won't start | `lsof $STORAGE_BASE/databases/temporal/temporal.db` → kill locked processes |
| MCP server not loading | `cat ~/.claude.json \| jq '.mcpServers'` → verify config, test standalone |
| Arduino not detected | `ls /dev/tty.usbmodem*` → update port in config |
| Monitoring issues | `ps aux \| grep -E 'prometheus\|loki\|grafana'` → check services running |
| Cluster memory sync | `python3 cluster-deployment/test_cluster_memory.py` → test connectivity |
| Port conflicts (Linux) | `python3 scripts/port-manager.py` → `sudo kill $(sudo lsof -t -i:PORT)` |
| RAID status (Linux) | `cat /proc/mdstat` → `mdadm --detail /dev/md0` |
| Builder API (Linux) | `systemctl --user status builder-node-api.service` → check logs with journalctl |
| Storage paths | `source scripts/detect-storage.sh && echo $STORAGE_BASE` |

## Documentation References

- **Quick Start**: `QUICK_START.md` - AGI system usage examples
- **System Catalog** (Linux): `SYSTEM-CATALOG.md` - Complete node status and configuration
- **Arduino setup** (macOS): `arduino-surface/CLAUDE.md`
- **Gemini overview**: `GEMINI.md` - Project overview for Gemini
- **Intelligent agents**: `intelligent-agents/README.md`
- **Cluster deployment**: `cluster-deployment/README.md`
- **Monitoring**: `monitoring/README.md`
- **Workflows**: `workflows/README.md`
- **Self-healing**: `intelligent-self-healing/AGENTIC_SELF_IMPROVEMENT_COMPLETE.md`
- **Web orchestration**: `web-worker-orchestrator/README.md`

## Builder API Reference (Linux Node)

**Endpoints** (Port 9000 on macpro51):
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/status` | GET | Comprehensive status |
| `/api/v1/builder` | GET | Builder info |
| `/api/v1/capabilities` | GET | Node capabilities |
| `/api/v1/control/execute` | POST | Execute commands |

Quick test: `curl http://macpro51.local:9000/api/v1/health | jq .`

**See `SYSTEM-CATALOG.md`** for complete Linux node documentation.
