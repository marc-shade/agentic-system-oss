# Enhanced Memory MCP Server - OSS Edition

A 4-tier memory system for AI agents, implementing cognitive-inspired memory architecture.

## Memory Tiers

| Tier | Purpose | Retention | Access Pattern |
|------|---------|-----------|----------------|
| **Working** | Active context | Minutes (TTL-based) | High frequency r/w |
| **Episodic** | Experiences | Hours-Days | Time-bound recall |
| **Semantic** | Concepts | Permanent | Abstracted knowledge |
| **Procedural** | Skills | Permanent | Executable procedures |

## Performance Targets

These are the benchmarks external verifiers should expect:

| Operation | Target | Tolerance |
|-----------|--------|-----------|
| Entity Creation | 435 ops/s | ±20% |
| Semantic Search | 81 ops/s | ±20% |
| Tier Promotion | 6.4 ops/s | ±20% |

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test the server
python3 server.py
```

## Claude Code CLI Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/enhanced-memory-mcp/server.py"]
    }
  }
}
```

## Available Tools

### Core Memory
- `create_entities` - Create memory entities with auto-tiering
- `search_nodes` - Search across all memory
- `get_memory_status` - System statistics

### Working Memory (Volatile)
- `add_to_working_memory` - Add TTL-based items
- `get_working_memory` - Retrieve active context

### Episodic Memory (Experiences)
- `add_episode` - Record experiences
- `get_episodes` - Recall by type/significance

### Semantic Memory (Concepts)
- `add_concept` - Store learned knowledge
- `get_concepts` - Query abstract concepts

### Procedural Memory (Skills)
- `add_skill` - Register executable procedures
- `record_skill_execution` - Track skill performance
- `get_skills` - List available skills

### Consolidation
- `autonomous_memory_curation` - Run tier promotions

### Versioning
- `memory_diff` - Compare entity versions

## Architecture

```
┌─────────────────────────────────────────┐
│           Claude Code CLI               │
├─────────────────────────────────────────┤
│        MCP Protocol (stdio)             │
├─────────────────────────────────────────┤
│     Enhanced Memory MCP Server          │
├─────────────────────────────────────────┤
│            SQLite Backend               │
│  ┌─────────┬─────────┬─────────────┐   │
│  │ Working │Episodic │  Semantic   │   │
│  │ Memory  │ Memory  │   Memory    │   │
│  └─────────┴─────────┴─────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │      Procedural Memory          │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## License

MIT License - See LICENSE file in repository root.
