# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Enhanced Memory MCP Server - a high-performance memory management system for AI agents. Provides compressed SQLite storage with 4-tier architecture, Git-like versioning, and advanced RAG (Retrieval-Augmented Generation) capabilities with 200+ MCP tools.

## Build & Test Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run MCP server standalone (for testing)
python3 server.py

# Run comprehensive tests
python3 comprehensive_test.py

# Test all RAG tiers (22 tests)
python3 test_rag_integration_comprehensive.py

# Test specific RAG features
python3 test_graphrag_integration.py
python3 test_letta_integration.py

# Test code execution sandbox
python3 test_advanced_tool_use.py

# Test individual modules
python3 test_agi_phase2.py  # Temporal reasoning & consolidation
python3 test_agi_phase3.py  # Emotional tagging & associative networks
python3 test_agi_phase4.py  # Meta-cognition & self-improvement
```

## Architecture

### Core Components

**server.py** (~1213 lines) - Main FastMCP server. Architecture:
- Uses `memory_client.py` to connect to memory-db Unix socket service for concurrent access
- Core operations (create_entities, search_nodes) delegated to memory-db service
- Tools registered modularly via `register_*_tools()` functions
- **TPU importance scoring at entity creation** (lines 35-56, 482-559):
  - Imports `tpu_importance` module from hooks (with fallback heuristics)
  - `_score_and_tier_entities()` scores each entity via TPU Warm Service (port 8780)
  - Auto-assigns tiers: score ≥0.8 → long_term, ≥0.6 → episodic, <0.6 → working
  - Called automatically in `create_entities()` after contextual enrichment

**memory_db_service.py** - Unix socket service providing centralized SQLite access. Enables multiple Claude Code instances to share memory without corruption.

**memory_client.py** - Client wrapper for memory-db service with automatic fallback to direct SQLite when service unavailable.

### Memory Tiers

| Tier | Purpose | Access Pattern |
|------|---------|----------------|
| Core | System roles, AI agent library | Pre-loaded, sub-ms access |
| Working | Active projects, current context | Session-scoped, frequent r/w |
| Reference | Documentation, code patterns | Full-text search, lazy loaded |
| Archive | Historical data, metrics | Maximum compression, rare access |

### RAG Strategy Implementation

All RAG strategies are registered in `server.py` main block (lines 1441-1562):

| Tier | Strategy | Status | Tools | File |
|------|----------|--------|-------|------|
| 1 | Hybrid Search (BM25+Vector) | ✅ | `search_hybrid` | `hybrid_search_tools_nmf.py` |
| 1 | Re-ranking (Cross-Encoder) | ✅ | `search_with_reranking` | `reranking_tools_nmf.py` |
| 2 | Query Expansion | ✅ | `search_with_query_expansion` | `query_expansion_tools.py` |
| 2 | Multi-Query RAG | ✅ | `search_with_multi_query` | `multi_query_rag_tools.py` |
| 3.1 | Contextual Retrieval | ✅ | `generate_context_for_chunk`, `reindex_with_context` | `contextual_retrieval_tools.py` |
| 3.2 | Context-Aware Chunking | ✅ | `chunk_document_semantic` | `context_aware_chunking.py` |
| 3.3 | Hierarchical RAG | ✅ | `index_document_hierarchical`, `search_hierarchical` | `hierarchical_rag_tools.py` |
| 4.1+4.3 | Agentic + Self-Reflective RAG | ✅ | `agentic_retrieve`, `analyze_query`, `evaluate_results` | `agentic_rag_tools.py` |
| 4 | GraphRAG | ✅ | `graph_enhanced_search`, `get_entity_neighbors` | `graphrag_tools.py` |
| 4 | Visual Memory | ✅ | `store_visual_episode`, `find_similar_visual` | `visual_memory_tools.py` |
| - | Semantic Cache | ✅ | `semantic_cache_get`, `semantic_cache_store`, `agi_cached_reasoning` | `semantic_cache_tools.py` |

### Tool Registration Pattern

Tools are registered modularly in `server.py` main block (~line 1355):

```python
from query_expansion_tools import register_query_expansion_tools
register_query_expansion_tools(app, nmf_instance)
```

**To add new tools**:
1. Create `{feature}_tools.py` with `register_{feature}_tools(app, ...)`
2. Import and call in server.py's tool registration section
3. Add to `tool_catalog.py` for progressive tool discovery
4. Add tests in `test_rag_integration_comprehensive.py`

### Key Tool Files

```
*_tools.py files (25+):
├── agi_tools.py           # AGI Phase 1: Identity & actions
├── agi_tools_phase2.py    # Temporal reasoning, consolidation
├── agi_tools_phase3.py    # Emotional tagging, associative networks
├── agi_tools_phase4.py    # Meta-cognition, self-improvement
├── agentic_rag_tools.py   # Tier 4.1+4.3: Autonomous + self-reflective RAG
├── cluster_brain_tools.py # Multi-node cluster intelligence
├── contextual_retrieval_tools.py  # Tier 3.1: Context enhancement
├── graphrag_tools.py      # Graph-enhanced retrieval
├── hierarchical_rag_tools.py  # Tier 3.3: Multi-level indexing
├── hybrid_search_tools.py # Tier 1: BM25 + Vector
├── multi_query_rag_tools.py   # Tier 2: Query perspectives
├── nmf_tools.py           # Neural Memory Fabric
├── query_expansion_tools.py   # Tier 2: Query expansion
├── reasoning_tools.py     # 75/15 rule prioritization
├── reranking_tools.py     # Tier 1: Cross-encoder re-ranking
├── safla_tools.py         # SAFLA 4-tier memory
├── sleeptime_tools.py     # Letta sleeptime compute
├── semantic_cache_tools.py # LLM reasoning result caching (30-40% hit rate)
├── tool_search.py         # Progressive tool discovery
└── visual_memory_tools.py # LVR-style visual embeddings

