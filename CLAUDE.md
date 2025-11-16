# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **24/7 autonomous agentic system** running on Mac hardware with distributed multi-node architecture. The system provides persistent AI capabilities through Temporal workflows, MCP (Model Context Protocol) servers, intelligent agents, and physical hardware integration via Arduino.

**Core Purpose**: Enable autonomous, self-improving AI agents with persistent memory, distributed computing, physical world interaction, and continuous optimization.

## Quick Health Check

**Verify system is operational**:

```bash
# Detect storage path and set $STORAGE_BASE
source scripts/detect-storage.sh && echo "Storage: $STORAGE_BASE"

# Check node type
cat ~/.claude/node-config.json 2>/dev/null || echo "Run /init-node to configure"

# Check core services (Linux)
systemctl --user status builder-node-api.service 2>/dev/null

# Check containers
docker ps 2>/dev/null || podman ps | grep -E 'redis|qdrant|n8n'

# Test MCP connectivity
python3 -c "import sys; sys.path.insert(0, 'mcp-servers/enhanced-memory-mcp'); from memory_manager import MemoryManager; print('✓ MCP working')" 2>/dev/null || echo "MCP needs setup"

# Check cluster memory
sqlite3 databases/cluster/shared_memories.db "SELECT COUNT(*) FROM entities;" 2>/dev/null || echo "Cluster DB not initialized"
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

**Intelligent Agents** (replaces polling scripts):
- Multi-provider support: Claude Code, OpenAI Codex, Gemini CLI
- Autonomous reasoning and decision-making
- Adaptive check intervals based on system state
- Evolution-aware protection systems

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

**Platform-specific runtime**:

```bash
# Linux (Podman preferred)
podman ps                    # List running containers
podman logs -f redis         # View container logs
podman restart qdrant        # Restart a container
podman stop n8n              # Stop a container

# macOS (Docker or Apple Container)
docker ps                    # List running containers
container list               # Apple Container on macOS 26+
docker logs -f redis         # View logs
docker restart qdrant        # Restart container
```

**Common container operations**:

```bash
# Check all running containers
podman ps  # or: docker ps

# View real-time logs
podman logs -f redis
podman logs -f qdrant
podman logs -f n8n

# Restart containers
podman restart redis
podman restart qdrant

# Check container resource usage
podman stats

# Remove and recreate container
podman stop redis && podman rm redis
# Then run start script to recreate
```

### MCP Server Management

MCP servers are configured in:
- **User-level**: `~/.claude.json` (main configuration)
- **Project-level**: `.mcp.json` (shared via git)

**NEVER** modify:
- `~/.claude/settings.json` (permissions only, not MCP config)
- `~/.claude/claude_desktop_config.json` (Desktop app only)

### Running Tests

**Test MCP servers**:

```bash
# Enhanced Memory MCP
cd $STORAGE_BASE/mcp-servers/enhanced-memory-mcp
python3 comprehensive_test.py
python3 test_rag_integration.py

# Agent Runtime MCP
cd $STORAGE_BASE/mcp-servers/agent-runtime-mcp
python3 test_agent_runtime.py
```

**Test intelligent agents**:

```bash
cd $STORAGE_BASE/intelligent-agents

# Test System Health Guardian (macOS only - requires Arduino)
python3 specialized/system_health_guardian.py /dev/tty.usbmodem8344401

# Test Code Evolution Protector
python3 specialized/code_evolution_protector.py
```

**Test cluster deployment**:

```bash
cd $STORAGE_BASE/cluster-deployment
python3 test_cluster_memory.py
```

**Test AGI system**:

```bash
cd $STORAGE_BASE
python3 demo_agi_workflow.py          # Demo 6-phase AGI workflow
python3 system_health_check.py        # Check system health
```

**Run benchmarks** (Linux nodes):

```bash
cd $STORAGE_BASE/scripts
./run-baseline-benchmarks.sh
```

**Test Arduino hardware** (macOS nodes only):

```bash
cd $STORAGE_BASE/arduino-surface
python3 test_hardware.py /dev/tty.usbmodem8344401
```

### Port Management (Linux Builder Node)

**Quick port commands**:

```bash
cd $STORAGE_BASE/scripts

# List all listening ports
python3 port-manager.py

# Show only agentic services
python3 port-manager.py --agentic

