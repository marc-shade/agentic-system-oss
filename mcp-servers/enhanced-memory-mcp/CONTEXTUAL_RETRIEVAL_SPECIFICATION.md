# Contextual Retrieval Specification - RAG Tier 3.1

**Date**: November 9, 2025
**Status**: Planning Phase
**Tier**: RAG Tier 3 - Context Enhancement
**Strategy**: 3.1 - Contextual Retrieval
**Priority**: HIGH (Anthropic's proven method)
**Expected Improvement**: +35-49% accuracy

---

## Executive Summary

**Contextual Retrieval** is a RAG enhancement technique developed and validated by Anthropic that adds document-level context to each chunk before embedding. This addresses a fundamental limitation of traditional RAG: chunks lose their document context when embedded in isolation.

**The Problem**:
- Traditional RAG embeds chunks independently
- Chunks like "It uses Redis for caching" lose document context
- Search struggles to match queries like "What caching does the system use?"

**The Solution**:
- Use LLM to generate contextual prefix for each chunk
- Prefix explains: "This section describes the caching layer of the authentication system..."
- Embed the contextualized chunk
- Search becomes significantly more accurate

**Anthropic's Research Results**:
- +35% improvement (with BM25 hybrid)
- +49% improvement (with BM25 + reranking)
- Validated across multiple domains

**Our Implementation Goal**: +35-49% accuracy improvement while maintaining acceptable performance

---

## Background & Motivation

### Current State (RAG Tier 1 + Tier 2)

We currently have:
- ✅ Hybrid Search (BM25 + Dense vectors): +20-30% recall
- ✅ Cross-Encoder Re-ranking: +40-55% precision
- ✅ Query Expansion: +15-25% recall
- ✅ Multi-Query RAG: +20-30% coverage

**Combined Current Improvement**: ~200-300% over baseline

### The Missing Piece: Context

**Observation**: Even with all current improvements, chunks embedded without context still struggle with:
1. **Ambiguous References**: "It uses Redis" - what is "it"?
2. **Implicit Context**: "The auth layer" - which system?
3. **Document Structure**: Where does this chunk fit in the larger document?
4. **Domain Context**: What domain/topic does this relate to?

### Anthropic's Solution

**Key Insight**: Prepend each chunk with LLM-generated context before embedding

**Process**:
1. For each chunk, prompt LLM: "Explain what this chunk is about in the context of the whole document"
2. LLM generates 50-100 word context
3. Concatenate: `[CONTEXT] + [ORIGINAL CHUNK]`
4. Embed the contextualized chunk
5. At search time, chunks now have rich context for matching

**Example**:

Original Chunk (isolated):
```
It uses Redis for caching and PostgreSQL for persistence.
```

Contextualized Chunk:
```
This section describes the data storage architecture of the authentication
service in the user management system. It uses Redis for caching and
PostgreSQL for persistence.
```

**Impact**: Query "What database does the authentication service use?" now matches much better!

---

## Functional Requirements

### FR-1: Context Generation

**Requirement**: Generate contextual prefixes for chunks using LLM

**Inputs**:
- Document content (full)
- Chunk content (excerpt)
- Document metadata (title, type, tags, etc.)

**Process**:
1. Build prompt with document context and chunk
2. Call LLM to generate 50-100 word contextual prefix
3. Validate prefix quality (length, relevance)

**Output**:
- Contextual prefix string
- Confidence score (0.0-1.0)

**Constraints**:
- Prefix length: 50-100 words (target)
- Generation time: <2 seconds per chunk
- Token cost: ~200-300 tokens per chunk

### FR-2: Re-indexing with Context

**Requirement**: Re-index existing entities with contextual prefixes

**Process**:
1. Retrieve all entities from database
2. For each entity:
   - Generate contextual prefix
   - Create new observation: `[CONTEXT] + [ORIGINAL]`
   - Update entity in database
   - Re-embed with NMF
3. Track progress, handle failures
4. Validate re-indexing completion

**Constraints**:
- Must preserve original observations
- Must maintain entity IDs (no recreation)
- Must handle 1,175 entities efficiently
- Estimated time: 1-2 hours for full re-index

### FR-3: Incremental Context Addition

**Requirement**: Add context to new entities as they're created

**Process**:
1. Intercept `create_entities` calls
2. For each new entity:
   - Generate contextual prefix
   - Prepend to observations before storage
3. Store both original and contextualized versions

**Constraints**:
- Must not slow down entity creation significantly (<500ms overhead)
- Must be optional (configurable)

### FR-4: Context Quality Validation

**Requirement**: Validate generated context quality

**Checks**:
1. **Length**: 50-100 words (warn if outside range)
2. **Relevance**: Contains key terms from original chunk
3. **Coherence**: Grammatically correct
4. **Specificity**: Avoids generic phrases like "this section discusses"

**Actions**:
- Log quality metrics
- Retry if quality too low
- Fall back to simpler context if LLM fails

### FR-5: Search Integration

**Requirement**: Integrate contextual retrieval with existing search

**Options**:
1. **Automatic**: All searches use contextualized chunks
2. **Optional**: New tool `search_with_context` alongside existing tools
3. **Hybrid**: Configurable via parameter

**Recommended**: Option 2 (new tool) for A/B testing and backwards compatibility

---

## Non-Functional Requirements

### NFR-1: Performance

**Re-indexing Performance**:
- Full re-index (1,175 entities): ≤2 hours
- Parallelization: Process 10 entities concurrently
- LLM batch requests: Optimize token usage

**Search Performance**:
- No degradation vs current search (<500ms total)
- Context doesn't increase embedding size significantly

### NFR-2: Cost Efficiency

**LLM Costs**:
- Target: <$10 for full re-index (1,175 entities)
- Per-entity cost: <$0.01
- Token optimization: Use smaller models (GPT-3.5 or local Ollama)

**Calculation**:
- 1,175 entities × 300 tokens/entity = 352,500 tokens
- At $0.002/1K tokens (GPT-3.5): **~$0.70 total**
- At local Ollama: **$0 (free)**

### NFR-3: Quality

**Context Quality Target**:
- 90%+ of contexts should be useful (subjective)
- Contains document-level information
- Adds value over isolated chunk

**Validation**:
- Manual review of 50 random samples
- Automated quality checks (length, relevance)

### NFR-4: Scalability

**Future Growth**:
- Support 10,000+ entities
- Streaming re-indexing for large datasets
- Progress tracking and resumability

### NFR-5: Backwards Compatibility

**Requirements**:
- Existing search tools continue working
- Original observations preserved
- Can disable contextualization if needed
- No breaking changes to existing tools

---

## System Architecture

### High-Level Flow

```
Entity Creation (New)
    ↓
Generate Context (LLM)
    ↓
Prepend Context to Observations
    ↓
Store Entity (with context)
    ↓
Embed with NMF (contextualized)
    ↓
Search (better matching!)

Re-indexing (Existing)
    ↓
Retrieve All Entities
    ↓
For Each Entity:
    Generate Context (LLM)
    Update Observations
    Re-embed
    ↓
Complete
```

### Components

**1. Context Generator**
- Uses LLM (Ollama or OpenAI)
- Generates 50-100 word contextual prefixes
- Handles batching and retries
- Quality validation

**2. Re-indexer**
- Iterates through all entities
- Parallel processing (10 concurrent)
- Progress tracking
- Error handling and recovery

**3. Integration Layer**
- Hooks into `create_entities`
- Optional context generation
- Backwards compatible

**4. Search Enhancement**
- New tool: `search_with_contextual_retrieval`
- Uses existing hybrid search
- Searches contextualized chunks

---

## Data Models

### ContextualChunk

**Fields**:
- `chunk_id` (str): Unique identifier
- `original_content` (str): Original chunk text
- `contextual_prefix` (str): Generated context
- `contextualized_content` (str): Prefix + original
- `document_title` (str): Source document title
- `document_type` (str): Source document type
- `generation_timestamp` (datetime): When context was generated
- `quality_score` (float): Context quality (0.0-1.0)
- `token_count` (int): Tokens used for generation

### ReindexingProgress

**Fields**:
- `total_entities` (int): Total to process
- `processed_entities` (int): Completed
- `failed_entities` (List[str]): Failed entity IDs
- `start_time` (datetime): When re-indexing started
- `estimated_completion` (datetime): ETA
- `status` (str): "in_progress", "completed", "failed"

### ContextGenerationRequest

**Fields**:
- `document_content` (str): Full document text
- `chunk_content` (str): Specific chunk to contextualize
- `metadata` (Dict): Document metadata
- `max_words` (int): Maximum context length (default: 100)

---

## API Design

### MCP Tools

#### 1. `generate_context_for_chunk`

**Purpose**: Generate contextual prefix for a single chunk

```python
generate_context_for_chunk(
    chunk: str,
    document: str,
    metadata: Dict[str, Any] = None,
    max_words: int = 100
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "success": True,
    "chunk": "original chunk text",
    "context": "generated contextual prefix",
    "contextualized": "context + chunk",
    "quality_score": 0.85,
    "token_count": 250
}
```

#### 2. `reindex_with_context`

**Purpose**: Re-index all entities with contextual prefixes

```python
reindex_with_context(
    batch_size: int = 10,
    max_workers: int = 10,
    llm_provider: str = "ollama"  # or "openai"
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "success": True,
    "total_entities": 1175,
    "processed": 1175,
    "failed": 0,
    "duration_seconds": 3600,
    "estimated_cost": 0.70,
    "progress": {
        "status": "completed",
        "percentage": 100.0
    }
}
```

#### 3. `get_reindexing_progress`

**Purpose**: Check re-indexing progress

```python
get_reindexing_progress() -> Dict[str, Any]
```

**Returns**:
```python
{
    "status": "in_progress",
    "total_entities": 1175,
    "processed": 500,
    "failed": 2,
    "percentage": 42.6,
    "elapsed_seconds": 1200,
    "estimated_remaining_seconds": 1400
}
```

#### 4. `search_with_contextual_retrieval`

**Purpose**: Search using contextualized chunks

```python
search_with_contextual_retrieval(
    query: str,
    limit: int = 10,
    score_threshold: float = None
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "success": True,
    "query": "authentication database",
    "count": 10,
    "results": [
        {
            "id": "entity-123",
            "content": "contextualized chunk",
            "score": 0.95,
            "metadata": {
                "has_context": True,
                "context_quality": 0.85
            }
        }
    ]
}
```

#### 5. `get_contextual_retrieval_stats`

**Purpose**: Get system statistics

```python
get_contextual_retrieval_stats() -> Dict[str, Any]
```

**Returns**:
```python
{
    "status": "ready",
    "total_entities": 1175,
    "contextualized_entities": 1175,
    "average_context_length": 85,
    "llm_provider": "ollama",
    "total_tokens_used": 352500,
    "estimated_cost": 0.00  # if using Ollama
}
```

---

## Context Generation Algorithm

### Prompt Template

```python
CONTEXT_PROMPT = """You are helping improve search by adding context to text chunks.

Given a document and a specific chunk from that document, generate a brief
(50-100 word) contextual prefix that explains:
1. What this chunk is about
2. How it relates to the larger document
3. Key domain/technical context

Document Title: {title}
Document Type: {doc_type}

Full Document:
{document}

Specific Chunk to Contextualize:
{chunk}

Generate a 50-100 word contextual prefix that will help someone searching
for this information. Be specific and include key terms.

Contextual Prefix:"""
```

### Generation Process

1. **Validate Inputs**:
   - Check chunk is not empty
   - Check document context available
   - Check metadata present

2. **Build Prompt**:
   - Insert document title, type
   - Insert full document (or summary if too long)
   - Insert specific chunk

3. **Call LLM**:
   - Send prompt to LLM (Ollama or OpenAI)
   - Request max 100 tokens output
   - Temperature: 0.3 (for consistency)

4. **Validate Output**:
   - Check length (50-100 words)
   - Check relevance (contains key terms from chunk)
   - Calculate quality score

5. **Return**:
   - Contextual prefix
   - Quality score
   - Token count

---

## Performance Considerations

### Re-indexing Performance

**Challenges**:
- 1,175 entities to process
- LLM calls are slow (~1-2 seconds each)
- Must avoid rate limits

**Optimizations**:
1. **Parallel Processing**: Process 10 entities concurrently
2. **Batching**: Group LLM requests where possible
3. **Progress Tracking**: Save state every 100 entities
4. **Resumability**: Can restart from last checkpoint

**Expected Timeline**:
- Sequential: 1,175 × 2 sec = 2,350 seconds = ~40 minutes
- Parallel (10x): 40 minutes / 10 = **~4 minutes minimum**
- With overhead: **~10-15 minutes total**

### Search Performance

**Impact Analysis**:
- Contextualized chunks are longer (original + 50-100 words)
- Embedding size: Same (768d vectors)
- Search time: No change (same vector operations)
- Storage: +20-30% (additional context text)

**Mitigation**:
- Storage is cheap
- No search performance degradation expected

### Cost Analysis

**LLM Costs**:

Using **Ollama (Local)**:
- Cost: $0 (free)
- Speed: ~1-2 sec/chunk
- Quality: Good (llama3 or mistral)
- **Recommended for production**

Using **OpenAI GPT-3.5**:
- Cost: $0.002/1K tokens
- 1,175 entities × 300 tokens = 352,500 tokens
- Total: **~$0.70**
- Speed: ~0.5-1 sec/chunk
- Quality: Excellent
- **Option for highest quality**

**Recommendation**: Start with Ollama, validate quality, switch to OpenAI if needed

---

## Testing Strategy

### Unit Tests (10 tests)

1. **test_context_generation**: Generate context for single chunk
2. **test_context_quality_validation**: Validate quality checks
3. **test_context_length**: Verify 50-100 word constraint
4. **test_context_relevance**: Check key terms present
5. **test_llm_retry_logic**: Handle LLM failures
6. **test_batching**: Batch processing logic
7. **test_parallel_processing**: Concurrent entity processing
8. **test_progress_tracking**: Progress calculation
9. **test_resumability**: Checkpoint and resume
10. **test_backwards_compatibility**: Original entities unchanged

### Integration Tests (5 tests)

1. **test_reindex_small_dataset**: Re-index 10 entities
2. **test_search_improvement**: Verify accuracy improvement
3. **test_mcp_tools**: All MCP tools accessible
4. **test_cost_tracking**: Token and cost tracking
5. **test_quality_validation**: Manual review of 50 samples

### A/B Testing

**Comparison**:
- Control: Current search (no context)
- Treatment: Contextual retrieval search

**Metrics**:
- Accuracy improvement
- Latency change
- User satisfaction (if applicable)

**Expected Results**:
- +35-49% accuracy (per Anthropic research)
- No latency degradation
- Higher user satisfaction

---

## Rollout Strategy

### Phase 1: Proof of Concept (Day 1)

**Goal**: Validate context generation works

**Tasks**:
1. Implement context generator
2. Test on 10 sample entities
3. Manual quality review
4. Measure token costs

**Success Criteria**:
- Context quality > 0.8
- Cost < $0.01/entity

### Phase 2: Small-Scale Re-indexing (Day 2)

**Goal**: Re-index 100 entities

**Tasks**:
1. Implement re-indexing tool
2. Process 100 entities
3. Validate search improvement
4. Measure performance

**Success Criteria**:
- Re-indexing completes in <5 minutes
- Search accuracy improves
- No errors

### Phase 3: Full Re-indexing (Day 3)

**Goal**: Re-index all 1,175 entities

**Tasks**:
1. Run full re-indexing
2. Monitor progress
3. Validate completion
4. Run A/B tests

**Success Criteria**:
- All entities re-indexed
- +35-49% accuracy improvement
- Cost < $10

### Phase 4: Production Integration (Day 4)

**Goal**: Deploy to production

**Tasks**:
1. Create MCP tools
2. Update documentation
3. Enable for new entities
4. Monitor performance

**Success Criteria**:
- All tools working
- No breaking changes
- Improved search quality

---

## Risk Mitigation

### Risk 1: LLM Quality Insufficient

**Mitigation**:
- Test multiple models (Ollama vs OpenAI)
- Manual quality review of samples
- Fallback to simpler context if needed

### Risk 2: Re-indexing Takes Too Long

**Mitigation**:
- Parallel processing (10 workers)
- Checkpoint progress every 100 entities
- Resume from checkpoint if interrupted

### Risk 3: Cost Too High

**Mitigation**:
- Use Ollama (free) as default
- Monitor token usage
- Batch requests to optimize

### Risk 4: Search Performance Degradation

**Mitigation**:
- Benchmark before/after
- Monitor query latency
- Optimize if needed

---

## Success Metrics

### Implementation Success

- ✅ Context generation working (quality > 0.8)
- ✅ Re-indexing completes successfully
- ✅ All tests passing (100% coverage)
- ✅ Cost within budget (<$10)

### Quality Success

- ✅ +35-49% accuracy improvement (per Anthropic research)
- ✅ Context quality validated (manual review)
- ✅ No search performance degradation

### Production Success

- ✅ All MCP tools deployed
- ✅ No breaking changes
- ✅ Documentation complete
- ✅ Monitoring in place

---

## Future Enhancements

### 1. Dynamic Context Length

**Current**: Fixed 50-100 words
**Future**: Adjust based on chunk complexity

### 2. Multi-Level Context

**Current**: Single contextual prefix
**Future**:
- Document-level context
- Section-level context
- Chunk-level context

### 3. Context Caching

**Current**: Generate fresh each time
**Future**: Cache common contexts to reduce LLM calls

### 4. Learned Context Templates

**Current**: Generic prompt template
**Future**: Domain-specific templates learned from data

---

## Conclusion

Contextual Retrieval (RAG Tier 3.1) addresses a fundamental RAG limitation by adding document-level context to isolated chunks. Anthropic's research validates **+35-49% accuracy improvement** with this approach.

**Key Benefits**:
- Significantly improved search accuracy
- Maintains search performance
- Low cost (especially with Ollama)
- Backwards compatible

**Implementation Plan**:
- Estimated time: 2-3 days
- Estimated cost: <$10 (or $0 with Ollama)
- Expected improvement: +35-49% accuracy

**Next Steps**:
1. Create architecture design document
2. Create implementation plan
3. Implement context generator
4. Implement re-indexing tool
5. Validate with A/B testing
6. Deploy to production

---

**Status**: ✅ SPECIFICATION COMPLETE
**Next**: Architecture Design Document
**Estimated Implementation**: 2-3 days
**Expected Improvement**: +35-49% accuracy
