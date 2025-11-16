# Multi-Query RAG - Technical Specification

**Version**: 1.0
**Date**: November 9, 2025
**Status**: Planning Phase
**Tier**: RAG Tier 2.2 - Query Optimization
**Author**: Enhanced Memory MCP Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements](#requirements)
3. [System Architecture](#system-architecture)
4. [Detailed Design](#detailed-design)
5. [API Specification](#api-specification)
6. [Data Models](#data-models)
7. [Performance Requirements](#performance-requirements)
8. [Testing Strategy](#testing-strategy)
9. [Integration Points](#integration-points)
10. [Security & Privacy](#security--privacy)
11. [Error Handling](#error-handling)
12. [Monitoring & Observability](#monitoring--observability)

---

## Executive Summary

### Purpose

Multi-Query RAG generates multiple query perspectives from a single user query, enabling comprehensive coverage across different viewpoints (technical, user-centric, conceptual). Unlike Query Expansion (which creates variations of the same query), Multi-Query RAG explores different *angles* on the same topic.

### Key Differences from Query Expansion

| Aspect | Query Expansion | Multi-Query RAG |
|--------|----------------|-----------------|
| **Goal** | Broader lexical coverage | Different perspectives |
| **Method** | Synonyms, reformulation | Perspective transformation |
| **Example Input** | "system architecture" | "system architecture" |
| **Query Expansion Output** | ["system architecture", "system design", "system structure"] | ["technical implementation of system", "user experience with system", "architectural design patterns"] |
| **Use Case** | Find documents with different terminology | Find documents addressing different aspects |
| **Expected Gain** | +15-25% recall | +20-30% coverage |

### Success Metrics

- **Coverage**: +20-30% increase in unique documents retrieved
- **Perspective Diversity**: ≥3 distinct perspectives per query
- **Latency**: ≤600ms for perspective generation + parallel search
- **Quality**: Perspective queries semantically distinct from original
- **Integration**: Seamless integration with existing RAG Tier 1 & 2.1

---

## Requirements

### Functional Requirements

#### FR-1: Perspective Generation
- **FR-1.1**: System SHALL generate ≥3 distinct perspectives for any input query
- **FR-1.2**: Perspectives SHALL be semantically different from each other
- **FR-1.3**: System SHALL support configurable number of perspectives (1-5)
- **FR-1.4**: System SHALL preserve original query as perspective 0
- **FR-1.5**: System SHALL use LLM for perspective generation

#### FR-2: Perspective Types
- **FR-2.1**: System SHALL generate technical/implementation perspective
- **FR-2.2**: System SHALL generate user/problem perspective
- **FR-2.3**: System SHALL generate conceptual/theoretical perspective
- **FR-2.4**: System SHALL support custom perspective types via configuration
- **FR-2.5**: System SHALL validate perspective quality before use

#### FR-3: Search Integration
- **FR-3.1**: System SHALL perform parallel hybrid searches for all perspectives
- **FR-3.2**: System SHALL aggregate results from all perspectives
- **FR-3.3**: System SHALL deduplicate results across perspectives
- **FR-3.4**: System SHALL track which perspective found each result
- **FR-3.5**: System SHALL support result fusion strategies (RRF, weighted, score-based)

#### FR-4: Result Ranking
- **FR-4.1**: System SHALL rank results by composite score
- **FR-4.2**: System SHALL support perspective-based weighting
- **FR-4.3**: System SHALL optionally apply re-ranking after fusion
- **FR-4.4**: System SHALL preserve provenance (which perspective found result)

#### FR-5: MCP Tool Integration
- **FR-5.1**: System SHALL expose `search_multi_query` MCP tool
- **FR-5.2**: System SHALL expose `get_multi_query_stats` MCP tool
- **FR-5.3**: System SHALL expose `generate_perspectives` utility tool (for testing)
- **FR-5.4**: System SHALL follow existing MCP tool patterns

### Non-Functional Requirements

#### NFR-1: Performance
- **NFR-1.1**: Perspective generation SHALL complete in ≤200ms
- **NFR-1.2**: Parallel searches SHALL complete in ≤400ms
- **NFR-1.3**: Total end-to-end latency SHALL be ≤600ms
- **NFR-1.4**: System SHALL support concurrent requests (≥10 QPS)

#### NFR-2: Scalability
- **NFR-2.1**: System SHALL handle queries of any length (up to 1000 chars)
- **NFR-2.2**: System SHALL support 1-5 perspectives without degradation
- **NFR-2.3**: System SHALL scale linearly with number of perspectives

#### NFR-3: Reliability
- **NFR-3.1**: System SHALL have 99.9% uptime
- **NFR-3.2**: System SHALL gracefully degrade if LLM unavailable
- **NFR-3.3**: System SHALL retry failed perspective generation (max 2 retries)
- **NFR-3.4**: System SHALL return partial results if some perspectives fail

#### NFR-4: Maintainability
- **NFR-4.1**: Code SHALL have ≥95% test coverage
- **NFR-4.2**: Code SHALL follow existing project patterns
- **NFR-4.3**: Code SHALL be documented with docstrings
- **NFR-4.4**: Code SHALL include inline comments for complex logic

#### NFR-5: Observability
- **NFR-5.1**: System SHALL log all perspective generations
- **NFR-5.2**: System SHALL track perspective diversity metrics
- **NFR-5.3**: System SHALL expose performance metrics
- **NFR-5.4**: System SHALL support debugging mode with detailed logs

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tool Layer                           │
│  search_multi_query() | get_multi_query_stats()             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Multi-Query Orchestrator                      │
│  - Input validation                                          │
│  - Perspective generation coordination                       │
│  - Parallel search execution                                 │
│  - Result fusion & ranking                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Perspective │  │   Search     │  │   Fusion     │
│  Generator   │  │  Executor    │  │   Engine     │
└──────────────┘  └──────────────┘  └──────────────┘
        ↓                  ↓                  ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ LLM Service  │  │ Hybrid Search│  │  Deduplicator│
│ (Ollama)     │  │  (Qdrant)    │  │  & Ranker    │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│              multi_query_rag_tools.py                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  PerspectiveGenerator                       │        │
│  ├────────────────────────────────────────────┤        │
│  │ + generate_perspectives()                   │        │
│  │ + validate_perspective()                    │        │
│  │ + calculate_diversity()                     │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  MultiQueryExecutor                         │        │
│  ├────────────────────────────────────────────┤        │
│  │ + execute_parallel_searches()               │        │
│  │ + collect_results()                         │        │
│  │ + handle_failures()                         │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  ResultFusionEngine                         │        │
│  ├────────────────────────────────────────────┤        │
│  │ + fuse_results()                            │        │
│  │ + deduplicate()                             │        │
│  │ + rank_results()                            │        │
│  │ + apply_weighting()                         │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
[User Query]
    ↓
[Input Validation]
    ↓
[PerspectiveGenerator.generate_perspectives()]
    ↓
[Technical, User, Conceptual Perspectives]
    ↓
[MultiQueryExecutor.execute_parallel_searches()]
    ↓
    ├─→ [Hybrid Search: Technical Perspective] → Results₁
    ├─→ [Hybrid Search: User Perspective]      → Results₂
    └─→ [Hybrid Search: Conceptual Perspective]→ Results₃
    ↓
[Aggregate: Results₁ + Results₂ + Results₃]
    ↓
[ResultFusionEngine.deduplicate()]
    ↓
[ResultFusionEngine.rank_results()]
    ↓
[Final Ranked Results with Provenance]
    ↓
[Return to User]
```

---

## Detailed Design

### 1. Perspective Generator

**Purpose**: Generate diverse query perspectives using LLM

**Class**: `PerspectiveGenerator`

**Responsibilities**:
- Generate N perspectives from original query using LLM
- Validate perspective quality (diversity, relevance)
- Calculate diversity score across perspectives
- Handle LLM failures with fallback strategies

**Key Methods**:

**`generate_perspectives(query, num_perspectives, perspective_types)`**
- **Input**: Original query string, number of perspectives, optional types
- **Output**: List of Perspective objects with type, query, confidence
- **Algorithm**:
  1. Construct LLM prompt with perspective requirements
  2. Call LLM to generate perspectives
  3. Parse JSON response into Perspective objects
  4. Validate each perspective (semantic distance, length, content)
  5. Calculate overall diversity score
  6. Return validated perspectives

**`validate_perspective(original, perspective)`**
- **Input**: Original query, perspective query
- **Output**: (is_valid: bool, diversity_score: float)
- **Validation Criteria**:
  - Semantic similarity: 0.5-0.9 (related but distinct)
  - Length: 10-500 characters
  - Not identical to original
  - Contains searchable terms
  - Grammatically valid

**`calculate_diversity(perspectives)`**
- **Input**: List of perspective queries
- **Output**: Diversity score (0-1)
- **Algorithm**:
  1. Generate embeddings for all perspectives
  2. Calculate pairwise cosine similarities
  3. Diversity = 1 - average_similarity
  4. Return diversity score

**LLM Prompt Template**:
```
Generate {num_perspectives} distinct query perspectives.

Original: "{query}"

Create queries from these angles:
1. Technical/Implementation: How it works, architecture, technical details
2. User/Problem: User needs, problems solved, use cases
3. Conceptual/Theoretical: Abstract concepts, design patterns, theory

Requirements:
- Semantically different from each other
- Maintain core intent
- Specific, searchable language
- Concise (< 100 words)

Return JSON:
{
  "perspectives": [
    {"type": "technical", "query": "...", "confidence": 0.9},
    {"type": "user", "query": "...", "confidence": 0.85},
    {"type": "conceptual", "query": "...", "confidence": 0.8}
  ]
}
```

---

### 2. Multi-Query Executor

**Purpose**: Execute parallel searches across all perspectives

**Class**: `MultiQueryExecutor`

**Responsibilities**:
- Execute hybrid searches in parallel (asyncio.gather)
- Handle individual search failures gracefully
- Collect and aggregate results
- Track performance metrics per perspective

**Key Methods**:

**`execute_parallel_searches(perspectives, limit)`**
- **Input**: List of Perspective objects, results limit
- **Output**: Dict mapping perspective type to search results
- **Algorithm**:
  1. Create async tasks for each perspective
  2. Execute tasks in parallel using asyncio.gather
  3. Handle exceptions (return empty results for failed searches)
  4. Map results back to perspective types
  5. Return dict of {perspective_type: [results]}

**`search_single_perspective(perspective, limit)`**
- **Input**: Single Perspective object, results limit
- **Output**: List of SearchResult objects
- **Algorithm**:
  1. Generate dense embedding for perspective query
  2. Generate sparse (BM25) embedding
  3. Execute hybrid search with RRF fusion
  4. Attach perspective metadata to results
  5. Return results list

**`handle_failures(results, perspectives)`**
- **Input**: Results dict (may contain exceptions), perspectives list
- **Output**: Cleaned results dict with failure info
- **Algorithm**:
  1. Identify failed searches (Exception objects)
  2. Log failures with perspective info
  3. Replace exceptions with empty result lists
  4. Track failure metrics
  5. Return cleaned results

**Parallel Execution Pattern**:
- Use `asyncio.gather(*tasks, return_exceptions=True)`
- Allows some searches to fail without blocking others
- Enables graceful degradation

---

### 3. Result Fusion Engine

**Purpose**: Combine, deduplicate, and rank results from all perspectives

**Class**: `ResultFusionEngine`

**Responsibilities**:
- Implement multiple fusion strategies (RRF, weighted, score-based)
- Deduplicate results across perspectives
- Preserve provenance (which perspective found each result)
- Generate composite scores

**Key Methods**:

**`fuse_results(perspective_results, strategy, weights)`**
- **Input**: Results per perspective, fusion strategy, optional weights
- **Output**: List of FusedResult objects with composite scores
- **Algorithm**:
  1. Select fusion strategy function
  2. Apply strategy to generate composite scores
  3. Attach provenance metadata
  4. Sort by composite score
  5. Return ranked results

**`deduplicate(results)`**
- **Input**: List of SearchResult objects (may have duplicates)
- **Output**: Deduplicated list (one entry per unique ID)
- **Algorithm**:
  1. Group results by document ID
  2. For each ID, keep result with highest score
  3. Merge provenance from all instances
  4. Return deduplicated list

**`reciprocal_rank_fusion(perspective_results, k=60)`**
- **Input**: Results per perspective, RRF constant k
- **Output**: List of FusedResult objects
- **Algorithm**: For each document:
  ```
  RRF_score = Σ(1 / (k + rank_i))

  where:
    k = 60 (constant)
    rank_i = rank in perspective i (1-based)
  ```
- **Properties**:
  - Simple, parameter-free
  - Works well without tuning
  - Balances contributions from all perspectives

**`weighted_fusion(perspective_results, weights)`**
- **Input**: Results per perspective, weight dict
- **Output**: List of FusedResult objects
- **Algorithm**: For each document:
  ```
  Weighted_score = Σ(weight_i × score_i)

  where:
    weight_i = weight for perspective i
    score_i = score in perspective i
  ```
- **Properties**:
  - Allows perspective prioritization
  - Requires weight tuning
  - Good for domain-specific needs

**`score_based_fusion(perspective_results)`**
- **Input**: Results per perspective
- **Output**: List of FusedResult objects
- **Algorithm**: For each document:
  ```
  Score = max(score_i) across all perspectives
  ```
- **Properties**:
  - Preserves best scores
  - May favor one perspective
  - Good for high-precision needs

---

## API Specification

### MCP Tool 1: `search_multi_query`

**Purpose**: Search using multiple query perspectives

**Parameters**:
```
query: str (required)
  Original search query

num_perspectives: int = 3
  Number of perspectives to generate (1-5)

perspective_types: List[str] = None
  Specific perspective types or None for auto-selection
  Options: ["technical", "user", "conceptual", "historical", "comparative"]

fusion_strategy: str = "rrf"
  Result fusion strategy
  Options: "rrf", "weighted", "score_based"

perspective_weights: Dict[str, float] = None
  Perspective weights for weighted fusion
  Example: {"technical": 0.5, "user": 0.3, "conceptual": 0.2}

limit: int = 10
  Total number of results to return

score_threshold: float = None
  Minimum score threshold for results

include_provenance: bool = True
  Include perspective tracking in results
```

**Returns**:
```json
{
  "success": true,
  "query": "system architecture",
  "perspectives": [
    {
      "type": "technical",
      "query": "technical implementation of system architecture",
      "confidence": 0.9,
      "result_count": 8
    }
  ],
  "fusion_strategy": "rrf",
  "count": 10,
  "results": [
    {
      "id": "123",
      "score": 0.856,
      "payload": {...},
      "provenance": [
        {"perspective": "technical", "rank": 1, "rrf_contribution": 0.016}
      ]
    }
  ],
  "metadata": {
    "strategy": "multi_query_rag",
    "num_perspectives": 3,
    "total_candidates": 21,
    "unique_results": 10,
    "perspective_diversity": 0.75,
    "latency_ms": {
      "perspective_generation": 150,
      "parallel_searches": 380,
      "fusion": 45,
      "total": 575
    }
  }
}
```

---

### MCP Tool 2: `get_multi_query_stats`

**Purpose**: Get system statistics and configuration

**Returns**:
```json
{
  "status": "ready",
  "llm_available": true,
  "perspective_types": ["technical", "user", "conceptual", "historical", "comparative"],
  "default_num_perspectives": 3,
  "fusion_strategies": ["rrf", "weighted", "score_based"],
  "default_fusion_strategy": "rrf",
  "performance": {
    "avg_perspective_generation_ms": 145,
    "avg_parallel_search_ms": 390,
    "avg_total_latency_ms": 560
  }
}
```

---

### MCP Tool 3: `generate_perspectives`

**Purpose**: Test perspective generation without search (utility tool)

**Parameters**:
```
query: str (required)
num_perspectives: int = 3
perspective_types: List[str] = None
```

**Returns**:
```json
{
  "success": true,
  "query": "system architecture",
  "perspectives": [
    {
      "type": "technical",
      "query": "technical implementation of system architecture",
      "confidence": 0.9
    }
  ],
  "diversity_score": 0.75,
  "latency_ms": 145
}
```

---

## Data Models

### Perspective
```python
@dataclass
class Perspective:
    type: str              # "technical", "user", "conceptual"
    query: str             # Reformulated query
    confidence: float      # Quality score (0-1)
    embedding: Optional[List[float]] = None
```

### SearchResult
```python
@dataclass
class SearchResult:
    id: str                # Document ID
    score: float           # Search score
    payload: Dict          # Document payload
    perspective: str       # Which perspective found this
    rank: int             # Rank in perspective's results
```

### FusedResult
```python
@dataclass
class FusedResult:
    id: str                      # Document ID
    score: float                 # Composite score
    payload: Dict                # Document payload
    provenance: List[Dict]       # Perspective metadata
    fusion_strategy: str         # Strategy used
```

---

## Performance Requirements

### Latency Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Perspective Generation | 150ms | 200ms |
| Single Hybrid Search | 100ms | 150ms |
| Parallel Searches (3) | 350ms | 400ms |
| Result Fusion | 30ms | 50ms |
| **Total End-to-End** | **550ms** | **600ms** |

### Throughput Targets
- QPS: ≥10
- Concurrent Requests: ≥10
- Success Rate: ≥99.5%

---

## Testing Strategy

### Unit Tests (10 tests minimum)
1. Perspective generation with LLM
2. Perspective validation logic
3. Diversity score calculation
4. Parallel search execution
5. Individual search failures
6. Result fusion (RRF)
7. Result fusion (weighted)
8. Result fusion (score-based)
9. Deduplication logic
10. Provenance tracking

### Integration Tests (5 tests minimum)
1. End-to-end multi-query flow
2. MCP tool invocation
3. Integration with hybrid search
4. LLM fallback handling
5. Performance benchmarks

---

## Integration Points

### Upstream Dependencies
1. Neural Memory Fabric (NMF) - LLM access
2. Qdrant - Vector database
3. FastEmbed - Sparse vectors

### Downstream Integrations
1. Re-ranking (optional chaining)
2. Query Expansion (complementary use)

---

## Security & Privacy

### Data Handling
- Queries sent to LLM (no PII)
- No long-term query storage
- Results from Qdrant (existing privacy)

### LLM Security
- Input validation
- Output sanitization
- Structured parsing

---

## Error Handling

### Graceful Degradation Priority
1. Full multi-query with LLM
2. Template-based perspectives (fallback)
3. Partial results if some searches fail
4. Single query if all perspectives fail

---

## Appendix

### Example Perspectives

**Query**: "memory optimization"

**Technical**: "technical implementation strategies for memory optimization including caching algorithms and data structure efficiency"

**User**: "how to solve memory performance problems and improve application responsiveness"

**Conceptual**: "theoretical foundations of memory optimization including time-space tradeoffs and algorithmic complexity"

---

**Status**: ✅ SPECIFICATION COMPLETE
**Next**: Architecture Design Document
