# AGI Plugin Architecture for Claude Code

## Executive Summary

This document describes the architecture for packaging our AGI development system as distributable Claude Code plugins. The system uses a 4-tier approach allowing teams to adopt capabilities incrementally based on their infrastructure.

## Current System Inventory

### MCP Servers (18 total)
| Server | Purpose | Infrastructure Needs |
|--------|---------|---------------------|
| enhanced-memory-mcp | Versioned memory with RAG | SQLite + Qdrant |
| agent-runtime-mcp | Goals and task queue | SQLite |
| agi-mcp | Meta-learning, self-improvement | SQLite |
| ember-mcp | Quality conscience keeper | Node.js + SQLite |
| research-paper-mcp | arXiv/Semantic Scholar | Network |
| voice-mode | Speech I/O | Audio hardware |
| voice-agi-mcp | Voice conversations | Audio + STT/TTS |
| video-transcript-mcp | YouTube transcripts | Network |
| node-chat-mcp | Inter-node comms | Multi-node cluster |
| security-scanner-mcp | Nuclei integration | Nuclei installed |
| security-auditor-mcp | Code security analysis | Ollama (remote) |
| claude-flow-mcp | Swarm orchestration | Node.js |
| SAFLA | Self-Aware Framework | Python |
| cluster-execution-mcp | Distributed execution | Multi-node |
| meta-cognition-mcp | Metacognitive tracking | SQLite |
| mcp-tool-router | Tool routing | None |
| claude-code-control-mcp | CLI control | None |

### Intelligent Agents (35+)
- **Core Orchestration**: agi_orchestrator.py, multi_agent_coordinator.py, pattern_aware_coordinator.py
- **Self-Improvement**: darwin_godel_machine.py, autonomous_improvement_daemon.py, auto_implementation_engine.py
- **Learning**: meta_learning_engine.py, knowledge_synthesis_engine.py, skill_evolution_system.py
- **Quality**: quality_gates.py, self_evaluation_system.py, verified_improvement_executor.py
- **Analysis**: llm_code_analyzer.py, rag_code_generator.py, context_synthesis_engine.py
- **Voice**: action_orchestrator.py, intent_classifier.py, conversation_manager.py
- **Monitoring**: capability_monitor.py, scheduled_health_monitor.py, performance_regression_tracker.py
- **Security**: autonomous_security_agent.py, security_auditor.py

### Slash Commands (6)
- `/agi-init` - Initialize AGI session
- `/agi-status` - Show progress/metrics
- `/agi-consolidate` - Memory consolidation
- `/agi-research` - Autonomous research
- `/agi-improve` - Self-improvement cycle
- `/show-transcripts` - View STT transcripts

### Custom Agents (7)
- agi-orchestrator, architect, code-reviewer, debugger, deep-thinker, researcher

### Behavioral Layer (CLAUDE.md)
- Action outcome recording
- Knowledge gap identification
- Meta-prompting workflow
- Similar action checking
- Metacognitive monitoring
- Sequential thinking guidance

---

## Plugin Taxonomy (4 Tiers)

### Tier 1: agi-core (Zero Infrastructure)
**Instant adoption - no servers, databases, or external services**

Components:
```
agi-core/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── agi-init.md
│   ├── agi-status.md
│   └── agi-help.md
├── agents/
│   ├── deep-thinker.agent.md
│   ├── architect.agent.md
│   ├── code-reviewer.agent.md
│   ├── debugger.agent.md
│   └── researcher.agent.md
├── skills/
│   └── meta-prompting.md
├── hooks.json
└── CLAUDE.md  (behavioral instructions)
```

What's included:
- All slash commands (adapted for standalone)
- All agent definitions
- Behavioral CLAUDE.md with AGI patterns
- Meta-prompting skill
- Hooks for action outcome recording (to local file)

What's NOT included:
- MCP servers (no infrastructure)
- Persistent memory across sessions
- Database backends

**Use case**: Individual developers wanting AGI-style reasoning patterns without infrastructure.

---

### Tier 2: agi-memory (Local Runtime)
**Extends agi-core with SQLite-based persistence**

Components:
```
agi-memory/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json           # MCP server configs
├── mcp/
│   ├── agent-runtime/  # Goal/task management
│   └── agi/           # Meta-learning
├── commands/
│   ├── agi-consolidate.md
│   └── agi-goals.md
├── scripts/
│   └── setup-databases.sh
└── config/
    └── defaults.yaml
```

Dependencies:
- **Requires**: agi-core
- **Adds**: SQLite databases, Python 3.10+

MCP Servers included:
- `agent-runtime-mcp` - Goal decomposition, task queues
- `agi-mcp` - Meta-learning, outcome recording
- `ember-mcp` - Quality conscience

What's added:
- Persistent goals and tasks across sessions
- Action outcome storage
- Quality gate enforcement
- Memory consolidation commands

**Use case**: Teams wanting persistent AGI state without Docker/containers.

---

### Tier 3: agi-extended (Docker Services)
**Full semantic memory and research capabilities**

