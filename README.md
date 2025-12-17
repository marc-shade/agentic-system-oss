# Agentic System - Open Source Verification Kit

[![AVIR Verified](https://img.shields.io/badge/AVIR-VERIFIED-brightgreen)](docs/AVIR.md)
[![Open for Verification](https://img.shields.io/badge/Verification-Open-blue)](VERIFICATION.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **24/7 autonomous agentic AI system** with persistent memory, multi-agent coordination, and self-improvement capabilities.

This repository contains the **verification kit** for independent researchers to replicate and verify the system's capabilities.

## What This Repository Contains

| Component | Description |
|-----------|-------------|
| `bootstrap.sh` | One-command installation script |
| `avir/` | AI-Verified Independent Replication protocol |
| `benchmarks/` | Standardized benchmark specifications |
| `docs/` | Architecture documentation |

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

- **OS**: macOS 14+ or Linux (Ubuntu 22.04+, Fedora 38+)
- **RAM**: 16GB minimum (32GB recommended)
- **Storage**: 50GB free space
- **Container Runtime**: Docker, Podman, or Apple Container
- **Python**: 3.11+

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
- [MCP Server Guide](docs/MCP_SERVERS.md)
- [Workflow Configuration](docs/WORKFLOWS.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

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
