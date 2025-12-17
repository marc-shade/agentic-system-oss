# MCP Ecosystem Overview

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Part of Agentic System](https://img.shields.io/badge/Part_of-Agentic_System-brightgreen)](https://github.com/marc-shade/agentic-system-oss)

The Agentic System is built on a comprehensive ecosystem of **26+ MCP (Model Context Protocol) servers** that provide specialized capabilities for AI agents. This document catalogs all available MCP servers organized by function.

## Ecosystem Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Ecosystem                          │
├─────────────────────────────────────────────────────────────────┤
│  Core AGI Infrastructure (Essential)                             │
│  ├─ enhanced-memory-mcp    : 4-tier persistent memory           │
│  ├─ agent-runtime-mcp      : Task orchestration & relay pipes   │
│  ├─ agi-mcp                : Full AGI with 21 tools             │
│  └─ safla-mcp              : High-speed embeddings (1.75M ops)  │
├─────────────────────────────────────────────────────────────────┤
│  Cluster Coordination                                            │
│  ├─ cluster-execution-mcp  : Distributed task routing           │
│  ├─ node-chat-mcp          : Inter-node AI communication        │
│  ├─ claude-flow-mcp        : Multi-agent swarm orchestration    │
│  └─ code-execution-mcp     : Sandboxed code execution           │
├─────────────────────────────────────────────────────────────────┤
│  Knowledge Acquisition                                           │
│  ├─ research-paper-mcp     : arXiv/Semantic Scholar papers      │
│  ├─ video-transcript-mcp   : YouTube transcript extraction      │
│  └─ llm-council-mcp        : Multi-LLM deliberation             │
├─────────────────────────────────────────────────────────────────┤
│  Security & Defense                                              │
│  ├─ security-scanner-mcp   : Nuclei vulnerability scanning      │
│  ├─ security-auditor-mcp   : Policy enforcement & auditing      │
│  ├─ threat-intel-mcp       : Threat intelligence aggregation    │
│  ├─ web-vuln-scanner-mcp   : Web application security testing   │
│  ├─ network-scanner-mcp    : Network discovery & port scanning  │
│  ├─ hids-mcp               : Host-based intrusion detection     │
│  ├─ dos-detector-mcp       : DoS attack detection               │
│  └─ fraud-detection-mcp    : Anomaly & fraud analysis           │
├─────────────────────────────────────────────────────────────────┤
│  Creative & Media                                                │
│  ├─ image-gen-mcp          : Multi-provider image generation    │
│  └─ voice-agi-mcp          : Stateful voice-controlled AGI      │
├─────────────────────────────────────────────────────────────────┤
│  Hardware & Edge                                                 │
│  ├─ coral-tpu-mcp          : Google Coral TPU edge inference    │
│  └─ arduino-surface (*)    : Physical I/O interface             │
├─────────────────────────────────────────────────────────────────┤
│  Development & Analysis                                          │
│  ├─ file-analyzer-mcp      : Deep file & malware analysis       │
│  ├─ crypto-tools-mcp       : Cryptographic utilities            │
│  ├─ synthetic-data-mcp     : Training data generation           │
│  ├─ claude-code-control-mcp: Claude Code automation             │
│  └─ ember-mcp              : Quality & policy enforcement       │
└─────────────────────────────────────────────────────────────────┘
(*) Private - not open-sourced
```

## Core AGI Infrastructure

Essential servers that form the foundation of the autonomous AGI system.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [enhanced-memory-mcp](https://github.com/marc-shade/enhanced-memory-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/enhanced-memory-mcp) | 4-tier persistent memory | Working, episodic, semantic, procedural memory; auto-curation; git-like versioning |
| [agent-runtime-mcp](https://github.com/marc-shade/agent-runtime-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/agent-runtime-mcp) | Persistent task management | Goal decomposition; relay race pipelines; circuit breakers; cross-session persistence |
| [agi-mcp](https://github.com/marc-shade/agi-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/agi-mcp) | Full AGI orchestration | 21 tools; meta-learning; skill evolution; Darwin Gödel self-improvement |
| [safla-mcp](https://github.com/marc-shade/safla-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/safla-mcp) | High-performance embeddings | 1.75M+ ops/sec; hybrid memory; pattern detection |

## Cluster Coordination

Servers enabling distributed multi-node operation across the cluster.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [cluster-execution-mcp](https://github.com/marc-shade/cluster-execution-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/cluster-execution-mcp) | Distributed task routing | Auto-routing by OS/arch; parallel execution; SSH orchestration |
| [node-chat-mcp](https://github.com/marc-shade/node-chat-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/node-chat-mcp) | Inter-node communication | Agent-to-agent messaging; persona awareness; cluster coordination |
| [claude-flow-mcp](https://github.com/marc-shade/claude-flow-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/claude-flow-mcp) | Swarm orchestration | Multi-agent workflows; task decomposition; workflow management |
| [code-execution-mcp](https://github.com/marc-shade/code-execution-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/code-execution-mcp) | Sandboxed execution | Secure code execution; Python/shell sandboxing; result capture |

## Knowledge Acquisition

Servers for autonomous learning from external sources.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [research-paper-mcp](https://github.com/marc-shade/research-paper-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/research-paper-mcp) | Academic paper search | arXiv integration; Semantic Scholar; citation analysis |
| [video-transcript-mcp](https://github.com/marc-shade/video-transcript-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/video-transcript-mcp) | Video learning | YouTube transcripts; concept extraction; methodology mining |
| [llm-council-mcp](https://github.com/marc-shade/llm-council-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/llm-council-mcp) | Multi-LLM deliberation | Claude, GPT, Gemini council; consensus building; debate patterns |

## Security & Defense

Comprehensive security monitoring and vulnerability assessment.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [security-scanner-mcp](https://github.com/marc-shade/security-scanner-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/security-scanner-mcp) | Vulnerability scanning | Nuclei integration; cluster-wide scans; scheduled assessments |
| [security-auditor-mcp](https://github.com/marc-shade/security-auditor-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/security-auditor-mcp) | Policy enforcement | Compliance auditing; policy validation; security reviews |
| [threat-intel-mcp](https://github.com/marc-shade/threat-intel-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/threat-intel-mcp) | Threat intelligence | Multi-source aggregation; IOC tracking; threat feeds |
| [web-vuln-scanner-mcp](https://github.com/marc-shade/web-vuln-scanner-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/web-vuln-scanner-mcp) | Web security testing | OWASP coverage; automated scanning; report generation |
| [network-scanner-mcp](https://github.com/marc-shade/network-scanner-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/network-scanner-mcp) | Network discovery | Port scanning; service detection; infrastructure mapping |
| [hids-mcp](https://github.com/marc-shade/hids-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/hids-mcp) | Intrusion detection | Host monitoring; file integrity; anomaly detection |
| [dos-detector-mcp](https://github.com/marc-shade/dos-detector-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/dos-detector-mcp) | DoS detection | Attack pattern recognition; traffic analysis; mitigation triggers |
| [fraud-detection-mcp](https://github.com/marc-shade/fraud-detection-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/fraud-detection-mcp) | Fraud analysis | Anomaly detection; pattern matching; financial security |

## Creative & Media

Content generation and voice interaction capabilities.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [image-gen-mcp](https://github.com/marc-shade/image-gen-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/image-gen-mcp) | Image generation | 5 providers (Pollinations FREE); pixel art; auto-fallback |
| [voice-agi-mcp](https://github.com/marc-shade/voice-agi-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/voice-agi-mcp) | Voice-controlled AGI | Local STT/TTS; Letta-style memory; tool execution via speech |

## Hardware & Edge

Edge computing and physical hardware integration.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [coral-tpu-mcp](https://github.com/marc-shade/coral-tpu-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/coral-tpu-mcp) | Coral TPU inference | Edge ML; low-latency inference; TensorFlow Lite models |

## Development & Analysis

Development utilities and code analysis tools.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [ember-mcp](https://github.com/marc-shade/ember-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/ember-mcp) | Quality enforcement | Production-only policy; code quality guardian; learning system |
| [file-analyzer-mcp](https://github.com/marc-shade/file-analyzer-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/file-analyzer-mcp) | File analysis | Deep inspection; malware detection; format identification |
| [crypto-tools-mcp](https://github.com/marc-shade/crypto-tools-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/crypto-tools-mcp) | Cryptographic utilities | Encryption; hashing; secure data handling |
| [synthetic-data-mcp](https://github.com/marc-shade/synthetic-data-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/synthetic-data-mcp) | Data generation | Training data; test fixtures; realistic synthetic data |
| [claude-code-control-mcp](https://github.com/marc-shade/claude-code-control-mcp) | ![Stars](https://img.shields.io/github/stars/marc-shade/claude-code-control-mcp) | Claude Code automation | Workflow control; session management; automated tasks |

## Related Projects

### Ollama Workbench

Full-featured desktop applications for AI development:

| Project | Stars | Description |
|---------|-------|-------------|
| [Ollama-Workbench-2](https://github.com/marc-shade/Ollama-Workbench-2) | ![Stars](https://img.shields.io/github/stars/marc-shade/Ollama-Workbench-2) | **v2.0 - SvelteKit + Tauri** native desktop app with MCP Studio, visual workflow builder, and tools debugger |
| [Ollama-Workbench](https://github.com/marc-shade/Ollama-Workbench) | ![Stars](https://img.shields.io/github/stars/marc-shade/Ollama-Workbench) | v1.x - Python/Streamlit desktop app (legacy) |

### Multi-Agent Frameworks

| Project | Stars | Description |
|---------|-------|-------------|
| [TeamForgeAI](https://github.com/marc-shade/TeamForgeAI) | ![Stars](https://img.shields.io/github/stars/marc-shade/TeamForgeAI) | AutoGen-based multi-agent collaboration framework |

## Installation

### Quick Start (All Core Servers)

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system-oss/master/bootstrap.sh | bash
```

### Individual Server Installation

Each MCP server can be installed independently:

```bash
# Clone the desired server
git clone https://github.com/marc-shade/{server-name}

# Install dependencies
cd {server-name}
pip install -r requirements.txt  # or npm install for TypeScript servers

# Add to ~/.claude.json
```

### Claude Code Configuration Example

```json
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["/path/to/enhanced-memory-mcp/server.py"]
    },
    "agent-runtime": {
      "command": "python3",
      "args": ["/path/to/agent-runtime-mcp/server.py"]
    },
    "agi-mcp": {
      "command": "python3",
      "args": ["/path/to/agi-mcp/server.py"]
    }
  }
}
```

## Recommended Server Combinations

### Minimal AGI Setup
- enhanced-memory-mcp
- agent-runtime-mcp
- sequential-thinking (Anthropic)

### Full AGI System
- All Core AGI Infrastructure servers
- node-chat-mcp (for multi-agent coordination)
- llm-council-mcp (for multi-provider deliberation)

### Security Operations
- security-scanner-mcp
- threat-intel-mcp
- network-scanner-mcp
- hids-mcp

### Research & Learning
- research-paper-mcp
- video-transcript-mcp
- enhanced-memory-mcp (for knowledge storage)

## Contributing

Each MCP server accepts contributions independently. See the CONTRIBUTING.md in each repository for guidelines.

## License

All MCP servers in this ecosystem are MIT licensed unless otherwise noted.

---

**Total: 26+ MCP Servers** | **Combined Tools: 100+** | **Part of the [Agentic System](https://github.com/marc-shade/agentic-system-oss)**
