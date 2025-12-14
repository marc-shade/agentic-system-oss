# Agentic Marketplace

AGI Development System plugins for Claude Code.

## Quick Start

```bash
# Install the marketplace (team admin)
# Add to .claude/settings.json:
{
  "plugins": {
    "marketplaces": [
      {
        "name": "agentic-marketplace",
        "path": "/path/to/agentic-marketplace"
      }
    ]
  }
}

# Install plugins (all users)
/plugin install agi-core@agentic-marketplace
```

## Available Plugins

### Tier 1: agi-core (Zero Infrastructure)
Core AGI reasoning patterns and specialized agents.

**What's included:**
- 5 specialized agents (deep-thinker, architect, code-reviewer, debugger, researcher)
- 3 commands (agi-init, agi-status, agi-help)
- Behavioral CLAUDE.md with AGI patterns
- Meta-prompting skill

**Install:**
```
/plugin install agi-core@agentic-marketplace
```

### Tier 2: agi-memory (SQLite)
Persistent memory with goals, tasks, and outcome recording.

**What's added:**
- Goal decomposition and task management
- Action outcome storage
- Quality conscience (Ember)
- Memory consolidation

**Requires:** agi-core, Python 3.10+

**Install:**
```
/plugin install agi-memory@agentic-marketplace
```

### Tier 3: agi-extended (Docker)
Full AGI with vector memory, research tools, and voice.

**What's added:**
- Vector-based semantic memory (Qdrant)
- Research paper integration (arXiv, Semantic Scholar)
- Video transcript learning (YouTube)
- Voice interaction
- Self-improvement cycles

**Requires:** agi-core, agi-memory, Docker

**Install:**
```
/plugin install agi-extended@agentic-marketplace
```

### Tier 4: agi-cluster (Multi-Node)
Distributed AGI across compute nodes.

**What's added:**
- Inter-node AI communication
- Distributed task execution
- Swarm intelligence coordination
- Hardware-aware task routing

**Requires:** agi-core, agi-memory, agi-extended, multiple machines

**Install:**
```
/plugin install agi-cluster@agentic-marketplace
```

## Bundles

For convenience, install pre-configured bundles:

| Bundle | Plugins | Use Case |
|--------|---------|----------|
| agi-starter | core + memory | Individual developers |
| agi-full | core + memory + extended | Full single-machine |
| agi-enterprise | all | Distributed teams |

```
/plugin install agi-starter@agentic-marketplace
```

## Configuration

After installation, customize at `~/.claude/agi/config.yaml`:

```yaml
tier: auto  # or: core, memory, extended, cluster

behaviors:
  action_recording:
    enabled: true
  meta_prompting:
    enabled: true

# See config/defaults.yaml for all options
```

## Team Setup

1. **Admin**: Clone marketplace to shared location
2. **Admin**: Add to repository's `.claude/settings.json`
3. **Members**: Trust repository when prompted
4. **Members**: Plugins auto-install

## Support

- **Issues**: https://github.com/your-org/agi-plugins/issues
- **Docs**: https://github.com/your-org/agi-plugins/wiki
- **Discussions**: https://github.com/your-org/agi-plugins/discussions

## License

MIT License - See LICENSE file for details.
