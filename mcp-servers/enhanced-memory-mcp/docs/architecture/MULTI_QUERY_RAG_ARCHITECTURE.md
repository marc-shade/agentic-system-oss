# Multi-Query RAG - Architecture Design Document

**Version**: 1.0
**Date**: November 9, 2025
**Status**: Architecture Design Phase
**References**: MULTI_QUERY_RAG_SPECIFICATION.md

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [Component Architecture](#component-architecture)
4. [Data Architecture](#data-architecture)
5. [Interface Design](#interface-design)
6. [Algorithm Design](#algorithm-design)
7. [Error Handling Architecture](#error-handling-architecture)
8. [Performance Architecture](#performance-architecture)
9. [Testing Architecture](#testing-architecture)
10. [Deployment Architecture](#deployment-architecture)

---

## Architecture Overview

### System Context

Multi-Query RAG operates within the enhanced-memory-mcp ecosystem as RAG Tier 2.2 (Query Optimization). It builds upon:

- **RAG Tier 1**: Hybrid Search + Re-ranking (foundation)
- **RAG Tier 2.1**: Query Expansion (complementary)

### Architectural Style

**Event-Driven Pipeline Architecture**:
- Input → Process → Output flow
- Asynchronous parallel execution
- Fail-fast with graceful degradation
- Stateless components (no persistence)

### Key Architectural Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Async/Parallel** | Minimize latency with concurrent searches | Complexity in error handling |
| **Stateless Design** | Simplicity, scalability | No query history tracking |
| **LLM-First with Fallback** | Best quality with reliability | Additional complexity |
| **RRF as Default** | Simple, no tuning needed | Less flexible than weighted |
| **Provenance Tracking** | Transparency, debugging | Additional metadata overhead |

---

## Design Principles

### 1. Separation of Concerns

**Principle**: Each component has one clear responsibility

**Application**:
- `PerspectiveGenerator`: Only perspective generation
- `MultiQueryExecutor`: Only search execution
- `ResultFusionEngine`: Only result combination

**Benefit**: Testable, maintainable, replaceable components

---

### 2. Fail-Fast with Graceful Degradation

**Principle**: Detect failures early, degrade gracefully

**Degradation Hierarchy**:
```
Level 1: Full multi-query with LLM-generated perspectives
    ↓ (LLM fails)
Level 2: Multi-query with template-based perspectives
    ↓ (Qdrant fails)
Level 3: Partial results from successful perspectives
    ↓ (All perspectives fail)
Level 4: Single-query fallback
```

**Benefit**: High availability, reliable service

---

### 3. Async-First Design

**Principle**: All I/O operations are asynchronous

**Application**:
- LLM calls: `async def generate_perspectives(...)`
- Search execution: `await asyncio.gather(*tasks)`
- Embedding generation: `await nmf.embedding_manager.generate(...)`

**Benefit**: Minimize latency through parallelism

---

### 4. Data Immutability

**Principle**: Data structures are immutable after creation

**Application**:
- Perspectives created once, never modified
- Search results are read-only
- Fused results are new objects

**Benefit**: Thread safety, easier reasoning

---

### 5. Explicit Over Implicit

**Principle**: Make behavior explicit and visible

**Application**:
- Provenance tracking shows which perspective found results
- Metadata includes all timing information
- Errors are logged with full context

**Benefit**: Observability, debugging

---

## Component Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                multi_query_rag_tools.py                 │
│                                                          │
│  ┌────────────────────────────────────────────────┐   │
│  │         PerspectiveGenerator                    │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ - nmf: NeuralMemoryFabric               │  │   │
│  │  │ - perspective_templates: Dict            │  │   │
│  │  │ - llm_prompt: str                        │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ + generate_perspectives()                │  │   │
│  │  │ + validate_perspective()                 │  │   │
│  │  │ + calculate_diversity()                  │  │   │
│  │  │ + _parse_llm_response()                  │  │   │
│  │  │ + _template_fallback()                   │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────────────────────────────────┐   │
│  │         MultiQueryExecutor                      │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ - nmf: NeuralMemoryFabric               │  │   │
│  │  │ - client: QdrantClient                   │  │   │
│  │  │ - sparse_model: SparseTextEmbedding      │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ + execute_parallel_searches()            │  │   │
│  │  │ + search_single_perspective()            │  │   │
│  │  │ + handle_failures()                      │  │   │
│  │  │ + _generate_embeddings()                 │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────────────────────────────────┐   │
│  │         ResultFusionEngine                      │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ - fusion_strategies: Dict                │  │   │
│  │  │ - rrf_k: int = 60                        │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ + fuse_results()                         │  │   │
│  │  │ + deduplicate()                          │  │   │
│  │  │ + reciprocal_rank_fusion()               │  │   │
│  │  │ + weighted_fusion()                      │  │   │
│  │  │ + score_based_fusion()                   │  │   │
│  │  │ + _build_provenance()                    │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
│                                                          │
│  ┌────────────────────────────────────────────────┐   │
│  │         MCP Tool Layer                          │   │
│  │  ┌──────────────────────────────────────────┐  │   │
│  │  │ + search_multi_query()                   │  │   │
│  │  │ + get_multi_query_stats()                │  │   │
│  │  │ + generate_perspectives()                │  │   │
│  │  └──────────────────────────────────────────┘  │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Component Interfaces

**PerspectiveGenerator Interface**:
```
Input:
  - query: str
  - num_perspectives: int
  - perspective_types: Optional[List[str]]

Output:
  - perspectives: List[Perspective]
  - diversity_score: float
  - latency_ms: int

Dependencies:
  - NMF (for LLM access)
  - Embedding manager (for diversity calculation)

Side Effects:
  - LLM API calls
  - Logging
```

**MultiQueryExecutor Interface**:
```
Input:
  - perspectives: List[Perspective]
  - limit: int

Output:
  - results_per_perspective: Dict[str, List[SearchResult]]
  - failures: List[str]
  - latency_ms: int

Dependencies:
  - Qdrant (for hybrid search)
  - NMF (for embeddings)
  - FastEmbed (for sparse vectors)

Side Effects:
  - Multiple Qdrant queries
  - Logging
```

**ResultFusionEngine Interface**:
```
Input:
  - perspective_results: Dict[str, List[SearchResult]]
  - strategy: str
  - weights: Optional[Dict[str, float]]

Output:
  - fused_results: List[FusedResult]
  - metadata: Dict

Dependencies:
  - None (pure computation)

Side Effects:
  - Logging
```

---

## Data Architecture

### Data Flow

```
┌──────────────┐
│  User Query  │
│  "system     │
│  architecture"│
└──────┬───────┘
       │
       ↓
┌─────────────────────────────────────────────┐
│  Step 1: Perspective Generation             │
│  Input: "system architecture"               │
│  Output:                                     │
│    [                                         │
│      {type: "technical",                     │
│       query: "technical implementation..."},│
│      {type: "user",                          │
│       query: "user experience with..."},    │
│      {type: "conceptual",                    │
│       query: "architectural patterns..."}   │
│    ]                                         │
└─────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────┐
│  Step 2: Parallel Search Execution          │
│                                              │
│  Technical Query ──→ Qdrant ──→ Results₁    │
│  User Query      ──→ Qdrant ──→ Results₂    │
│  Conceptual Query─→ Qdrant ──→ Results₃    │
│                                              │
│  Results₁: [Doc1(0.9), Doc2(0.8), Doc3(0.7)]│
│  Results₂: [Doc2(0.85), Doc4(0.75)]         │
│  Results₃: [Doc1(0.95), Doc5(0.7), Doc6(0.6)]│
└─────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────┐
│  Step 3: Result Fusion (RRF)                │
│                                              │
│  Doc1: Appears in Technical(rank=1),        │
│         Conceptual(rank=1)                  │
│    RRF = 1/(60+1) + 1/(60+1) = 0.0328      │
│                                              │
│  Doc2: Appears in Technical(rank=2),        │
│         User(rank=1)                        │
│    RRF = 1/(60+2) + 1/(60+1) = 0.0325      │
│                                              │
│  Doc3: Appears in Technical(rank=3)         │
│    RRF = 1/(60+3) = 0.0159                 │
│                                              │
│  Sorted: [Doc1(0.0328), Doc2(0.0325), ...]  │
└─────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────┐
│  Step 4: Add Provenance                     │
│                                              │
│  {                                           │
│    id: "doc1",                              │
│    score: 0.0328,                           │
│    provenance: [                            │
│      {perspective: "technical", rank: 1},   │
│      {perspective: "conceptual", rank: 1}   │
│    ]                                         │
│  }                                           │
└─────────────────────────────────────────────┘
       │
       ↓
┌──────────────┐
│ Final Results│
└──────────────┘
```

### Data Transformations

**Transformation 1: Query → Perspectives**
```
Input:  "system architecture"
Output: [
  Perspective(
    type="technical",
    query="technical implementation of system architecture",
    confidence=0.9
  ),
  ...
]
```

**Transformation 2: Perspective → Search Results**
```
Input:  Perspective(type="technical", query="...")
Output: [
  SearchResult(
    id="123",
    score=0.9,
    payload={...},
    perspective="technical",
    rank=1
  ),
  ...
]
```

**Transformation 3: Multiple Results → Fused Results**
```
Input:  {
  "technical": [Result1, Result2],
  "user": [Result2, Result3]
}
Output: [
  FusedResult(
    id="result2",
    score=0.0325,
    provenance=[
      {perspective: "technical", rank: 2},
      {perspective: "user", rank: 1}
    ]
  ),
  ...
]
```

---

## Interface Design

### LLM Interface

**Prompt Structure**:
```
System: You are a query reformulation expert.

User: Generate {num_perspectives} distinct query perspectives.

Original: "{query}"

Create queries from:
1. Technical: Implementation, architecture, how it works
2. User: Problems solved, use cases, user needs
3. Conceptual: Theory, patterns, abstract concepts

Requirements:
- Semantically different
- Maintain intent
- Searchable language
- Concise (<100 words)

Return JSON:
{
  "perspectives": [
    {"type": "...", "query": "...", "confidence": 0.0-1.0}
  ]
}
```

**Response Parsing**:
```python
# Expected format
{
  "perspectives": [
    {
      "type": "technical",
      "query": "technical implementation strategies...",
      "confidence": 0.9
    },
    {
      "type": "user",
      "query": "how users solve problems with...",
      "confidence": 0.85
    },
    {
      "type": "conceptual",
      "query": "theoretical foundations of...",
      "confidence": 0.8
    }
  ]
}

# Validation
- Must be valid JSON
- Must have "perspectives" key
- Each perspective must have type, query, confidence
- Confidence must be 0.0-1.0
```

---

### Qdrant Interface

**Hybrid Search Pattern**:
```python
# For each perspective query

# 1. Generate dense vector
embedding_result = await nmf.embedding_manager.generate_embedding(
    perspective.query
)
dense_vector = embedding_result.embedding

# 2. Generate sparse vector
sparse_embeddings = list(sparse_model.embed([perspective.query]))
sparse_vector = {
    "indices": sparse_embeddings[0].indices.tolist(),
    "values": sparse_embeddings[0].values.tolist()
}

# 3. Hybrid search with RRF
results = client.query_points(
    collection_name="enhanced_memory",
    prefetch=[
        Prefetch(query=dense_vector, using="text-dense", limit=limit*2),
        Prefetch(query=sparse_vector, using="text-sparse", limit=limit*2)
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=limit,
    with_payload=True
).points
```

---

## Algorithm Design

### Reciprocal Rank Fusion (RRF)

**Purpose**: Combine rankings from multiple perspectives without score normalization

**Algorithm**:
```
INPUT:
  results_per_perspective: Dict[str, List[SearchResult]]
  k: int = 60  (RRF constant)

INITIALIZE:
  doc_scores: Dict[str, float] = {}
  doc_provenance: Dict[str, List] = {}

FOR each (perspective_type, results) in results_per_perspective:
  FOR each (rank, result) in enumerate(results, start=1):
    doc_id = result.id

    # Calculate RRF contribution
    rrf_score = 1.0 / (k + rank)

    # Accumulate score
    IF doc_id NOT IN doc_scores:
      doc_scores[doc_id] = 0.0
      doc_provenance[doc_id] = []

    doc_scores[doc_id] += rrf_score
    doc_provenance[doc_id].append({
      perspective: perspective_type,
      rank: rank,
      score: result.score,
      rrf_contribution: rrf_score
    })

# Create fused results
fused_results = []
FOR each (doc_id, composite_score) in doc_scores:
  fused_results.append(FusedResult(
    id=doc_id,
    score=composite_score,
    provenance=doc_provenance[doc_id]
  ))

# Sort by composite score (descending)
fused_results.sort(key=lambda x: x.score, reverse=True)

RETURN fused_results
```

**Example**:
```
Given:
  Technical: [Doc1(rank=1), Doc2(rank=2), Doc3(rank=3)]
  User:      [Doc2(rank=1), Doc4(rank=2)]
  Conceptual:[Doc1(rank=1), Doc3(rank=2)]

RRF Scores (k=60):
  Doc1 = 1/(60+1) + 1/(60+1) = 0.0328
  Doc2 = 1/(60+2) + 1/(60+1) = 0.0325
  Doc3 = 1/(60+3) + 1/(60+2) = 0.0320
  Doc4 = 1/(60+2) = 0.0161

Ranking: [Doc1, Doc2, Doc3, Doc4]
```

---

### Diversity Calculation

**Purpose**: Measure semantic diversity across perspectives

**Algorithm**:
```
INPUT:
  perspectives: List[Perspective]

# Generate embeddings
embeddings = []
FOR perspective in perspectives:
  embedding = await generate_embedding(perspective.query)
  embeddings.append(embedding)

# Calculate pairwise similarities
similarities = []
FOR i in range(len(embeddings)):
  FOR j in range(i+1, len(embeddings)):
    similarity = cosine_similarity(embeddings[i], embeddings[j])
    similarities.append(similarity)

# Diversity is inverse of average similarity
IF len(similarities) > 0:
  avg_similarity = mean(similarities)
  diversity_score = 1.0 - avg_similarity
ELSE:
  diversity_score = 0.0

RETURN diversity_score
```

**Interpretation**:
- Diversity = 1.0: Completely different perspectives
- Diversity = 0.75: Good diversity (target)
- Diversity = 0.5: Moderate diversity
- Diversity = 0.0: Identical perspectives

---

## Error Handling Architecture

### Error Taxonomy

```
┌─────────────────────────────────────┐
│         Error Categories             │
├─────────────────────────────────────┤
│                                      │
│  1. LLM Errors                      │
│     - Service unavailable           │
│     - Timeout                       │
│     - Invalid response              │
│     - Quota exceeded                │
│                                      │
│  2. Search Errors                   │
│     - Qdrant unavailable            │
│     - Collection not found          │
│     - Query timeout                 │
│     - Invalid vectors               │
│                                      │
│  3. Validation Errors               │
│     - Invalid input query           │
│     - Malformed perspectives        │
│     - Low diversity score           │
│                                      │
│  4. System Errors                   │
│     - Out of memory                 │
│     - Network failure               │
│     - Dependency errors             │
│                                      │
└─────────────────────────────────────┘
```

### Error Handling Strategy

**Level 1: Component-Level Error Handling**
```python
# PerspectiveGenerator
try:
    perspectives = await llm_generate(query)
except LLMError as e:
    logger.warning(f"LLM failed, using template fallback: {e}")
    perspectives = template_fallback(query)
```

**Level 2: Graceful Degradation**
```python
# MultiQueryExecutor
results = await asyncio.gather(*tasks, return_exceptions=True)

working_results = {}
failed_perspectives = []

for i, perspective in enumerate(perspectives):
    if isinstance(results[i], Exception):
        logger.error(f"Search failed for {perspective.type}")
        failed_perspectives.append(perspective.type)
    else:
        working_results[perspective.type] = results[i]

# Return partial results if some succeeded
if len(working_results) > 0:
    return working_results, failed_perspectives
else:
    raise AllSearchesFailedError()
```

**Level 3: Fallback to Single Query**
```python
# MCP Tool Level
try:
    return await search_multi_query(query, ...)
except AllSearchesFailedError:
    logger.error("All perspectives failed, falling back to single query")
    return await search_hybrid(query, ...)  # Fallback to Tier 1
```

---

## Performance Architecture

### Latency Budget

```
Total Budget: 600ms

┌─────────────────────────────────────────┐
│  Perspective Generation: 200ms (33%)    │
│  ├─ LLM call: 150ms                     │
│  ├─ Parse response: 20ms                │
│  └─ Validation: 30ms                    │
├─────────────────────────────────────────┤
│  Parallel Searches: 400ms (67%)         │
│  ├─ Embedding generation: 50ms × 3      │
│  │   (parallel)                          │
│  ├─ Hybrid searches: 100ms × 3          │
│  │   (parallel)                          │
│  └─ Network overhead: 50ms              │
├─────────────────────────────────────────┤
│  Result Fusion: 50ms (8%)               │
│  ├─ Deduplication: 20ms                 │
│  ├─ RRF calculation: 20ms               │
│  └─ Sorting: 10ms                       │
└─────────────────────────────────────────┘
```

### Optimization Strategies

**1. Parallel Execution**
```python
# All searches run concurrently
tasks = [
    search_single_perspective(p1, limit),
    search_single_perspective(p2, limit),
    search_single_perspective(p3, limit)
]
results = await asyncio.gather(*tasks)

# Not sequential (3× slower):
# result1 = await search_single_perspective(p1)
# result2 = await search_single_perspective(p2)
# result3 = await search_single_perspective(p3)
```

**2. Early Returns**
```python
# Validate early, fail fast
if not query or len(query) < 2:
    raise ValidationError("Query too short")

if num_perspectives < 1 or num_perspectives > 5:
    raise ValidationError("Invalid num_perspectives")
```

**3. Caching** (Future)
```python
# Cache perspective generation for common queries
cache_key = f"perspectives:{query}:{num_perspectives}"
if cache_key in cache:
    return cache[cache_key]

# ... generate perspectives ...

cache[cache_key] = perspectives
return perspectives
```

---

## Testing Architecture

### Test Pyramid

```
                    ┌─────┐
                    │  E2E│  (5 tests)
                    │Tests│
                  ┌─┴─────┴─┐
                  │Integration│  (8 tests)
                  │  Tests    │
              ┌───┴───────────┴───┐
              │    Unit Tests      │  (15+ tests)
              │   (Components)     │
          ┌───┴────────────────────┴───┐
          │      Test Utilities        │
          │  (Mocks, Fixtures, Helpers)│
          └────────────────────────────┘
```

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | E2E Tests |
|-----------|------------|-------------------|-----------|
| PerspectiveGenerator | 5 | 2 | - |
| MultiQueryExecutor | 4 | 2 | - |
| ResultFusionEngine | 6 | 2 | - |
| MCP Tools | - | 2 | 5 |

### Test Data Strategy

**Fixture Design**:
```python
# test_fixtures.py

@pytest.fixture
def sample_query():
    return "system architecture"

@pytest.fixture
def sample_perspectives():
    return [
        Perspective(
            type="technical",
            query="technical implementation of system architecture",
            confidence=0.9
        ),
        Perspective(
            type="user",
            query="how users interact with system architecture",
            confidence=0.85
        ),
        Perspective(
            type="conceptual",
            query="architectural design patterns and theory",
            confidence=0.8
        )
    ]

@pytest.fixture
def mock_search_results():
    return {
        "technical": [
            SearchResult(id="doc1", score=0.9, payload={}, perspective="technical", rank=1),
            SearchResult(id="doc2", score=0.8, payload={}, perspective="technical", rank=2)
        ],
        "user": [
            SearchResult(id="doc2", score=0.85, payload={}, perspective="user", rank=1),
            SearchResult(id="doc3", score=0.75, payload={}, perspective="user", rank=2)
        ]
    }
```

---

## Deployment Architecture

### File Structure

```
enhanced-memory-mcp/
├── multi_query_rag_tools.py       (Core implementation)
├── test_multi_query_rag.py        (Unit tests)
├── test_multi_query_mcp.py        (Integration tests)
├── MULTI_QUERY_RAG_SPECIFICATION.md
├── MULTI_QUERY_RAG_ARCHITECTURE.md
├── MULTI_QUERY_RAG_IMPLEMENTATION.md
└── server.py                       (Updated with registration)
```

### Integration Points

**server.py Integration**:
```python
# After query expansion tools

# Register Multi-Query RAG tools (RAG Tier 2.2)
if nmf_instance:
    try:
        from multi_query_rag_tools import register_multi_query_tools
        register_multi_query_tools(app, nmf_instance)
        logger.info("✅ Multi-Query RAG (RAG Tier 2) integrated - Expected +20-30% coverage")
    except Exception as e:
        logger.warning(f"⚠️  Multi-Query RAG integration skipped: {e}")
else:
    logger.warning("⚠️  Multi-Query RAG skipped: NMF not available")
```

---

## Architecture Review Checklist

- ✅ Separation of concerns maintained
- ✅ Async-first design for performance
- ✅ Fail-fast with graceful degradation
- ✅ Stateless components for scalability
- ✅ Explicit error handling at all levels
- ✅ Comprehensive logging and observability
- ✅ Performance budget defined
- ✅ Testing strategy comprehensive
- ✅ Integration points clearly defined
- ✅ Data flow fully documented

---

**Status**: ✅ ARCHITECTURE COMPLETE
**Next**: Implementation Plan Document
