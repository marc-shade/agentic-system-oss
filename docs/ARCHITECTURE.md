# System Architecture

## Overview

The Agentic System is a 24/7 autonomous AI infrastructure providing persistent memory, task orchestration, and self-improvement capabilities.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Claude Code CLI                                  │
│                    (User's Development Environment)                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ MCP Protocol
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MCP Server Layer                                 │
├──────────────────┬──────────────────┬──────────────────┬───────────────┤
│ enhanced-memory  │ agent-runtime    │ sequential-      │ safla-mcp     │
│     -mcp         │     -mcp         │   thinking       │               │
│                  │                  │                  │               │
│ • 4-tier memory  │ • Goal mgmt      │ • Chain-of-      │ • 1.75M ops/s │
│ • Versioning     │ • Task queues    │   thought        │ • Embeddings  │
│ • RAG search     │ • Relay pipelines│ • Deep reasoning │ • Hybrid mem  │
│ • Compression    │ • Circuit breaker│                  │               │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴───────┬───────┘
         │                  │                  │                 │
         ▼                  ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Storage Layer                                    │
├──────────────────┬──────────────────┬──────────────────────────────────┤
│     Qdrant       │     SQLite       │          Redis                    │
│  (Vectors)       │  (Structured)    │         (Cache)                   │
│                  │                  │                                   │
│ • Embeddings     │ • Tasks          │ • Session cache                   │
│ • Similarity     │ • Goals          │ • Message queues                  │
│ • HNSW index     │ • Memories       │ • Rate limiting                   │
└──────────────────┴──────────────────┴──────────────────────────────────┘
```

## Component Details

### MCP Servers

#### enhanced-memory-mcp
4-tier memory system inspired by human cognition:

| Tier | Purpose | Retention | Example |
|------|---------|-----------|---------|
| Working | Active context | Minutes | Current task state |
| Episodic | Recent experiences | Hours-Days | Yesterday's work |
| Semantic | Learned concepts | Permanent | "How to use X" |
| Procedural | Skills | Permanent | Code patterns |

Features:
- Git-like versioning (commit, branch, diff, revert)
- Hybrid BM25 + vector search
- Automatic tier promotion
- 3.2x compression

#### agent-runtime-mcp
Persistent task management:
- Goals decompose into hierarchical tasks
- Tasks survive across sessions
- 48-agent relay pipeline for complex workflows
- Circuit breaker for fault tolerance

#### sequential-thinking
Deep reasoning chains:
- Multi-step analysis
- Hypothesis generation
- Self-verification

#### safla-mcp
High-performance memory operations:
- 1.75M+ embedding operations/second
- Hybrid memory architecture
- Pattern learning

### Storage Layer

#### Qdrant (Vector Database)
- HNSW index for fast similarity search
- 768-dimension embeddings
- Hybrid search (dense + sparse)

#### SQLite
- Structured data (tasks, goals, metadata)
- ACID transactions
- Simple deployment

#### Redis
- Session caching
- Message queues
- Rate limiting

## Data Flow

### Memory Creation
```
User Input → Embedding → Qdrant (vector) + SQLite (metadata)
                              ↓
                    4-Tier Classification
                              ↓
                    Compression & Versioning
```

### Memory Retrieval
```
Query → Embedding → Hybrid Search (BM25 + Vector)
                         ↓
              Re-ranking (Cross-encoder)
                         ↓
              Context Assembly
```

### Task Execution
```
Goal → Decomposition → Task Queue
                           ↓
              Agent Assignment
                           ↓
              Relay Pipeline (if complex)
                           ↓
              Result Aggregation
```

## Performance Characteristics

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Entity creation | ~2.3ms | 435/s |
| Semantic search | ~12ms | 81/s |
| Tier promotion | ~156ms | 6.4/s |
| Task decomposition | ~1200ms | - |
| Baton handoff | ~89ms | - |

## Deployment Options

### Local Development
- All services on localhost
- SQLite for simplicity
- Single-node Qdrant

### Production
- Distributed MCP servers
- Qdrant cluster
- Redis cluster
- Temporal for workflows
