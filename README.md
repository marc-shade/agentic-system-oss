# Agentic System

**24/7 Autonomous Agentic AI System - Distributed Multi-Node Infrastructure**

[![Status](https://img.shields.io/badge/Status-Operational-brightgreen)]()
[![Test Coverage](https://img.shields.io/badge/Tests-7%2F7%20Passing-success)]()
[![Nodes](https://img.shields.io/badge/Active%20Nodes-3-blue)]()
[![License](https://img.shields.io/badge/License-MIT-blue)]()
[![AVIR Verified](https://img.shields.io/badge/AVIR-VERIFIED-brightgreen)]()
[![Open for Verification](https://img.shields.io/badge/Verification-Open-blue)]()

## Overview

A production-ready distributed AI system running 24/7 across multiple nodes with automatic workload distribution, cluster memory, and intelligent task routing.

---

## Independent Verification

**We invite researchers to verify this system's capabilities.**

### One-Command Installation
```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/master/bootstrap-open-source.sh | bash
```

### Verification Options

| Method | Time | What You Verify |
|--------|------|-----------------|
| **[AVIR Protocol](avir/PROTOCOL.md)** | ~1 hour | AI-based cryptographic verification using Codex/Gemini |
| **[Full Replication](avir/RESEARCHER_INVITATION.md)** | 1-2 days | Complete system replication and benchmarking |
| **Component Testing** | 2-4 hours | Individual capability verification |

### AVIR Verification (AI-Verified Independent Replication)
```bash
# Run AI-based verification with different provider
python3 avir/run_verification.py --provider codex
```

**Latest AVIR Results** (2025-12-17):
- Verdict: **VERIFIED** (5/5 benchmarks passed)
- Attestation: `13cf71841710554f3dfa6ddbaa4cb372006efdc167e44876c6f6fa1f3cdc438d`

### Research Paper
See [`research-paper/PAPER.md`](research-paper/PAPER.md) for complete system documentation.

### Submit Verification
- **GitHub Issue**: Use "Verification Report" template
- **Email**: verification@2acrestudios.com

---

## Quick Start

### For New Nodes (Onboarding)

```bash
# Clone and run Claude Code onboarding
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system
./onboard-with-claude.sh
```

Claude Code will guide you through setup via voice, installing infrastructure (Ollama, Temporal, AutoKitteh, Qdrant) and configuring MCP servers.

**Manual setup**: See `cluster-deployment/CROSS_NETWORK_DEPLOYMENT_GUIDE.md`

### For Existing Nodes

```bash
# Run AGI demo
python3 demo_agi_workflow.py

# Check cluster status
python3 cluster-deployment/distributed_task_router.py cluster-status

# Distributed task execution
from cluster_offload import offload
result = offload("make build && make test")
```

## Key Features

### Distributed Task Execution
**Status**: ✅ FULLY OPERATIONAL - 7/7 tests passed

- **Automatic routing** - Tasks route to optimal nodes based on OS, architecture, and capabilities
- **Aggressive offloading** - Keeps active node free (100% offload rate achieved)
- **Smart distribution** - Linux → macpro51, macOS → Mac Studio/MacBook Air
- **Simple API** - One-line task submission
- **Parallel execution** - Distribute work across cluster

```python
from cluster_offload import offload, offload_many

# Simple offload - automatic routing
result = offload("echo 'Hello' && hostname")

# Linux-specific task
result = offload("make build", requires_os="linux")

# Parallel execution
results = offload_many(["python3 test_1.py", "python3 test_2.py", "python3 test_3.py"])
```

### AGI Orchestrator (6-Phase Workflow)
- Goal Decomposition → Context Synthesis → Multi-Agent Coordination → Meta-Learning → Skill Evolution → Darwin Gödel
- Self-improving through meta-learning
- Entry point: `from agi_orchestrator import AGIOrchestrator`

### Cluster Memory System
- Shared memory across all nodes
- Personal and cluster-wide scopes
- Node attribution and automatic synchronization

## Architecture

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

## Test Results

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

## Repository Structure

```
agentic-system/
├── cluster-deployment/          # Multi-node deployment tools
├── monitoring/                  # Prometheus, Loki, Grafana
├── mcp-servers/                 # MCP protocol servers
│   ├── enhanced-memory-mcp/     # 4-tier memory with RAG
│   ├── agent-runtime-mcp/       # Persistent task management
│   └── ...
├── intelligent-agents/          # AI-powered agents
├── workflows/                   # Temporal & AutoKitteh workflows
├── services/                    # System services
└── databases/                   # Persistent data
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete system documentation for Claude Code
- **[QUICK_START.md](QUICK_START.md)** - AGI system usage examples
- **[Distributed Execution Guide](cluster-deployment/DISTRIBUTED_EXECUTION.md)** - Task routing guide
- **[Architecture & Design](cluster-deployment/WORKLOAD_DISTRIBUTION_DESIGN.md)** - System architecture

## System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Distributed Execution | ✅ Operational | 7/7 tests passing |
| SSH Mesh | ✅ Operational | 6/6 routes working |
| Service Discovery | ✅ Operational | Avahi/mDNS active |
| Builder API | ✅ Operational | Port 9000 accessible |
| Monitoring Stack | ✅ Operational | Prometheus + Grafana |
| Cluster Memory | ✅ Operational | All nodes deployed |

## Security

- ED25519 SSH key authentication
- Passwordless SSH mesh
- Firewall configured (Linux nodes)
- No hardcoded credentials
- GitHub PAT authentication for cross-network communication

## License

MIT License - See LICENSE file for details

---

**Generated with Claude Code**

For detailed usage, see [CLAUDE.md](CLAUDE.md) or run `python3 demo_agi_workflow.py`.