# Check required ports are available
python3 port-manager.py --check

# Get firewall suggestions
python3 port-manager.py --suggest

# Export port map for orchestrator
python3 port-manager.py export
```

**Manual port checks**:

```bash
# Check specific port
sudo lsof -i :9000
ss -tuln | grep 9000

# Kill process on port
sudo kill $(sudo lsof -t -i:9000)

# Check firewall rules
sudo firewall-cmd --list-all
sudo firewall-cmd --list-ports
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
import asyncio

# Initialize orchestrator
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

**Quick test**:
```bash
cd $STORAGE_BASE
python3 demo_agi_workflow.py  # Demo complete workflow in ~0.5 seconds
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

**Service Ports**:
- Temporal: 7233 (gRPC), 8233 (UI) - macOS only
- AutoKitteh: 9980
- n8n: 5678
- Prometheus: 9700
- Loki: 9900, 9901 (gRPC)
- Grafana: 9500
- Qdrant: 6333 (REST), 6334 (gRPC)
- Redis: 6379
- MCP servers: 8101, 8102, 8200, 8300
- Builder API: 9000 - Linux only
- Hardware Info: 8888 - Linux only
- Ollama: 11434 - Linux only

## Troubleshooting

**Temporal won't start**:
```bash
# Check if database is locked
lsof $STORAGE_BASE/databases/temporal/temporal.db
# Kill processes if needed, then restart
```

**MCP server not loading**:
```bash
# Verify config
cat ~/.claude.json | jq '.mcpServers'
# Check server can run standalone
python3 $STORAGE_BASE/mcp-servers/{server}/server.py
```

**Arduino not detected**:
```bash
# Find current port
ls /dev/tty.usbmodem*
# Update port in configuration
```

**Monitoring stack issues**:
```bash
# Check all services
ps aux | grep -E 'prometheus|loki|grafana' | grep -v grep
# View logs
tail -f $STORAGE_BASE/monitoring/{service}/logs/*.log
```

**Cluster memory sync issues**:
```bash
# Verify node configuration
cat ~/.claude/node-config.json
# Check shared database access
sqlite3 $STORAGE_BASE/databases/cluster/shared_memories.db "SELECT COUNT(*) FROM entities;"
# Test cluster connectivity
cd $STORAGE_BASE/cluster-deployment
python3 test_cluster_memory.py
```

**Port conflicts** (Linux nodes):
```bash
# Check what's using a port
python3 scripts/port-manager.py
sudo lsof -i :PORT_NUMBER
# Kill process on port
sudo kill $(sudo lsof -t -i:PORT_NUMBER)
```

**RAID status** (Linux nodes):
```bash
# Check RAID health
cat /proc/mdstat
mdadm --detail /dev/md0
# Monitor rebuilds
watch -n 1 cat /proc/mdstat
```

**Builder API not responding** (Linux nodes):
```bash
# Check service status
systemctl --user status builder-node-api.service
# View logs
journalctl --user -u builder-node-api.service -f
# Test API directly
curl http://localhost:9000/api/v1/health
```

**Storage path issues**:
```bash
# Detect correct storage path
source scripts/detect-storage.sh
echo "Using: $STORAGE_BASE"

# Verify path exists and is writable
test -d "$STORAGE_BASE" && test -w "$STORAGE_BASE" && echo "✓ Storage OK" || echo "✗ Storage issue"
```

## Integration Points

**Voice Mode** (macOS): Use for all user communication - supports TTS/STT, emotions, multilingual
**Arduino Surface** (macOS): Human-in-the-loop approvals, ambient monitoring, physical feedback
**Builder API** (Linux): HTTP endpoints for orchestrator control and status monitoring
**Enhanced Memory**: Store learnings, patterns, project outcomes with compression
**Agent Runtime**: Persistent tasks that survive across sessions
**Sequential Thinking**: Deep reasoning for complex problems
**Ember**: Quality guardian - enforces production-only standards
**AGI Orchestrator**: Execute multi-phase AGI workflows with meta-learning

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

## Node-Specific Quick References

**For Linux nodes (macpro51)**, see `SYSTEM-CATALOG.md` for:
- Port management and firewall configuration
- RAID10 status and management
- Systemd service administration
- Builder API endpoints and usage
- Network discovery and mDNS setup
- Docker/Podman container management
