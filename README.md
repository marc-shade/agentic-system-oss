# Agentic System

<div align="center">

**24/7 Autonomous Agentic AI System - Distributed Multi-Node Infrastructure**

[![Status](https://img.shields.io/badge/Status-Operational-brightgreen)]()
[![GAIA Level 1](https://img.shields.io/badge/GAIA%20L1-87.5%25-success)]()
[![GAIA Level 2](https://img.shields.io/badge/GAIA%20L2-80.0%25-success)]()
[![Tests](https://img.shields.io/badge/Tests-7%2F7%20Passing-success)]()
[![Nodes](https://img.shields.io/badge/Active%20Nodes-4-blue)]()
[![License](https://img.shields.io/badge/License-MIT-blue)]()
[![AVIR Verified](https://img.shields.io/badge/AVIR-VERIFIED-brightgreen)]()

</div>

---

## Overview
<img width="300" height="300" align="right" alt="agentic-system-oss" src="https://github.com/user-attachments/assets/ac0ba0df-ec74-4aff-a616-e668420b7018" />
A production-ready distributed AI system running 24/7 across multiple nodes with automatic workload distribution, cluster memory, and intelligent task routing.

| Component | Description |
|-----------|-------------|
| `mcp-servers/` | **19 Installable MCP servers** for Claude Code CLI |
| `├─ enhanced-memory-mcp/` | 4-tier persistent memory with auto-curation |
| `├─ agent-runtime-mcp/` | Task management, relay pipelines, circuit breakers |
| `├─ phoenix-cortex-mcp/` | Intelligent context sidecar (97% token reduction) |
| `├─ context-engine-mcp/` | Tool-RAG semantic search (94.8% reduction) |
| `├─ safla-mcp/` | High-performance embeddings (1.75M+ ops/sec) |
| `├─ research-paper-mcp/` | arXiv/Semantic Scholar paper search |
| `├─ video-transcript-mcp/` | YouTube transcript extraction |
| `├─ llm-council-mcp/` | Multi-provider LLM deliberation |
| `├─ ember-mcp/` | Quality enforcement and policy guardian |
| `├─ sequential-thinking/` | Reference to deep reasoning MCP |
| `├─ threat-intel-mcp/` | Threat intelligence aggregation (IOC feeds) |
| `├─ security-scanner-mcp/` | Nuclei vulnerability scanning |
| `├─ network-scanner-mcp/` | Network discovery and port scanning |
| `├─ hids-mcp/` | Host-based intrusion detection |
| `├─ dos-detector-mcp/` | DoS attack detection |
| `├─ nuclei-mcp/` | Direct Nuclei template management |
| `├─ web-vuln-scanner-mcp/` | Web application security testing |
| `├─ fraud-detection-mcp/` | Anomaly and fraud analysis |
| `└─ security-auditor-mcp/` | Security policy enforcement |
| `claude-config/` | **Claude Code customizations** |
| `├─ agents/` | Specialized sub-agents (7 agents) |
| `├─ commands/` | Slash commands (10 commands) |
| `├─ skills/` | Compositional skills (5 skills) |
| `└─ hooks/` | Pre/post tool execution hooks |
| `scripts/` | Setup and service utilities |
| `avir/` | AI-Verified Independent Replication protocol |
| `benchmarks/` | Standardized benchmark specifications |
| `docs/` | Architecture documentation |
| `bootstrap.sh` | One-command installation script |

### Why Prometheus?

- **Verifiable Results** - Run the benchmarks yourself, see the numbers
- **Open Source** - Full source code, no black box
- **Self-Hosted** - Your data stays on your infrastructure
- **Extensible** - Add your own agents, tools, and workflows

---

## 🚀 Quick Start

### One-Command Installation

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/master/bootstrap-open-source.sh | bash
```

### For Existing Nodes

```bash
# Run AGI demo (~0.5s full workflow)
python3 demo_agi_workflow.py

# Check cluster status
python3 cluster-deployment/distributed_task_router.py cluster-status

# Distributed task execution
from cluster_offload import offload
result = offload("make build && make test")
```

---

## 🔬 Independent Verification

**We invite researchers to verify this system's capabilities.**

| Method | Time | What You Verify |
|--------|------|-----------------|
| **[AVIR Protocol](avir/PROTOCOL.md)** | ~1 hour | AI-based cryptographic verification |
| **[Full Replication](avir/RESEARCHER_INVITATION.md)** | 1-2 days | Complete system benchmarking |
| **Benchmark Suite** | ~5 min | GAIA-comparable performance |

### Latest AVIR Results (2025-12-17)
- **Verdict**: VERIFIED (5/5 benchmarks passed)
- **Attestation**: `13cf71841710554f3dfa6ddbaa4cb372006efdc167e44876c6f6fa1f3cdc438d`

---

## 🏗️ Architecture

### Cluster Nodes

| Node | Role | OS | Capabilities | Status |
|------|------|----|----|--------|
| **mac-studio** | Orchestrator | macOS ARM64 | Coordination, scheduling | ✅ |
| **macbook-air** | Researcher | macOS ARM64 | Analysis, documentation | ✅ |
| **macbook-pro** | Developer | macOS ARM64 | Implementation, testing | ✅ |
| **macpro51** | Builder | Linux x86_64 | Docker, compilation, GPU | ✅ |

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic System                           │
├─────────────────────────────────────────────────────────────┤
│  Security Layer (9 servers + hooks + encryption)           │
│  ├─ threat-intel-mcp     : IOC feeds, threat scoring       │
│  ├─ security-scanner-mcp : Nuclei vulnerability scanning   │
│  ├─ network-scanner-mcp  : ARP discovery, port scanning    │
│  ├─ hids-mcp             : Host intrusion detection        │
│  ├─ dos-detector-mcp     : DoS attack detection            │
│  ├─ web-vuln-scanner-mcp : OWASP web security testing      │
│  ├─ fraud-detection-mcp  : Anomaly & fraud analysis        │
│  ├─ security-auditor-mcp : Policy enforcement & auditing   │
│  └─ Pre/Post hooks       : Injection/credential scanning   │
├─────────────────────────────────────────────────────────────┤
│  Context Optimization Layer (97% token reduction)          │
│  ├─ phoenix-cortex-mcp   : Intelligent context sidecar      │
│  └─ context-engine-mcp   : Tool-RAG semantic search         │
├─────────────────────────────────────────────────────────────┤
│  Core AGI Servers (Model Context Protocol)                  │
│  ├─ enhanced-memory-mcp  : 4-tier persistent memory         │
│  ├─ agent-runtime-mcp    : Task orchestration               │
│  ├─ sequential-thinking  : Chain-of-thought reasoning       │
│  └─ safla-mcp           : High-speed embeddings             │
├─────────────────────────────────────────────────────────────┤
│  Workflow Engines                                           │
│  ├─ Temporal            : Long-running stateful workflows   │
│  └─ AutoKitteh          : Event-driven automation           │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                              │
│  ├─ Qdrant              : Vector database                   │
│  ├─ SQLite              : Structured data                   │
│  └─ Redis               : Cache and queues                  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
    │ Claude  │         │  GPT-4  │         │ Gemini  │
    │ Reasoning│        │  Code   │         │ Vision  │
    └─────────┘         └─────────┘         └─────────┘
         │                    │                    │
    ┌────▼────────────────────▼────────────────────▼────┐
    │              Distributed Execution                 │
    │   mac-studio ←→ macbook-air ←→ macpro51           │
    └───────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
    │ Memory  │         │ Sandbox │         │Hardware │
    │ (Qdrant)│         │(Apple C)│         │(Arduino)│
    └─────────┘         └─────────┘         └─────────┘
```

### Key Technologies

- **Apple Container** - Native macOS sandboxed execution (1.5s cold start)
- **Qdrant** - Vector database for semantic memory
- **Temporal** - Long-running workflow orchestration
- **AutoKitteh** - Event-driven automation
- **LLM Council** - Multi-provider consensus decisions

---

## 📁 Repository Structure

```
agentic-system/
├── intelligent-agents/prometheus/   # Core agent system
│   ├── agents/                      # Specialized agents
│   ├── benchmarks/                  # GAIA-comparable tests
│   └── apple_container.py           # Sandbox integration
├── cluster-deployment/              # Multi-node tools
├── mcp-servers/                     # MCP protocol servers
│   ├── enhanced-memory-mcp/         # 4-tier memory + RAG
│   ├── agent-runtime-mcp/           # Persistent tasks
│   └── voice-mode/                  # TTS/STT
├── monitoring/                      # Prometheus + Grafana
├── workflows/                       # Temporal & AutoKitteh
└── databases/                       # Persistent data
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Complete system documentation |
| [QUICK_START.md](QUICK_START.md) | AGI usage examples |
| [GAP_ANALYSIS.md](intelligent-agents/prometheus/GAP_ANALYSIS.md) | Feature comparison vs Manus |
| [Distributed Execution](cluster-deployment/DISTRIBUTED_EXECUTION.md) | Task routing guide |
| [Research Paper](research-paper/PAPER.md) | Academic documentation |

---

## 🔒 Security

- ED25519 SSH key authentication
- Apple Container sandboxed execution
- Network isolation by default
- No hardcoded credentials
- Firewall configured on all nodes

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [**MCP Ecosystem (28+ servers)**](docs/MCP_ECOSYSTEM.md) - Complete catalog of all MCP servers
- [**Security Architecture**](docs/SECURITY.md) - Layered defense documentation
- [Services Configuration](docs/SERVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## MCP Ecosystem

This system is built on **28+ MCP servers** organized by function:

| Category | Servers | Highlights |
|----------|---------|------------|
| **Context Optimization** | 2 | phoenix-cortex (97% reduction), context-engine (Tool-RAG) |
| **Core AGI** | 4 | enhanced-memory, agent-runtime, agi-mcp, safla-mcp |
| **Cluster Coordination** | 4 | cluster-execution, node-chat, claude-flow, code-execution |
| **Knowledge Acquisition** | 3 | research-paper, video-transcript, llm-council |
| **Security & Defense** | 9 | threat-intel, security-scanner, network-scanner, hids, dos-detector, nuclei, web-vuln-scanner, fraud-detection, security-auditor |
| **Creative & Media** | 2 | image-gen, voice-agi |
| **Development** | 5 | ember, file-analyzer, crypto-tools, synthetic-data, claude-code-control |

See [docs/MCP_ECOSYSTEM.md](docs/MCP_ECOSYSTEM.md) for the complete server catalog with installation instructions.

### Security MCP Servers (Included in This Repo)

| Server | Description | Key Features |
|--------|-------------|--------------|
| `threat-intel-mcp` | Threat intelligence aggregation | Multi-feed IOC tracking (abuse.ch, CISA KEV, Feodo); threat scoring; IP/domain/hash lookup |
| `security-scanner-mcp` | Nuclei vulnerability scanning | Single target and cluster-wide scans; embedding-based anomaly detection; scan history |
| `network-scanner-mcp` | Network discovery and monitoring | ARP scanning; port scanning; service fingerprinting; cluster health monitoring; alert daemon |
| `hids-mcp` | Host-based intrusion detection | File integrity monitoring; anomaly detection; host security assessment |
| `dos-detector-mcp` | DoS attack detection | Traffic pattern analysis; attack recognition; mitigation triggers |
| `nuclei-mcp` | Direct Nuclei template interface | Template management; scan orchestration; result analysis |
| `web-vuln-scanner-mcp` | Web application security testing | OWASP coverage; automated scanning; report generation |
| `fraud-detection-mcp` | Fraud and anomaly analysis | Feature engineering (46 features); GNN fraud detection; SHAP explainability; async inference |
| `security-auditor-mcp` | Security policy enforcement | Compliance auditing; policy validation; security reviews |

## Security Architecture

The system implements defense-in-depth through three layers:

**Layer 1: Hook-Based Runtime Protection** (`claude-config/hooks/`)
- `pre-tool-use.py` validates every tool call before execution: blocks destructive commands, detects SQL/command injection, prevents credential leaks in arguments
- `post-tool-use.py` scans tool output for accidentally exposed secrets, logs all operations for audit trails

**Layer 2: MCP Security Servers** (9 servers listed above)
- Active monitoring: network scanning, intrusion detection, DoS detection
- Vulnerability assessment: Nuclei scanning, web application testing
- Intelligence: threat feed aggregation, IOC correlation
- Analysis: fraud detection with ML models, security policy auditing

**Layer 3: Encryption and PKI** (via [claude-code-security](https://github.com/marc-shade/claude-code-security))
- AES-256-GCM encryption for data at rest
- X.509 PKI for inter-node authentication
- Token vault for secure credential management
- See the linked repository for encryption, PKI, and token vault capabilities

See [docs/SECURITY.md](docs/SECURITY.md) for the full security architecture documentation.

## Research Paper

The full research paper documenting this system is available at:
- [research-paper/PAPER.md](research-paper/PAPER.md)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with Claude Code** | [Documentation](CLAUDE.md) | [Benchmarks](intelligent-agents/prometheus/benchmarks/)

</div>
