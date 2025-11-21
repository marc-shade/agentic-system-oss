<<<<<<< HEAD
# Agentic System - Cross-Network Cluster Onboarding

**24/7 Autonomous Agentic System - Complete Self-Onboarding for Multiple Platforms**

## 🚀 Claude Code Orchestrated Onboarding (Recommended)

This repository contains **everything** needed to join the agentic cluster network. The onboarding process is orchestrated by Claude Code, which will guide you through authentication and setup via voice interaction.

### AI-Assisted Setup (Claude Code Required)

```bash
# 1. Clone the repository
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system

# 2. Start Claude Code onboarding (if Claude Code is installed)
chmod +x onboard-with-claude.sh
./onboard-with-claude.sh
```

**Claude Code will**:
- 🎤 Communicate with you via voice
- 🔍 Check which platforms you have installed
- 🤖 **Automatically install** missing infrastructure (Ollama, Temporal, AutoKitteh, Qdrant)
- 📋 Guide you through manual installations if needed (OpenAI Codex, Gemini CLI)
- 🔐 Walk you through authentication for each platform
- ⚙️ Configure MCP servers across all platforms automatically
- ✅ Verify everything is working

**You will**:
- Follow Claude Code's voice instructions
- Install any missing platforms when prompted
- Complete OAuth flows or provide API keys
- Confirm when steps are done

### System Requirements

Your system needs multiple components. Claude Code will **automatically install** most of them:

**AI Platforms** (Primary orchestrators):
- ✅ **Claude Code** - Primary orchestrator (must be installed first)
- ✅ **Ollama** - Local LLM server (auto-installed)
- ⚠️ **OpenAI Codex** - OpenAI's code assistant (optional, manual)
- ⚠️ **Gemini CLI** - Google's AI (auto-installed if npm available)

**Infrastructure** (Auto-installed by Claude Code):
- ✅ **Qdrant** - Vector database for memory
- ✅ **Temporal** - Workflow engine
- ✅ **AutoKitteh** - Event-driven workflows
- ✅ **Monitoring** - Prometheus, Loki, Grafana (optional)

**📖 Complete Requirements**: See `SYSTEM_REQUIREMENTS.md` for detailed component list and installation methods

### Prerequisites

