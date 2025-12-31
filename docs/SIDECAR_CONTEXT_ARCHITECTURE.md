# Sidecar Context Architecture

## The Problem

Current context usage: **216k tokens (108% capacity)**
- MCP tools: 109.4k tokens (54.7%) - 11 servers × ~10k each
- Skills: ~45k tokens - 253 skills loaded regardless of need
- Agents: 6.7k tokens - 90+ agent definitions
- Memory files: 19.4k tokens - CLAUDE.md always present

**This is a STATIC LOADING anti-pattern.** Everything loads upfront whether needed or not.

## The Solution: Two-Tier Lazy Context System

### Tier 1: Core Context (Always Loaded) - Target: ~30k tokens

```
┌─────────────────────────────────────────────────────────────┐
│                    CORE CONTEXT (~30k)                       │
├─────────────────────────────────────────────────────────────┤
│  Native Tools (~10k)                                        │
│  ├─ Read, Write, Edit, MultiEdit                           │
│  ├─ Bash, Task, TodoWrite                                  │
│  └─ Glob, Grep, WebSearch, WebFetch                        │
├─────────────────────────────────────────────────────────────┤
│  Gateway MCP (~8k)                                          │
│  ├─ phoenix-cortex (intent → tool routing)                 │
│  │   ├─ cortex_query - Find tools by intent                │
│  │   ├─ cortex_schema - Get full schema on demand          │
│  │   ├─ cortex_execute - Proxy execution                   │
│  │   └─ cortex_state - Working memory                      │
│  ├─ voice-mode (communication)                             │
│  │   └─ converse - TTS/STT                                 │
│  └─ enhanced-memory (core only - 5 tools)                  │
│      ├─ search_nodes                                        │
│      ├─ create_entities                                     │
│      ├─ unified_search                                      │
│      ├─ semantic_cache_get/store                           │
│      └─ get_memory_status                                   │
├─────────────────────────────────────────────────────────────┤
│  Core Instructions (~5k)                                    │
│  ├─ CLAUDE_CORE.md (essential identity/policies)           │
│  └─ Response format template                                │
├─────────────────────────────────────────────────────────────┤
│  Indexes (~3k)                                              │
│  ├─ tool-index.json (150 tools, names only)                │
│  ├─ skill-index.json (253 skills, triggers only)           │
│  └─ agent-index.json (90 agents, capabilities only)        │
└─────────────────────────────────────────────────────────────┘
```

### Tier 2: Sidecar Context (Queryable on Demand) - Unlimited

```
┌─────────────────────────────────────────────────────────────┐
│                 SIDECAR CONTEXT MANAGER                      │
├─────────────────────────────────────────────────────────────┤
│  Full Tool Schemas (150+ tools)                             │
│  ├─ research-paper-mcp tools                               │
│  ├─ cluster-execution-mcp tools                            │
│  ├─ agent-runtime-mcp tools                                │
│  ├─ llm-council tools                                       │
│  ├─ sequential-thinking tools                              │
│  └─ arduino-surface tools                                   │
├─────────────────────────────────────────────────────────────┤
│  Full Skill Definitions (253 skills)                        │
│  └─ Loaded via sidecar_get_skill(name)                     │
├─────────────────────────────────────────────────────────────┤
│  Full Agent Definitions (90+ agents)                        │
│  └─ Loaded via sidecar_get_agent(name)                     │
├─────────────────────────────────────────────────────────────┤
│  Extended CLAUDE.md Sections                                │
│  ├─ mcp-details.md                                         │
│  ├─ workflows.md                                            │
│  ├─ troubleshooting.md                                      │
│  └─ examples.md                                             │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow

```
User: "Research AGI papers on arXiv"
         │
         ▼
┌─────────────────────────────────────────┐
│ 1. Core Context receives request        │
│    - No research tools loaded           │
│    - Has cortex_query available         │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 2. cortex_query("research papers arXiv")│
│    Returns: search_arxiv, extract_      │
│    insights, store_paper_knowledge      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 3. cortex_schema("search_arxiv")        │
│    Returns: Full schema with params     │
│    - query: str                         │
│    - max_results: int (default 10)      │
│    - sort_by: relevance|date            │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 4. sidecar_execute("research-paper-mcp",│
│    "search_arxiv", {query: "AGI"})      │
│    Sidecar proxies to actual server     │
│    Returns: Compressed results          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ 5. Results returned to user             │
│    Schemas released from context        │
│    Pattern recorded for learning        │
└─────────────────────────────────────────┘
```

## Token Budget Comparison

| Component | Current | Minimal | Savings |
|-----------|---------|---------|---------|
| MCP Tools | 109.4k | 15k | 94.4k (86%) |
| Skills | 45k | 3k (index) | 42k (93%) |
| Agents | 6.7k | 1k (index) | 5.7k (85%) |
| Memory files | 19.4k | 5k | 14.4k (74%) |
| **TOTAL** | **180k** | **24k** | **156k (87%)** |

## Implementation Components

### 1. Minimal Profile Config (`~/.claude.minimal.json`)

```json
{
  "mcpServers": {
    "phoenix-cortex": { "command": "python3", "args": [...] },
    "enhanced-memory-minimal": { "command": "python3", "args": ["--minimal"] },
    "voice-mode": { "command": "uv", "args": [...] }
  }
}
```

### 2. Sidecar Context Manager MCP

New server providing:
- `sidecar_get_tool(server, tool)` - Full schema on demand
- `sidecar_get_skill(name)` - Full skill definition
- `sidecar_get_agent(name)` - Full agent definition
- `sidecar_get_section(name)` - CLAUDE.md section
- `sidecar_execute(server, tool, params)` - Proxied execution

### 3. Index Files

- `~/.claude/indexes/tools.json` - Tool names + brief descriptions
- `~/.claude/indexes/skills.json` - Skill names + trigger patterns
- `~/.claude/indexes/agents.json` - Agent names + capability keywords

### 4. Enhanced Cortex Proxy

Upgrade Phoenix Cortex to:
- Actually execute proxied calls (not just return instructions)
- Use HTTP/stdio to communicate with backend MCP servers
- Cache schemas and results
- Track usage patterns for predictive loading

### 5. Profile Switcher Hook

`session-start` hook that:
- Detects session type (complex vs simple)
- Loads appropriate profile
- Initializes sidecar connection

## Migration Path

1. **Phase 1**: Create minimal profile + sidecar server (this doc)
2. **Phase 2**: Enhance Cortex for true proxying
3. **Phase 3**: Build index files and lazy loaders
4. **Phase 4**: Profile switching automation
5. **Phase 5**: Predictive loading and pattern learning

## Expected Results

- **Context**: 216k → 35k tokens (84% reduction)
- **Capability**: 100% maintained via sidecar
- **Latency**: +50-100ms for cold loads, <10ms for cached
- **Learning**: System gets smarter over time
