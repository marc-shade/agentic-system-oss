# Sidecar Context Manager MCP

**The brain of the lazy-loading context system.**

Reduces Claude Code context from ~142k tokens to ~20k tokens (86% reduction) while maintaining 100% functionality through on-demand loading.

## The Problem

Claude Code's context was at 108% capacity (216k/200k tokens):
- MCP tools: 109k tokens (11 servers × ~10k each)
- Skills: 45k tokens (253 skills loaded regardless of need)
- Agents: 7k tokens (90+ agent definitions)
- Memory files: 20k tokens (CLAUDE.md always present)

**This is a STATIC LOADING anti-pattern.** Everything loads upfront whether needed or not.

## The Solution

Two-tier lazy context architecture:

### Tier 1: Core Context (Always Loaded) - ~20k tokens
- `enhanced-memory-minimal` - 6 essential memory tools
- `voice-mode` - Voice communication
- `sidecar-context` - Gateway to everything else
- `phoenix-cortex` - Intent routing

### Tier 2: Sidecar Context (On-Demand) - Unlimited
- 150+ MCP tool schemas
- 253 skill definitions
- 90+ agent definitions
- Extended CLAUDE.md sections

## Installation

```bash
# Already installed in agentic-system
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/sidecar-context-mcp

# Run directly
python3 server.py
```

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "sidecar-context": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/sidecar-context-mcp/server.py"],
      "env": {"STORAGE_BASE": "/Volumes/SSDRAID0/agentic-system"}
    }
  }
}
```

## Tools

### `sidecar_search`
Search indexes for tools, skills, or agents.
```python
sidecar_search(query="memory", types="all", limit=5)
# Returns lightweight index entries, not full content
```

### `sidecar_get_tool`
Get full schema for a specific tool.
```python
sidecar_get_tool("mcp__research-paper-mcp__search_arxiv")
# Returns complete schema with parameters
```

### `sidecar_get_skill`
Get full skill definition.
```python
sidecar_get_skill("github-release-management")
# Returns SKILL.md content
```

### `sidecar_get_agent`
Get full agent definition.
```python
sidecar_get_agent("code-reviewer")
# Returns agent.md content
```

### `sidecar_get_section`
Get CLAUDE.md section on demand.
```python
sidecar_get_section("workflows")
# Returns section content
# Available: mcp-details, workflows, troubleshooting, ports
```

### `sidecar_list_indexes`
Overview of all indexed items.
```python
sidecar_list_indexes()
# Returns counts and samples
```

### `sidecar_stats`
Performance statistics.
```python
sidecar_stats()
# Returns cache hit rates, access patterns
```

### `sidecar_preload`
Preload items for faster access.
```python
sidecar_preload(["search_arxiv", "code-reviewer"])
# Warms cache for upcoming work
```

## Profile Switching

Use the profile switcher to switch between minimal and full profiles:

```bash
~/.claude/scripts/switch-profile.sh minimal  # 20k tokens
~/.claude/scripts/switch-profile.sh full     # 142k tokens
~/.claude/scripts/switch-profile.sh status   # Show current
```

## Index Files

Pre-built indexes at `~/.claude/indexes/`:
- `tools.json` - Tool names, servers, keywords (~2k tokens)
- `skills.json` - Skill names, triggers, token estimates (~1k tokens)
- `agents.json` - Agent names, capabilities (~500 tokens)

## Context Sections

Modular CLAUDE.md sections at `~/.claude/context-sections/`:
- `mcp-details.md` - Full MCP server documentation
- `workflows.md` - Temporal, AutoKitteh, AGI workflows
- `troubleshooting.md` - Common issues and fixes
- `ports.md` - Port reference table

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CORE CONTEXT (~20k)                       │
├─────────────────────────────────────────────────────────────┤
│  4 MCP Servers: memory, voice, sidecar, cortex              │
│  Lightweight indexes: tools, skills, agents                  │
│  Core CLAUDE.md instructions                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ sidecar_get_*
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 SIDECAR CONTEXT (Unlimited)                  │
├─────────────────────────────────────────────────────────────┤
│  Full tool schemas (150+)      │  Extended CLAUDE.md        │
│  Full skill definitions (253)  │  Workflow guides           │
│  Full agent definitions (90+)  │  Troubleshooting docs      │
│  LRU cached for performance    │  Port references           │
└─────────────────────────────────────────────────────────────┘
```

## Token Budget

| Component | Full | Minimal | Savings |
|-----------|------|---------|---------|
| MCP Tools | 70k | 12.5k | 82% |
| Skills | 45k | 0 (indexed) | 100% |
| Agents | 7k | 0 (indexed) | 100% |
| Memory files | 20k | 5k | 75% |
| **TOTAL** | **142k** | **20k** | **86%** |

## Integration with Phoenix Cortex

Sidecar works alongside Phoenix Cortex:
- **Cortex**: Intent → tool routing, compiled chains
- **Sidecar**: Full content loading, caching, indexes

Together they provide:
1. `cortex_query("research papers")` → suggests tools
2. `sidecar_get_tool("search_arxiv")` → full schema
3. `cortex_execute()` → proxied execution

## Performance

- Index lookup: <1ms
- Cache hit: <5ms
- Cache miss (file load): ~50ms
- LRU cache: 50 items per type
- Hit rate improves with use