Components:
```
agi-extended/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── mcp/
│   ├── enhanced-memory/   # Vector RAG
│   ├── research-paper/    # arXiv integration
│   ├── video-transcript/  # YouTube learning
│   └── voice-mode/        # Speech I/O
├── docker/
│   ├── docker-compose.yml
│   └── qdrant/
├── commands/
│   ├── agi-research.md
│   ├── agi-improve.md
│   └── agi-learn.md
└── scripts/
    ├── start-services.sh
    └── stop-services.sh
```

Dependencies:
- **Requires**: agi-core, agi-memory
- **Adds**: Docker, Qdrant, optional Redis

MCP Servers included:
- `enhanced-memory-mcp` - Versioned memory, RAG, compression
- `research-paper-mcp` - arXiv, Semantic Scholar
- `video-transcript-mcp` - YouTube transcript extraction
- `voice-mode` - Speech input/output (optional)
- `security-auditor-mcp` - Code security scanning

What's added:
- Vector-based semantic memory
- Episodic/semantic/procedural memory types
- Autonomous research from papers/videos
- Self-improvement cycles
- Voice interaction

**Use case**: Teams wanting full AGI capabilities on single machine.

---

### Tier 4: agi-cluster (Multi-Node)
**Distributed AGI across compute nodes**

Components:
```
agi-cluster/
├── .claude-plugin/
│   └── plugin.json
├── .mcp.json
├── mcp/
│   ├── node-chat/         # Inter-node comms
│   ├── cluster-execution/ # Distributed tasks
│   └── claude-flow/       # Swarm orchestration
├── config/
│   ├── cluster-topology.yaml
│   └── node-profiles.yaml
├── scripts/
│   ├── deploy-to-node.sh
│   ├── cluster-status.sh
│   └── sync-nodes.sh
├── commands/
│   ├── cluster-status.md
│   ├── cluster-deploy.md
│   └── cluster-task.md
└── agents/
    └── agi-orchestrator.agent.md
```

Dependencies:
- **Requires**: agi-core, agi-memory, agi-extended
- **Adds**: SSH access, multiple nodes, shared storage

MCP Servers included:
- `node-chat-mcp` - AI persona-to-persona communication
- `cluster-execution-mcp` - Distributed task execution
- `claude-flow-mcp` - Swarm coordination, neural patterns
- `security-scanner-mcp` - Cluster-wide security scanning

What's added:
- Multi-node task distribution
- Specialized node roles (orchestrator, builder, researcher)
- Inter-node AI communication
- Collective intelligence patterns
- Hardware-aware task routing

**Use case**: Enterprise teams with multiple machines wanting distributed AGI.

---

## Plugin Dependency Graph

```
                    ┌─────────────┐
                    │ agi-cluster │  Tier 4
                    │  (Multi-Node)│
                    └──────┬──────┘
                           │ requires
                    ┌──────▼──────┐
                    │agi-extended │  Tier 3
                    │  (Docker)   │
                    └──────┬──────┘
                           │ requires
                    ┌──────▼──────┐
                    │ agi-memory  │  Tier 2
                    │  (SQLite)   │
                    └──────┬──────┘
                           │ requires
                    ┌──────▼──────┐
                    │  agi-core   │  Tier 1
                    │ (Zero Infra)│
                    └─────────────┘
```

---

## Configuration Schema

### Environment Detection
Plugins automatically detect available infrastructure:

```yaml
# ~/.claude/agi/environment.yaml (auto-generated)
detected:
  docker: true
  qdrant: true
  redis: false
  ollama_remote: "http://192.168.1.186:11434"
  nodes:
    - mac-studio: online
    - macpro51: online
    - macbook-air-m3: offline

active_tier: extended  # Auto-selected based on detection
```

### User Configuration
```yaml
# ~/.claude/agi/config.yaml
tier: auto  # or: core, memory, extended, cluster

memory:
  database_path: ~/.claude/agi/databases
  qdrant_url: http://localhost:6333
  compression_enabled: true

cluster:
  nodes:
    - name: mac-studio
      role: orchestrator
      ssh: marc@192.168.1.79
    - name: macpro51
      role: builder
      ssh: marc@192.168.1.87
  shared_storage: /mnt/agentic-system

safety:
  require_approval_for:
    - self_modification
    - code_execution
    - capability_installation
  autonomous_allowed:
    - memory_consolidation
    - knowledge_research
    - performance_tracking

ollama:
  host: http://192.168.1.186:11434  # Never local CPU
```

---

## Marketplace Structure

### Private Team Marketplace
```
agentic-marketplace/
├── manifest.json
├── plugins/
│   ├── agi-core/
│   │   └── plugin.json
│   ├── agi-memory/
│   │   └── plugin.json
│   ├── agi-extended/
│   │   └── plugin.json
│   └── agi-cluster/
│       └── plugin.json
└── README.md
```

