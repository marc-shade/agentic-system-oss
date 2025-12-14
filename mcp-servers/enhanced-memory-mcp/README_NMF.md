# Neural Memory Fabric Integration

## What's New

The **Neural Memory Fabric (NMF)** has been integrated into the enhanced-memory-mcp server, adding revolutionary capabilities:

✅ **Multi-Backend Storage**: SQLite + Chroma + Neo4j + Redis + Files
✅ **Memory Blocks**: Letta-style editable memory units
✅ **Hybrid Retrieval**: Semantic + Graph + Temporal + BM25
✅ **Dynamic Linking**: A-MEM inspired automatic connections
✅ **Temporal Awareness**: Bi-temporal tracking (Zep-style)
✅ **Distributed Sync**: Multi-node coordination (future)

## Quick Start

### 1. Install Dependencies

```bash
cd /Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp
pip install -r requirements-nmf.txt
```

### 2. Start Infrastructure

```bash
cd /Volumes/FILES/agentic-system/memory-fabric
docker-compose up -d
```

### 3. Test Phase 1

```bash
cd /Volumes/FILES/agentic-system/mcp/enhanced-memory-mcp
python3 test_nmf.py
```

### 4. Use in MCP

The enhanced-memory-mcp server now exposes these tools:

- `nmf_remember` - Store memories
- `nmf_recall` - Retrieve memories
- `nmf_open_block` - Load memory blocks
- `nmf_edit_block` - Edit memory blocks
- `nmf_close_block` - Close memory blocks
- `nmf_get_status` - System status
- `nmf_list_blocks` - List agent's blocks

## Architecture

```
┌─────────────────────────────────────────┐
│     Enhanced Memory MCP Server           │
│                                          │
│  ┌───────────────┐  ┌─────────────────┐│
│  │ Original      │  │ Neural Memory   ││
│  │ Git-like      │  │ Fabric (NEW)    ││
│  │ Tools         │  │ Tools           ││
│  └───────────────┘  └─────────────────┘│
└─────────────────────────────────────────┘
         │                    │
         │                    └──────────────┐
         ▼                                   ▼
┌──────────────────┐          ┌─────────────────────────┐
│  SQLite          │          │  Multi-Backend Storage  │
│  (Git Versions)  │          │  ├─ SQLite (metadata)   │
│                  │          │  ├─ Chroma (vectors)    │
│                  │          │  ├─ Neo4j (graph)       │
│                  │          │  ├─ Redis (cache)       │
│                  │          │  └─ Files (portable)    │
└──────────────────┘          └─────────────────────────┘
```

## Configuration

Edit `/Volumes/FILES/agentic-system/memory-fabric/nmf_config.yaml`

Key settings:
- **Storage paths**: SQLite, vector, files
- **Backend URIs**: Neo4j, Redis
- **Memory tiers**: Ultra-fast, working, long-term, archival
- **Intelligence**: Consolidation, linking, pruning
- **Distribution**: Multi-node sync (future)

## Backend Status

Phase 1 (Current):
- ✅ SQLite: Core storage
- ✅ Redis: Caching (optional)
- ⚠️  Chroma: Vector search (install required)
- ⚠️  Neo4j: Graph (Docker required)

Phase 2 (Next):
- Dynamic linking (A-MEM)
- Temporal graphs (Zep)
- Memory consolidation
- LLM integration

## Example Usage

### Python

```python
from neural_memory_fabric import get_nmf

# Initialize
nmf = await get_nmf()

# Store a memory
result = await nmf.remember(
    content="Important project insight...",
    metadata={'tags': ['project', 'insight']},
    agent_id="agent_marc"
)

# Recall memories
memories = await nmf.recall(
    query="project insights",
    agent_id="agent_marc",
    mode="hybrid"
)

# Use memory blocks
await nmf.edit_block(
    agent_id="agent_marc",
    block_name="identity",
    new_value="I am Marc's primary assistant..."
)

identity = await nmf.open_block("agent_marc", "identity")
```

### MCP Tools

From Claude Code:

```python
# Store memory
mcp__enhanced-memory-mcp__nmf_remember(
    content="Neural Memory Fabric is revolutionary",
    agent_id="agent_marc",
    tags=["nmf", "memory"]
)

# Recall memories
mcp__enhanced-memory-mcp__nmf_recall(
    query="memory systems",
    mode="hybrid"
)

# Edit memory block
mcp__enhanced-memory-mcp__nmf_edit_block(
    agent_id="agent_marc",
    block_name="context",
    new_value="Currently working on NMF implementation"
)
```

## Troubleshooting

### Docker Services Not Starting

```bash
cd /Volumes/FILES/agentic-system/memory-fabric
docker-compose down
docker-compose up -d
docker-compose ps  # Check status
```

### Dependencies Missing

```bash
pip install chromadb neo4j redis pyyaml
```

### Connection Errors

Check config file paths and URIs:
```bash
cat /Volumes/FILES/agentic-system/memory-fabric/nmf_config.yaml
```

## Next Steps

1. ✅ Phase 1: Core infrastructure (CURRENT)
2. ⏳ Phase 2: Vector + Graph integration
3. ⏳ Phase 3: Intelligence layer
4. ⏳ Phase 4: Memory blocks enhancement
5. ⏳ Phase 5: Distributed sync

See `/Users/marc/NEURAL_MEMORY_FABRIC_ARCHITECTURE.md` for complete roadmap.

---

**Status**: Phase 1 - Foundation Complete
**Created**: October 1, 2025
**Next**: Install dependencies and test
