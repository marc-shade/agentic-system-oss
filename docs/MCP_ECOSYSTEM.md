# MCP Ecosystem Overview

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Part of Agentic System](https://img.shields.io/badge/Part_of-Agentic_System-brightgreen)](https://github.com/marc-shade/agentic-system-oss)

The Agentic System is built on a comprehensive ecosystem of **28+ MCP (Model Context Protocol) servers** that provide specialized capabilities for AI agents. This document catalogs all available MCP servers organized by function.

## Ecosystem Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Ecosystem                          │
├─────────────────────────────────────────────────────────────────┤
│  Context Optimization (97% Token Reduction)                      │
│  ├─ phoenix-cortex-mcp     : Intelligent context sidecar        │
│  └─ context-engine-mcp     : Tool-RAG semantic search           │
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
│  Security & Defense (9 servers - all included in this repo)      │
│  ├─ threat-intel-mcp       : Threat intelligence aggregation    │
│  ├─ security-scanner-mcp   : Nuclei vulnerability scanning      │
│  ├─ network-scanner-mcp    : Network discovery & port scanning  │
│  ├─ hids-mcp               : Host-based intrusion detection     │
│  ├─ dos-detector-mcp       : DoS attack detection               │
│  ├─ nuclei-mcp             : Nuclei template management         │
│  ├─ web-vuln-scanner-mcp   : Web application security testing   │
│  ├─ fraud-detection-mcp    : Anomaly & fraud analysis           │
│  └─ security-auditor-mcp   : Policy enforcement & auditing      │
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

## Context Optimization

Servers that dramatically reduce token usage while improving performance.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [phoenix-cortex-mcp](../mcp-servers/phoenix-cortex-mcp) | NEW | Intelligent context sidecar | 97% token reduction; progressive disclosure; tool chains; working memory |
| [context-engine-mcp](../mcp-servers/context-engine-mcp) | NEW | Tool-RAG semantic search | 94.8% reduction; semantic tool discovery; usage pattern learning |

### Token Reduction Comparison

| Scenario | Without Optimization | With Phoenix Cortex | Reduction |
|----------|---------------------|---------------------|-----------|
| Tool Loading | 193,000 tokens | ~2,000 tokens | 99% |
| Result Returns | 50,000 tokens | ~500 tokens | 99% |
| Context Refresh | Full reload | Incremental | 95% |
| **Average Session** | ~250,000 | ~8,000 | **97%** |

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

Comprehensive security monitoring and vulnerability assessment. All 9 security servers are **included in this repository** under `mcp-servers/`.

See [SECURITY.md](SECURITY.md) for the full security architecture documentation.

| Server | Stars | Description | Key Features |
|--------|-------|-------------|--------------|
| [threat-intel-mcp](../mcp-servers/threat-intel-mcp) | Included | Threat intelligence aggregation | abuse.ch, CISA KEV, Feodo feeds; IOC lookup; threat scoring; bulk analysis |
| [security-scanner-mcp](../mcp-servers/security-scanner-mcp) | Included | Nuclei vulnerability scanning | Embedding-based anomaly detection; cluster-wide scans; priority scoring |
| [network-scanner-mcp](../mcp-servers/network-scanner-mcp) | Included | Network discovery & monitoring | ARP scanning; port scanning; service fingerprinting; alert daemon |
| [hids-mcp](../mcp-servers/hids-mcp) | Included | Host-based intrusion detection | File integrity monitoring; process monitoring; anomaly detection |
| [dos-detector-mcp](../mcp-servers/dos-detector-mcp) | Included | DoS attack detection | Traffic analysis; SYN/HTTP flood detection; rate limiting |
| [nuclei-mcp](../mcp-servers/nuclei-mcp) | Included | Nuclei template management | Template listing; updates; scan orchestration |
| [web-vuln-scanner-mcp](../mcp-servers/web-vuln-scanner-mcp) | Included | Web application security testing | OWASP coverage; automated scanning; report generation |
| [fraud-detection-mcp](../mcp-servers/fraud-detection-mcp) | Included | Fraud & anomaly analysis | 46-feature engineering; GNN detection; SHAP explainability; async inference |
| [security-auditor-mcp](../mcp-servers/security-auditor-mcp) | Included | Security policy enforcement | Compliance auditing; policy validation; code review |

### Security Server Configuration Example

```json
{
  "mcpServers": {
    "threat-intel": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/threat-intel-mcp/server.py"]
    },
    "security-scanner": {
      "command": "python3",
      "args": ["-m", "security_scanner.server"],
      "cwd": "/path/to/mcp-servers/security-scanner-mcp/src"
    },
    "network-scanner": {
      "command": "python3",
      "args": ["-m", "network_scanner_mcp.server"],
      "cwd": "/path/to/mcp-servers/network-scanner-mcp/src"
    },
    "security-auditor": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/security-auditor-mcp/server.py"]
    }
  }
}
```

### Encryption & PKI

For data-at-rest encryption, X.509 PKI, and token vault capabilities, see [claude-code-security](https://github.com/marc-shade/claude-code-security). This is maintained as a separate repository for focused auditability.

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
- threat-intel-mcp (threat awareness)
- security-scanner-mcp (vulnerability scanning)
- network-scanner-mcp (network monitoring)
- hids-mcp (host monitoring)
- dos-detector-mcp (attack detection)
- fraud-detection-mcp (anomaly analysis)
- security-auditor-mcp (compliance)

### Research & Learning
- research-paper-mcp
- video-transcript-mcp
- enhanced-memory-mcp (for knowledge storage)

## Contributing

Each MCP server accepts contributions independently. See the CONTRIBUTING.md in each repository for guidelines.

## License

All MCP servers in this ecosystem are MIT licensed unless otherwise noted.

---

**Total: 28+ MCP Servers** | **Combined Tools: 120+** | **Part of the [Agentic System](https://github.com/marc-shade/agentic-system-oss)**