agi/                       # AGI-specific modules (22 files)
├── consolidation.py       # Sleep-like memory consolidation
├── metacognition.py       # Self-awareness tracking
├── belief_tracking.py     # Probabilistic belief states
├── epistemic_scheduler.py # Epistemic flexibility audit
├── action_tracker.py      # Action outcome recording
├── agent_identity.py      # Cross-session identity
├── associative_network.py # Memory associations
├── emotional_memory.py    # Emotional tagging
├── self_improvement.py    # Self-improvement cycles
└── temporal_reasoning.py  # Causal chains

sandbox/                   # Code execution sandbox
├── executor.py            # RestrictedPython execution
└── security.py            # Safety checks, PII tokenization
```

### Database Schema

Primary tables in `~/.claude/enhanced_memories/memory.db`:

- `entities` - Core memory storage with compression, versioning, tier assignment
- `observations` - Entity observations/facts
- `relations` - Entity relationships (from → to, with weight and causal flag)
- `entity_versions` - Git-like version history
- `entity_branches` - Branch management
- `working_memory` - TTL-based temporary storage
- `episodic_memory` - Time-bound experiences
- `semantic_memory` - Abstract concepts
- `procedural_memory` - Skills and procedures
- `visual_episodes` - Visual memory with TPU embeddings

### Dependencies

Critical dependencies (from requirements.txt):
- `fastmcp` - MCP protocol implementation
- `sentence-transformers` - Re-ranking with cross-encoder (ms-marco-MiniLM-L-6-v2)
- `qdrant-client` - Hybrid search with BM25 + Vector
- `RestrictedPython` - Secure sandbox code execution
- `anthropic` - Claude API for contextual prefix generation

### Environment Variables

- `AGENTIC_SYSTEM_PATH` - Root path for agentic system (default: ~/agentic-system)
- `OLLAMA_HOST` - Ollama server for LLM operations
- `QDRANT_HOST` / `QDRANT_PORT` - Vector database connection

### TPU Integration

Real-time importance scoring via Google Coral TPU (when available on macpro51):
- Entities scored at creation time in `create_entities()`
- Auto-assigned to tier (working/episodic/long_term) based on score
- Graceful fallback to heuristic scoring when TPU unavailable
- Score ≥0.8 → long_term, ≥0.6 → episodic, <0.6 → working

### Neural Memory Fabric (NMF)

Alternative memory architecture in `neural_memory_fabric.py` and `nmf_*.py` files. Provides Letta-style memory blocks with open/edit/close semantics. Required by RAG Tier 1-2 tools.

## Common Patterns

### Adding a new memory tier feature

1. Add database table in `init_database()` if needed
2. Create tool file: `{feature}_tools.py`
3. Implement `register_{feature}_tools(app, db_path)`
4. Register in server.py tool registration section
5. Update `tool_catalog.py` for progressive tool discovery
6. Add tests to `test_rag_integration_comprehensive.py`

### Testing MCP tools locally

```python
# MockFastMCPApp pattern for testing tool registration
class MockFastMCPApp:
    def __init__(self):
        self.tools = {}
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

# Use in tests
mock_app = MockFastMCPApp()
register_your_tools(mock_app, dependencies)
assert 'your_tool_name' in mock_app.tools
```

### Memory consolidation (sleep-like cycles)

```python
# Run full consolidation: patterns → semantic, causal discovery, compression
result = await run_full_consolidation(time_window_hours=24)
```

### Agentic RAG retrieval (self-reflective)

```python
from agentic_rag_tools import AgenticRetriever

retriever = AgenticRetriever(nmf_instance)
result = retriever.retrieve(
    query="How does memory consolidation work?",
    max_iterations=3,
    quality_threshold=0.7
)
# Returns: RetrievalResult with results, quality_score, iterations, refinements
```

## Test Coverage

Main test file: `test_rag_integration_comprehensive.py` (22 tests, 100% pass rate)

| Tier | Tests |
|------|-------|
| Tier 1 | Hybrid search, re-ranking imports and registration |
| Tier 2 | Query expansion, multi-query RAG imports and registration |
| Tier 3 | Contextual retrieval, hierarchical RAG imports, registration, class creation |
| Tier 4 | Agentic RAG classes (QueryAnalyzer, ResultEvaluator, AgenticRetriever) |
