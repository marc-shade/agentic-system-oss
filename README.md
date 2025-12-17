# Agentic System - Open Source Edition

[![AVIR Verified](https://img.shields.io/badge/AVIR-VERIFIED-brightgreen)](docs/AVIR.md)
[![Open for Verification](https://img.shields.io/badge/Verification-Open-blue)](VERIFICATION.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<img align="right" width="300" height="300" alt="agentic-system-oss" src="https://github.com/user-attachments/assets/ae76f829-23f2-4ad9-8b41-533c23092d34" />

A **24/7 autonomous agentic AI system** with persistent memory, multi-agent coordination, and self-improvement capabilities.

This repository contains **fully functional MCP servers** and the **verification kit** for independent researchers to install, configure, and verify the system on their own machines.

**What This Repository Contains**

| Component | Description |
|-----------|-------------|
| `mcp-servers/` | **8 Installable MCP servers** for Claude Code CLI |
| `├─ enhanced-memory-mcp/` | 4-tier persistent memory with auto-curation |
| `├─ agent-runtime-mcp/` | Task management, relay pipelines, circuit breakers |
| `├─ safla-mcp/` | High-performance embeddings (1.75M+ ops/sec) |
| `├─ research-paper-mcp/` | arXiv/Semantic Scholar paper search |
| `├─ video-transcript-mcp/` | YouTube transcript extraction |
| `├─ llm-council-mcp/` | Multi-provider LLM deliberation |
| `├─ ember-mcp/` | Quality enforcement and policy guardian |
| `└─ sequential-thinking/` | Reference to deep reasoning MCP |
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

## Quick Start

### One-Command Installation

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system-oss/master/bootstrap.sh | bash
```

Or clone and run:

```bash
git clone https://github.com/marc-shade/agentic-system-oss.git
cd agentic-system-oss
./bootstrap.sh
```

### Requirements

- **Claude Code CLI**: [claude.ai/code](https://claude.ai/code)
- **Python**: 3.10+ (3.11+ recommended)
- **Node.js**: 18+ (optional, for ember-mcp TypeScript server)
- **OS**: macOS 12+ or Linux (Ubuntu 20.04+, Fedora 38+)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 1GB free space

### Optional Services

For enhanced functionality, you can run optional background services:

```bash
# Start optional services (Qdrant vector DB, Redis cache)
./scripts/start-services.sh start all

# Check service status
./scripts/start-services.sh status
```

See [docs/SERVICES.md](docs/SERVICES.md) for detailed service configuration.

### Manual Installation (Alternative)

If you prefer manual setup:

```bash
# Install MCP server dependencies
pip3 install fastmcp

# Add to ~/.claude.json:
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/enhanced-memory-mcp/server.py"]
    },
    "agent-runtime": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/agent-runtime-mcp/server.py"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropics/mcp-server-sequential-thinking"]
    }
  }
}

# Restart Claude Code CLI
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic System                           │
├─────────────────────────────────────────────────────────────┤
│  MCP Servers (Model Context Protocol)                       │
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
```

## Verification

### AVIR Protocol (AI-Verified Independent Replication)

The AVIR protocol enables AI systems to independently verify this system's capabilities:

```bash
cd avir
./run-verification.sh --provider codex  # or gemini
```

**What AVIR Tests:**
1. Memory entity creation speed (target: >400 ops/s)
2. Semantic search performance (target: >75 ops/s)
3. Memory tier promotion (target: >5 ops/s)
4. Task decomposition latency (target: <1500ms)
5. Relay baton handoff (target: <150ms)

### Manual Verification

See [VERIFICATION.md](VERIFICATION.md) for step-by-step manual verification instructions.

### Submit Your Results

After verification, submit your results:
1. Open an issue using the [Verification Report template](.github/ISSUE_TEMPLATE/verification-report.md)
2. Include your attestation hash and benchmark results
3. Community maintains a list of verified replications

## Benchmarks

| Benchmark | Description | Target | Tolerance |
|-----------|-------------|--------|-----------|
| memory_entity_creation | Entities created per second | 435 ops/s | ±20% |
| semantic_search | Search operations per second | 81 ops/s | ±20% |
| memory_promotion | Tier promotions per second | 6.4 ops/s | ±20% |
| task_decomposition | Goal → tasks latency | 1200ms | ±25% |
| baton_handoff | Agent relay latency | 89ms | ±50% |

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [**MCP Ecosystem (26+ servers)**](docs/MCP_ECOSYSTEM.md) - Complete catalog of all MCP servers
- [Services Configuration](docs/SERVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## MCP Ecosystem

This system is built on **26+ MCP servers** organized by function:

| Category | Servers | Highlights |
|----------|---------|------------|
| **Core AGI** | 4 | enhanced-memory, agent-runtime, agi-mcp, safla-mcp |
| **Cluster Coordination** | 4 | cluster-execution, node-chat, claude-flow, code-execution |
| **Knowledge Acquisition** | 3 | research-paper, video-transcript, llm-council |
| **Security & Defense** | 8 | security-scanner, threat-intel, network-scanner, hids, and more |
| **Creative & Media** | 2 | image-gen, voice-agi |
| **Development** | 5 | ember, file-analyzer, crypto-tools, synthetic-data, claude-code-control |

See [docs/MCP_ECOSYSTEM.md](docs/MCP_ECOSYSTEM.md) for the complete server catalog with installation instructions.

## Research Paper

The full research paper documenting this system is available at:
- [research-paper/PAPER.md](research-paper/PAPER.md)

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Citation

If you use this system in your research, please cite:

```bibtex
@software{agentic_system_2025,
  title = {Agentic System: A 24/7 Autonomous AI Framework},
  author = {Shade, Marc},
  year = {2025},
  url = {https://github.com/marc-shade/agentic-system-oss}
}
```

## Acknowledgments

Built with Claude Code by Anthropic and the Model Context Protocol ecosystem.
