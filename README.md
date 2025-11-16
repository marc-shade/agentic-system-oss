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