### manifest.json
```json
{
  "name": "agentic-marketplace",
  "version": "1.0.0",
  "description": "AGI Development System plugins for Claude Code",
  "author": "Marc & Team",
  "plugins": [
    {
      "name": "agi-core",
      "version": "1.0.0",
      "description": "Core AGI reasoning patterns and agents",
      "tier": 1
    },
    {
      "name": "agi-memory",
      "version": "1.0.0",
      "description": "Persistent memory with SQLite",
      "tier": 2,
      "requires": ["agi-core"]
    },
    {
      "name": "agi-extended",
      "version": "1.0.0",
      "description": "Full AGI with Docker services",
      "tier": 3,
      "requires": ["agi-core", "agi-memory"]
    },
    {
      "name": "agi-cluster",
      "version": "1.0.0",
      "description": "Distributed multi-node AGI",
      "tier": 4,
      "requires": ["agi-core", "agi-memory", "agi-extended"]
    }
  ]
}
```

---

## Migration Path

### For Existing Users (Current System)
1. **Export current state**: Run migration script to export memories, goals, tasks
2. **Install plugins**: `/plugin install agi-extended@agentic-marketplace`
3. **Import state**: Run import script to restore data
4. **Verify**: Run `/agi-status` to confirm migration

### For New Users
1. **Choose tier**: Based on infrastructure availability
2. **Install marketplace**: Add marketplace to Claude Code
3. **Install plugin**: `/plugin install agi-core@agentic-marketplace`
4. **Upgrade path**: Install higher tiers as infrastructure grows

### Migration Script
```bash
#!/bin/bash
# migrate-to-plugins.sh

# Export from current system
echo "Exporting current AGI state..."
python3 /mnt/agentic-system/scripts/export-agi-state.py \
  --output ~/.claude/agi/migration/

# Install plugins
echo "Installing AGI plugins..."
# (manual step via Claude Code)

# Import to new system
echo "Importing AGI state to plugin system..."
python3 ~/.claude/plugins/agi-extended/scripts/import-state.py \
  --input ~/.claude/agi/migration/
```

---

## Installation Workflow

### Team Setup (Admin)
1. Clone/copy marketplace to shared location (GitHub, SMB, etc.)
2. Add to `.claude/settings.json`:
```json
{
  "plugins": {
    "marketplaces": [
      {
        "name": "agentic-marketplace",
        "path": "/path/to/agentic-marketplace"
      }
    ],
    "enabled": ["agi-extended@agentic-marketplace"]
  }
}
```
3. Commit to repository

### Team Member Setup
1. Trust repository when prompted
2. Plugins auto-install
3. Run `/agi-init` to initialize
4. Configure `~/.claude/agi/config.yaml` for local environment

---

## Risk Analysis

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database schema changes | High | Medium | Version schemas, migration scripts |
| MCP server crashes | Medium | High | Health checks, auto-restart, fallbacks |
| Cluster node failures | Medium | Medium | Graceful degradation to local mode |
| Configuration conflicts | Medium | Low | Clear precedence rules, validation |
| Secret exposure | Low | Critical | Env vars only, .gitignore patterns |
| Breaking updates | Medium | High | Semantic versioning, changelogs |

### Safety Controls
- All self-modification requires user approval
- Code execution sandboxed
- Immutable safety goals cannot be overridden by plugins
- Audit logging for all AGI actions

---

## Next Steps

1. **Phase 1**: Build agi-core plugin (commands, agents, CLAUDE.md)
2. **Phase 2**: Package MCP servers for agi-memory
3. **Phase 3**: Create Docker compose for agi-extended
4. **Phase 4**: Build cluster orchestration for agi-cluster
5. **Phase 5**: Create private marketplace
6. **Phase 6**: Test with team members
7. **Phase 7**: Documentation and training

---

## File Inventory for Migration

### To agi-core
- `~/.claude/commands/*.md` → `commands/`
- `~/.claude/agents/*.md` → `agents/`
- `~/.claude/CLAUDE.md` → `CLAUDE.md`

### To agi-memory
- `/mnt/agentic-system/mcp-servers/agent-runtime-mcp/` → `mcp/agent-runtime/`
- `/mnt/agentic-system/mcp-servers/agi-mcp/` → `mcp/agi/`
- `/mnt/agentic-system/mcp-servers/ember-mcp/` → `mcp/ember/`

### To agi-extended
- `/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/` → `mcp/enhanced-memory/`
- `/mnt/agentic-system/mcp-servers/research-paper-mcp/` → `mcp/research-paper/`
- `/mnt/agentic-system/mcp-servers/video-transcript-mcp/` → `mcp/video-transcript/`
- `/mnt/agentic-system/mcp-servers/voice-mode/` → `mcp/voice-mode/`
- Docker configs from `/mnt/agentic-system/docker/`

### To agi-cluster
- `/mnt/agentic-system/mcp-servers/node-chat-mcp/` → `mcp/node-chat/`
- `/mnt/agentic-system/mcp-servers/cluster-execution-mcp/` → `mcp/cluster-execution/`
- `/mnt/agentic-system/mcp-servers/claude-flow-mcp/` → `mcp/claude-flow/`
- `/mnt/agentic-system/scripts/deploy-to-node.sh` → `scripts/`