**Required**:
- **Python 3.10+** - [Download](https://www.python.org/)
- **Git** - [Download](https://git-scm.com/)
- **GitHub Account** - [Sign up](https://github.com/join)
- **GitHub Personal Access Token** - [Create one](https://github.com/settings/tokens/new)
  - Scopes: `repo`, `read:org`, `workflow`

**AI Platforms** (all required):
- **Claude Code** - [Download](https://code.claude.com)
- **Ollama** - [Download](https://ollama.ai/download)
- **OpenAI Codex** - [Installation Guide](https://developers.openai.com/codex/cli/)
- **Gemini CLI** - `npm install -g @google/generative-ai-cli`

**Authentication Credentials**:
- OpenAI API key (for Codex) - [Get one](https://platform.openai.com/api-keys)
- Gemini API key (for Gemini CLI) - [Get one](https://aistudio.google.com/app/apikey)
- OR Google Cloud credentials (for Gemini with ADC)

### Manual Setup (Without Claude Code)

If you don't have Claude Code or prefer manual setup:

1. **Check platform status**:
```bash
./check-platforms.sh
```

2. **Install missing platforms** (follow instructions from check script)

3. **Run traditional bootstrap**:
```bash
./bootstrap.sh  # Interactive authentication setup
```

4. **Configure MCP servers**:
```bash
export NODE_ID="your-node-id"
export CLUSTER_REPO="marc-shade/agentic-cluster-comms"
./configure-all-mcps.sh
```

5. **Start cluster daemon**:
```bash
cd cluster-deployment
export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
./start_daemon.sh
```

For detailed manual setup, see: `cluster-deployment/CROSS_NETWORK_DEPLOYMENT_GUIDE.md`

### For Claude Code (Onboarding Guide)

If you are Claude Code orchestrating an onboarding, see: `claude-onboarding-guide.md`

## What's Included

### Bootstrap System
- **`bootstrap.sh`** - Automated setup script with platform detection
- **`requirements.txt`** - All Python dependencies
- **`config-templates/`** - Platform-specific configuration templates
  - `claude-code-config.json` - Claude Code MCP configuration
  - `openai-codex-config.json` - OpenAI Codex MCP configuration
  - `gemini-cli-config.json` - Gemini CLI MCP configuration

### MCP Servers (`mcp-servers/`)
- **`enhanced-memory-mcp/`** - 4-tier memory architecture with RAG
- **`agent-runtime-mcp/`** - Persistent task and goal management
- Installation scripts for automated setup
- See `mcp-servers/README.md` for details

### Cluster Deployment (`cluster-deployment/`)

**Core Daemon**:
- `github_node_daemon.py` - Background daemon for task execution
- `submit_cluster_task.py` - Helper for submitting tasks
- `check_daemon_status.sh` - Monitoring script
- `start_daemon.sh` - Daemon startup script

**Documentation**:
- `CROSS_NETWORK_DEPLOYMENT_GUIDE.md` - Complete deployment guide
- `DEPLOYMENT_COMPLETE.md` - Status and next steps
- `SYSTEM_OPERATIONAL.md` - Live system status

**Features**:
- Cross-network communication (no VPN required)
- GitHub as secure message broker
- Task execution (health checks, code execution, node cloning)
- Complete audit trail via git history
- Multi-platform support (Claude Code, OpenAI Codex, Gemini CLI)

## Architecture

```
GitHub (Message Broker)
marc-shade/agentic-cluster-comms
  ├── tasks/{node-id}     ← Incoming tasks
  ├── results/{node-id}   ← Execution results
  └── heartbeat/          ← Node health

Your Node
  ├── Daemon (polls GitHub every 30s)
  ├── Task execution
  └── Result submission
```

## Security

- HTTPS transport (GitHub infrastructure)
- Private repository access only
- GitHub PAT authentication
- Complete git history for audit trail
- Rate limiting via GitHub API

## Communication

- Round-trip latency: ~60-120 seconds
- Poll interval: 30 seconds (configurable)
- GitHub API rate limit: 5000 req/hour
- Task types: health_check, code_execution, clone_node, custom

## Support

- Issues: https://github.com/marc-shade/agentic-system/issues
- Documentation: See `cluster-deployment/` directory
- Main repo: https://github.com/marc-shade/agentic-system

## License

Private - Authorized collaborators only
=======
# Agentic System

**24/7 Autonomous Agentic AI System - Distributed Multi-Node Infrastructure**

[![Status](https://img.shields.io/badge/Status-Operational-brightgreen)]()
[![Test Coverage](https://img.shields.io/badge/Tests-7%2F7%20Passing-success)]()
[![Nodes](https://img.shields.io/badge/Active%20Nodes-3-blue)]()
[![License](https://img.shields.io/badge/License-MIT-blue)]()

## Overview

A production-ready distributed AI system running 24/7 across multiple nodes with automatic workload distribution, cluster memory, and intelligent task routing.

## 🚀 Key Features

### Distributed Task Execution (NEW!)
**Status**: ✅ FULLY OPERATIONAL - 7/7 tests passed

- **Automatic routing** - Tasks route to optimal nodes based on OS, architecture, and capabilities
- **Aggressive offloading** - Keeps active node free (100% offload rate achieved)
- **Smart distribution** - Linux → macpro51, macOS → Mac Studio/MacBook Air
- **Simple API** - One-line task submission
- **Parallel execution** - Distribute work across cluster

```python
from cluster_offload import offload

# Just submit - automatic routing!
result = offload("make build && make test")
print(f"Executed on: {result['assigned_to']}")
```

### Cluster Memory System
- Shared memory across all nodes
- Personal and cluster-wide scopes
- Node attribution
- Automatic synchronization

### Multi-Node Architecture
- **macpro51** (Linux Builder) - x86_64, compilation, testing, containerization
- **mac-studio** (Orchestrator) - ARM64, coordination, monitoring
- **macbook-air** (Researcher) - ARM64, analysis, documentation

## 📊 Test Results

```
✓ Simple Offload
✓ Linux Routing (100% accuracy to macpro51)
✓ macOS Routing (100% accuracy to Mac nodes)
✓ Parallel Execution (5/5 tasks completed)
✓ Capability Routing (docker → macpro51)
✓ Aggressive Offloading (0 local, 10 remote tasks)
✓ Cluster Status

TOTAL: 7/7 tests passed ✅
```

## 🏗️ Architecture

### Cluster Nodes

| Node | Type | OS | Arch | Capabilities | Status |
|------|------|----|----|--------------|--------|
| macpro51 | Builder | Linux | x86_64 | docker, podman, compilation | ✅ Operational |
| mac-studio | Orchestrator | macOS | ARM64 | orchestration, coordination | ✅ Operational |
| macbook-air | Researcher | macOS | ARM64 | research, documentation | ✅ Operational |

### Communication

- **SSH Mesh** - Full passwordless connectivity (6/6 routes operational)
- **Service Discovery** - Avahi/mDNS
- **API Access** - Builder API (port 9000), Prometheus (9700), Grafana (9500)
- **Task Queue** - SQLite-based distributed task queue

## 🔧 Quick Start

### Using Distributed Execution

**Python API:**
```python
from cluster_offload import offload, offload_many

# Simple offload
result = offload("echo 'Hello' && hostname")

# Linux-specific task
result = offload("make build", requires_os="linux")

# Parallel execution
results = offload_many([
    "python3 test_1.py",
    "python3 test_2.py",
    "python3 test_3.py"
])
```

**CLI:**
```bash
cd ~/agentic-system/cluster-deployment
python3 distributed_task_router.py submit "hostname"
python3 distributed_task_router.py cluster-status
```

### Running Tests

```bash
cd ~/agentic-system/cluster-deployment
python3 test_distributed_execution.py
```

## 📁 Repository Structure

```
agentic-system/
├── cluster-deployment/          # Multi-node deployment tools
│   ├── distributed_task_router.py
│   ├── cluster_offload.py
│   ├── test_distributed_execution.py
│   ├── DISTRIBUTED_EXECUTION.md
│   └── ...
├── monitoring/                  # Prometheus, Loki, Grafana
├── mcp-servers/                 # MCP protocol servers
│   ├── enhanced-memory-mcp/
│   ├── agent-runtime-mcp/
│   └── ...
├── intelligent-agents/          # AI-powered agents
├── workflows/                   # Temporal & AutoKitteh workflows
├── services/                    # System services
└── databases/                   # Persistent data
```

## 📖 Documentation

- **[Distributed Execution Guide](cluster-deployment/DISTRIBUTED_EXECUTION.md)** - Complete usage guide
- **[Architecture & Design](cluster-deployment/WORKLOAD_DISTRIBUTION_DESIGN.md)** - System architecture
- **[Implementation Summary](DISTRIBUTED_EXECUTION_IMPLEMENTATION.md)** - Implementation details
- **[Cluster Communication Tests](CLUSTER_COMMUNICATION_TEST_REPORT.md)** - Network testing results

## 🎯 Performance Metrics

- **Task Routing**: ~0.5 seconds
- **Remote Execution**: ~1-2 seconds (SSH overhead)
- **Parallel Efficiency**: 5 tasks in 6.8 seconds
- **Offload Rate**: 100% (0 local, 10 remote in testing)

### Aggressive Offloading

The system heavily prioritizes remote execution to keep your active node responsive:

```
Test Results:
Local node (macpro51): 0 tasks
Remote nodes: 10 tasks
Offload rate: 100% ✅
```

## 🛠️ Technology Stack

- **Languages**: Python 3.x
- **Distributed Computing**: SSH mesh, SQLite task queue
- **Monitoring**: Prometheus, Loki, Grafana
- **Workflows**: Temporal, AutoKitteh, n8n
- **Memory**: Enhanced Memory MCP, Agent Runtime MCP
- **Containers**: Docker, Podman (platform-specific)

## 🔐 Security

- ED25519 SSH key authentication
- Passwordless SSH mesh
- Firewall configured (Linux nodes)
- No hardcoded credentials

## 🚦 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Distributed Execution | ✅ Operational | 7/7 tests passing |
| SSH Mesh | ✅ Operational | 6/6 routes working |
| Service Discovery | ✅ Operational | Avahi/mDNS active |
| Builder API | ✅ Operational | Port 9000 accessible |
| Monitoring Stack | ✅ Operational | Prometheus + Grafana |
| Cluster Memory | ⏳ Partial | macbook-air deployed |

## 📈 Roadmap

### Implemented ✅
- [x] Distributed task execution
- [x] Automatic routing based on capabilities
- [x] Aggressive offloading
- [x] Parallel execution
- [x] SSH mesh connectivity
- [x] Comprehensive testing

### Planned 🔜
- [ ] Real-time node load monitoring
- [ ] Dynamic capability discovery
- [ ] Task result caching
- [ ] Health-based failover
- [ ] Web dashboard for visualization
- [ ] Integration with Temporal workflows
- [ ] Task dependencies (DAG execution)

## 🤝 Contributing

This is a personal infrastructure project, but suggestions and issues are welcome!

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built with:
- [Claude Code](https://claude.ai/code) - AI-powered development
- [Temporal](https://temporal.io) - Workflow orchestration
- [Prometheus](https://prometheus.io) - Monitoring
- [Grafana](https://grafana.com) - Visualization

---

**Generated with Claude Code** 🤖

For detailed usage instructions, see the [Distributed Execution Guide](cluster-deployment/DISTRIBUTED_EXECUTION.md).
>>>>>>> origin/main
