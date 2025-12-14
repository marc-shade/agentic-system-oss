# Cluster Node Feature Catalog
Generated: 2025-11-24

## Quick Summary

| Node | Role | Enhanced Memory | AGI Subsystem | MCP Servers | Intelligent Agents |
|------|------|-----------------|---------------|-------------|-------------------|
| **macpro51** | builder | 134 files | 12 files (MOST) | 18 servers | 58 agents |
| **mac-studio** | orchestrator | 130 files | 9 files | 24 servers (MOST) | 67 agents |
| **macbook-air-m3** | researcher | 129 files | 9 files | 18 servers | 68 agents (MOST) |
| **completeu-server** | ai-inference | 125 files | 9 files | 14 servers | 59 agents |

---

## Node Details

### macpro51 (Builder) - 192.168.1.183
**Storage**: `/mnt/agentic-system`
**OS**: Linux (Fedora)

**Unique Capabilities:**
- PySR Symbolic Regression (pysr_hooks.py, pysr_scheduler.py, pysr_symbolic_regression.py)
- Security scanning (security-auditor-mcp, security-scanner-mcp)
- Voice AI (voice-agi-mcp, voice-mode)
- Node chat MCP (node-chat-mcp)
- Claude Code control MCP
- Compression integration
- Fast batch sync
- Filesystem tools

**AGI Subsystem (12 files):**
- action_tracker.py
- agent_identity.py
- associative_network.py
- consolidation.py
- emotional_memory.py
- metacognition.py
- pysr_hooks.py ⭐ UNIQUE
- pysr_scheduler.py ⭐ UNIQUE
- pysr_symbolic_regression.py ⭐ UNIQUE
- self_improvement.py
- temporal_reasoning.py

---

### mac-studio (Orchestrator) - 192.168.1.16
**Storage**: `/Volumes/SSDRAID0/agentic-system`
**OS**: macOS (arm64)

**Unique Capabilities:**
- Most MCP servers (24)
- AutoKitteh MCP
- Component library MCP
- Content creator MCP
- Instructor MCP
- LangGraph MCP
- Maker MCP
- Nuclei MCP
- Outlines MCP
- Software planning MCP
- Sprite animation MCP
- SQLite MCP server
- Task manager MCP
- YouTube transcript MCP
- toon_fastmcp.py

**AGI Subsystem (9 files):**
- Standard AGI files (no PySR)

---

### macbook-air-m3 (Researcher) - 192.168.1.76
**Storage**: `/Users/marc/agentic-system`
**OS**: macOS (arm64)

**Unique Capabilities:**
- Most intelligent agents (68)
- Bing mechanism MCP
- Dipole protocol MCP
- MCP code execution wrapper
- Symbolic learning MCP
- THZ probabilistic MCP

**AGI Subsystem (9 files):**
- Standard AGI files (no PySR)

---

### completeu-server (AI Inference) - 192.168.1.186
**Storage**: `/Volumes/FILES/agentic-system`
**OS**: macOS (arm64)

**Unique Capabilities:**
- 24 Ollama models (up to 120B params)
- LRU cache layer
- Model router
- Server v2
- Sequential thinking MCP
- Claude Flow wrapper

**AGI Subsystem (9 files):**
- Standard AGI files (no PySR)

**MISSING (needs sync):**
- agent_file.py, agent_file_tools.py
- cluster_shared_blocks.py
- compression_integration.py
- fast_batch_sync.py
- filesystem_tools.py
- letta_memory_blocks.py, letta_tools.py
- pysr_tools.py
- sleeptime_agent.py, sleeptime_tools.py
- sync_sqlite_to_qdrant.py
- PySR AGI files

---

## Critical Files to Sync

### Priority 1: AGI Subsystem (macpro51 → all others)
```
mcp-servers/enhanced-memory-mcp/agi/pysr_hooks.py
mcp-servers/enhanced-memory-mcp/agi/pysr_scheduler.py
mcp-servers/enhanced-memory-mcp/agi/pysr_symbolic_regression.py
```

### Priority 2: Enhanced Memory Tools (macpro51 → completeu-server)
```
mcp-servers/enhanced-memory-mcp/agent_file.py
mcp-servers/enhanced-memory-mcp/agent_file_tools.py
mcp-servers/enhanced-memory-mcp/cluster_shared_blocks.py
mcp-servers/enhanced-memory-mcp/compression_integration.py
mcp-servers/enhanced-memory-mcp/fast_batch_sync.py
mcp-servers/enhanced-memory-mcp/filesystem_tools.py
mcp-servers/enhanced-memory-mcp/letta_memory_blocks.py
mcp-servers/enhanced-memory-mcp/letta_tools.py
mcp-servers/enhanced-memory-mcp/pysr_tools.py
mcp-servers/enhanced-memory-mcp/sleeptime_agent.py
mcp-servers/enhanced-memory-mcp/sleeptime_tools.py
mcp-servers/enhanced-memory-mcp/sync_sqlite_to_qdrant.py
```

### Priority 3: MCP Servers (selective sync based on role)
- **All nodes need**: node-chat-mcp, security-auditor-mcp
- **Builder nodes**: voice-mode, security-scanner-mcp
- **Inference nodes**: model-router capabilities

---

## Sync Commands

### Sync AGI subsystem to all nodes:
```bash
# To mac-studio
rsync -avz /mnt/agentic-system/mcp-servers/enhanced-memory-mcp/agi/ \
  marc@192.168.1.16:/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp/agi/

# To macbook-air-m3
rsync -avz /mnt/agentic-system/mcp-servers/enhanced-memory-mcp/agi/ \
  marc@192.168.1.76:/Users/marc/agentic-system/mcp-servers/enhanced-memory-mcp/agi/

# To completeu-server
rsync -avz /mnt/agentic-system/mcp-servers/enhanced-memory-mcp/agi/ \
  marc@192.168.1.186:/Volumes/FILES/agentic-system/mcp-servers/enhanced-memory-mcp/agi/
```

---

## Last Verified
- macpro51: 2025-11-24 21:54 UTC
- mac-studio: 2025-11-24 21:54 UTC
- macbook-air-m3: 2025-11-24 21:54 UTC
- completeu-server: 2025-11-24 21:54 UTC
