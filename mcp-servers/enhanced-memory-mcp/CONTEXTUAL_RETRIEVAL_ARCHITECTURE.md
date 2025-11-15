# Contextual Retrieval Architecture Design

**Date**: November 9, 2025
**Status**: Planning Phase
**Tier**: RAG Tier 3.1 - Context Enhancement
**Expected Improvement**: +35-49% accuracy

---

## Executive Summary

This document provides the detailed architecture design for Contextual Retrieval, implementing Anthropic's proven method of adding LLM-generated context to chunks before embedding. The architecture emphasizes:

- **Modularity**: Separate components for generation, re-indexing, and search
- **Performance**: Parallel processing for efficient re-indexing
- **Quality**: Multiple validation layers for context quality
- **Backwards Compatibility**: No breaking changes to existing systems

---

## System Architecture Overview

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tools Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Generate   │  │  Re-index    │  │  Search with     │  │
│  │   Context    │  │  with        │  │  Contextual      │  │
│  │              │  │  Context     │  │  Retrieval       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Core Components Layer                      │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Context          │  │  Re-indexing     │                │
│  │ Generator        │  │  Engine          │                │
│  │                  │  │                  │                │
│  │ - LLM Integration│  │ - Parallel Proc  │                │
│  │ - Quality Check  │  │ - Progress Track │                │
│  │ - Retry Logic    │  │ - Checkpointing  │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Integration Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  NMF/Qdrant      │  │  Enhanced Memory │                │
│  │  Interface       │  │  Database        │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Context Generator

**Responsibility**: Generate contextual prefixes for chunks using LLM

#### Sub-Components

**1.1 LLM Provider Interface**

Abstraction layer supporting multiple LLM providers:

```python
class LLMProvider(ABC):
    """Abstract LLM provider interface"""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from prompt"""

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token count"""
```

**Implementations**:
- `OllamaProvider`: Local Ollama (free, ~1-2 sec/call)
- `OpenAIProvider`: GPT-3.5/4 (paid, ~0.5-1 sec/call)

**1.2 Prompt Builder**

Constructs prompts for context generation:

```python
class PromptBuilder:
    """Build prompts for context generation"""

    def build_context_prompt(
        self,
        chunk: str,
        document: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Build prompt for generating contextual prefix

        Template:
        - Document title and type
        - Full document (or summary if long)
        - Specific chunk to contextualize
        - Instructions for 50-100 word context
        """
```

**1.3 Quality Validator**

Validates generated context quality:

```python
class ContextQualityValidator:
    """Validate context quality"""

    def validate(self, context: str, chunk: str) -> QualityScore:
        """
        Validate context quality

        Checks:
        1. Length: 50-100 words
        2. Relevance: Contains key terms from chunk
        3. Coherence: Grammatically correct
        4. Specificity: Not too generic

        Returns:
        - quality_score: 0.0-1.0
        - issues: List of quality issues
        - recommendations: Improvement suggestions
        """
```

**1.4 Context Generator (Main)**

Orchestrates generation process:

```python
class ContextGenerator:
    """Generate contextual prefixes for chunks"""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.prompt_builder = PromptBuilder()
        self.validator = ContextQualityValidator()

    async def generate_context(
        self,
        chunk: str,
        document: str,
        metadata: Dict[str, Any],
        max_retries: int = 3
    ) -> ContextualChunk:
        """
        Generate context for chunk

        Process:
        1. Build prompt
        2. Call LLM (with retry logic)
        3. Validate quality
        4. Return contextualized chunk
        """
```

#### Data Flow

```
Input: Chunk + Document + Metadata
    ↓
PromptBuilder.build_context_prompt()
    ↓
LLMProvider.generate() (with retries)
    ↓
ContextQualityValidator.validate()
    ↓
Quality OK? → Return ContextualChunk
Quality Low? → Retry (up to 3 times)
Quality Failed? → Return with warning
```

---

### 2. Re-indexing Engine

**Responsibility**: Re-index all entities with contextual prefixes

#### Sub-Components

**2.1 Entity Retriever**

Retrieves entities from database:

```python
class EntityRetriever:
    """Retrieve entities for re-indexing"""

    async def get_all_entities(self) -> List[Entity]:
        """Get all entities from database"""

    async def get_entities_batch(
        self,
        offset: int,
        limit: int
    ) -> List[Entity]:
        """Get batch of entities for parallel processing"""
```

**2.2 Parallel Processor**

Processes entities in parallel:

```python
class ParallelProcessor:
    """Process entities in parallel"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.executor = asyncio.Semaphore(max_workers)

    async def process_batch(
        self,
        entities: List[Entity],
        processor_func: Callable
    ) -> List[Result]:
        """
        Process batch of entities in parallel

        Uses asyncio.gather with semaphore for concurrency control
        """
```

**2.3 Progress Tracker**

Tracks re-indexing progress:

```python
class ProgressTracker:
    """Track re-indexing progress"""

    def __init__(self, total_entities: int):
        self.total = total_entities
        self.processed = 0
        self.failed = []
        self.start_time = datetime.now()

    def update(self, entity_id: str, success: bool):
        """Update progress"""

    def get_progress(self) -> ReindexingProgress:
        """Get current progress"""

    def get_eta(self) -> datetime:
        """Calculate estimated time to completion"""
```

**2.4 Checkpoint Manager**

Saves and restores checkpoints:

```python
class CheckpointManager:
    """Manage re-indexing checkpoints"""

    def save_checkpoint(self, progress: ReindexingProgress):
        """Save checkpoint to disk"""

    def load_checkpoint(self) -> Optional[ReindexingProgress]:
        """Load last checkpoint"""

    def clear_checkpoint(self):
        """Clear checkpoint after completion"""
```

**2.5 Re-indexing Engine (Main)**

Orchestrates re-indexing:

```python
class ReindexingEngine:
    """Re-index entities with contextual prefixes"""

    def __init__(
        self,
        context_generator: ContextGenerator,
        nmf: NeuralMemoryFabric,
        max_workers: int = 10
    ):
        self.generator = context_generator
        self.nmf = nmf
        self.retriever = EntityRetriever(nmf)
        self.processor = ParallelProcessor(max_workers)
        self.tracker = None
        self.checkpoint = CheckpointManager()

    async def reindex_all(
        self,
        resume: bool = True
    ) -> ReindexingResult:
        """
        Re-index all entities

        Process:
        1. Load checkpoint if resume=True
        2. Get all entities
        3. Process in parallel batches
        4. Update each entity in database
        5. Save checkpoints every 100 entities
        6. Return results
        """

    async def process_entity(
        self,
        entity: Entity
    ) -> EntityResult:
        """
        Process single entity

        Steps:
        1. Generate context for observations
        2. Create contextualized observations
        3. Update entity in database
        4. Re-embed with NMF
        """
```

#### Data Flow

```
Start Re-indexing
    ↓
Load Checkpoint (if resume=True)
    ↓
Retrieve All Entities (batched)
    ↓
For Each Batch:
    ├─ Entity 1 ──┐
    ├─ Entity 2 ──┤
    ├─ Entity 3 ──┤  Parallel Processing
    ├─ ...        │  (10 concurrent)
    └─ Entity 10 ─┘
        ↓
    Generate Context (LLM)
        ↓
    Update Entity (Database)
        ↓
    Re-embed (NMF)
        ↓
Update Progress
    ↓
Save Checkpoint (every 100)
    ↓
Repeat Until Complete
```

---

### 3. Search Integration

**Responsibility**: Integrate contextual retrieval with search

#### Components

**3.1 Contextual Search**

Uses existing hybrid search on contextualized chunks:

```python
class ContextualSearch:
    """Search using contextualized chunks"""

    def __init__(self, nmf: NeuralMemoryFabric):
        self.nmf = nmf

    async def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = None
    ) -> SearchResults:
        """
        Search contextualized chunks

        Process:
        1. Use existing hybrid search
        2. Chunks are already contextualized
        3. Return results (no special handling needed)

        Note: The improvement comes from better embeddings,
        not from changing the search algorithm
        """
```

**Key Insight**: Once entities are re-indexed with context, existing search tools automatically benefit. No special search logic needed!

---

## Data Models

### ContextualChunk

```python
@dataclass
class ContextualChunk:
    """Chunk with contextual prefix"""

    # Identifiers
    chunk_id: str
    entity_id: str

    # Content
    original_content: str        # Original chunk
    contextual_prefix: str       # Generated context
    contextualized_content: str  # Prefix + original

    # Metadata
    document_title: str
    document_type: str
    generation_timestamp: datetime
    quality_score: float
    token_count: int

    # Provider info
    llm_provider: str
    llm_model: str
```

### ReindexingProgress

```python
@dataclass
class ReindexingProgress:
    """Re-indexing progress tracking"""

    # Counts
    total_entities: int
    processed_entities: int
    failed_entities: List[str]

    # Timing
    start_time: datetime
    last_update_time: datetime
    estimated_completion: datetime

    # Status
    status: str  # "in_progress", "completed", "failed"
    current_batch: int

    # Metrics
    avg_time_per_entity: float
    total_tokens_used: int
    estimated_cost: float
```

### EntityResult

```python
@dataclass
class EntityResult:
    """Result of processing single entity"""

    entity_id: str
    success: bool
    error_message: Optional[str]

    # Context info
    contexts_generated: int
    quality_scores: List[float]
    tokens_used: int

    # Timing
    processing_time: float
```

### QualityScore

```python
@dataclass
class QualityScore:
    """Context quality assessment"""

    overall_score: float  # 0.0-1.0

    # Component scores
    length_score: float      # Is length 50-100 words?
    relevance_score: float   # Contains key terms?
    coherence_score: float   # Grammatically correct?
    specificity_score: float # Not too generic?

    # Details
    issues: List[str]
    recommendations: List[str]
```

---

## Algorithms

### Context Generation Algorithm

```python
async def generate_context(chunk, document, metadata):
    """
    Generate contextual prefix for chunk

    Input:
    - chunk: Original chunk text
    - document: Full document text
    - metadata: {title, type, tags, etc.}

    Output:
    - ContextualChunk with prefix and quality score
    """

    # Step 1: Build prompt
    prompt = build_prompt(
        chunk=chunk,
        document=document,
        title=metadata.get("title"),
        doc_type=metadata.get("type")
    )

    # Step 2: Generate with retry
    for attempt in range(max_retries):
        try:
            # Call LLM
            context = await llm.generate(
                prompt=prompt,
                max_tokens=150,  # ~100 words
                temperature=0.3   # Consistent output
            )

            # Step 3: Validate quality
            quality = validate_quality(context, chunk)

            # Step 4: Check if acceptable
            if quality.overall_score >= 0.7:
                # Success - return result
                return ContextualChunk(
                    original_content=chunk,
                    contextual_prefix=context,
                    contextualized_content=f"{context} {chunk}",
                    quality_score=quality.overall_score,
                    # ... other fields
                )

            # Quality too low - retry
            logger.warning(
                f"Context quality {quality.overall_score} too low, "
                f"retrying ({attempt + 1}/{max_retries})"
            )

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")

    # All retries failed
    return ContextualChunk(
        original_content=chunk,
        contextual_prefix="",  # Empty context
        contextualized_content=chunk,  # Just original
        quality_score=0.0,
        # ... other fields
    )
```

### Quality Validation Algorithm

```python
def validate_quality(context: str, chunk: str) -> QualityScore:
    """
    Validate context quality

    Returns score 0.0-1.0 and detailed breakdown
    """

    # 1. Length score (50-100 words target)
    word_count = len(context.split())
    if 50 <= word_count <= 100:
        length_score = 1.0
    elif 40 <= word_count < 50 or 100 < word_count <= 120:
        length_score = 0.7  # Acceptable
    else:
        length_score = 0.3  # Too short or too long

    # 2. Relevance score (contains key terms from chunk)
    chunk_terms = extract_key_terms(chunk)
    context_terms = extract_key_terms(context)
    overlap = len(chunk_terms & context_terms)
    relevance_score = min(overlap / len(chunk_terms), 1.0)

    # 3. Coherence score (grammatically correct)
    # Simple heuristic: check for complete sentences
    sentences = context.split(".")
    has_capital = any(s.strip() and s.strip()[0].isupper() for s in sentences)
    has_period = context.strip().endswith(".")
    coherence_score = 1.0 if has_capital and has_period else 0.5

    # 4. Specificity score (not too generic)
    generic_phrases = [
        "this section",
        "this describes",
        "this explains",
        "this is about"
    ]
    generic_count = sum(
        1 for phrase in generic_phrases
        if phrase in context.lower()
    )
    specificity_score = max(1.0 - (generic_count * 0.2), 0.0)

    # Overall score (weighted average)
    overall = (
        length_score * 0.2 +
        relevance_score * 0.4 +
        coherence_score * 0.2 +
        specificity_score * 0.2
    )

    return QualityScore(
        overall_score=overall,
        length_score=length_score,
        relevance_score=relevance_score,
        coherence_score=coherence_score,
        specificity_score=specificity_score,
        issues=collect_issues(...),
        recommendations=generate_recommendations(...)
    )
```

### Parallel Re-indexing Algorithm

```python
async def reindex_all_entities(
    entities: List[Entity],
    max_workers: int = 10
):
    """
    Re-index all entities in parallel

    Uses batching and semaphore for concurrency control
    """

    # Initialize
    progress = ProgressTracker(total=len(entities))
    semaphore = asyncio.Semaphore(max_workers)

    async def process_with_semaphore(entity):
        """Process single entity with semaphore"""
        async with semaphore:
            return await process_entity(entity)

    # Process in batches for checkpointing
    batch_size = 100
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]

        # Process batch in parallel (up to max_workers concurrent)
        tasks = [process_with_semaphore(e) for e in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Update progress
        for entity, result in zip(batch, results):
            if isinstance(result, Exception):
                progress.mark_failed(entity.id, str(result))
            else:
                progress.mark_completed(entity.id)

        # Save checkpoint
        save_checkpoint(progress)

        # Log progress
        logger.info(
            f"Progress: {progress.processed}/{progress.total} "
            f"({progress.percentage:.1f}%)"
        )

    return progress.to_result()
```

---

## Error Handling

### Graceful Degradation Levels

**Level 1: Retry with Backoff**
- LLM call fails → Retry up to 3 times with exponential backoff
- Wait: 1s, 2s, 4s

**Level 2: Fallback to Simple Context**
- All retries fail → Generate simple context from metadata
- Example: "This is from document '{title}' of type '{type}'"

**Level 3: No Context**
- Even simple context fails → Use original chunk without context
- Log warning, entity still gets indexed

**Level 4: Skip Entity**
- Critical failure → Skip entity, mark as failed
- Continue with other entities
- Can retry failed entities later

### Error Recovery

```python
class ErrorHandler:
    """Handle errors during processing"""

    async def handle_llm_error(
        self,
        error: Exception,
        chunk: str,
        metadata: Dict
    ) -> ContextualChunk:
        """
        Handle LLM generation error

        Fallback strategy:
        1. If timeout → retry with lower max_tokens
        2. If rate limit → wait and retry
        3. If API error → use simple context from metadata
        4. If all else fails → return original chunk
        """

    def log_error(self, error: Exception, context: Dict):
        """Log error with context for debugging"""

    async def notify_failure(self, entity_id: str, error: str):
        """Notify about entity processing failure"""
```

---

## Performance Architecture

### Parallel Processing Strategy

```
Batch 1 (100 entities)
┌────────────────────────────────────────┐
│ Worker 1: Entity 1                     │
│ Worker 2: Entity 2                     │
│ Worker 3: Entity 3                     │
│ ...                                    │
│ Worker 10: Entity 10                   │
│                                        │
│ (Next 10 when workers free)            │
│ Worker 1: Entity 11                    │
│ ...                                    │
└────────────────────────────────────────┘
        ↓ Checkpoint saved
Batch 2 (100 entities)
...
```

**Benefits**:
- 10x speedup from parallelization
- Checkpoint every 100 entities (resumable)
- Controlled concurrency (avoid overwhelming LLM API)

### Cost Optimization

**Strategy 1: Use Ollama (Free)**
- Cost: $0
- Speed: ~1-2 sec/chunk
- Quality: Good (llama3/mistral)
- **Recommended for production**

**Strategy 2: Batch Requests**
- Group multiple chunks in single LLM call
- Reduces API overhead
- More complex parsing

**Strategy 3: Cache Common Contexts**
- Cache contexts for common chunk patterns
- Reduces duplicate generation
- Saves tokens and time

---

## Testing Architecture

### Test Pyramid

```
                    ┌─────────────┐
                    │   Manual    │
                    │   Review    │
                    │  (50 samples)│
                    └─────────────┘
                 ┌──────────────────┐
                 │   Integration    │
                 │     Tests        │
                 │   (5 tests)      │
                 └──────────────────┘
            ┌────────────────────────────┐
            │      Unit Tests            │
            │     (10 tests)             │
            └────────────────────────────┘
```

### Test Coverage Matrix

| Component | Unit Tests | Integration Tests | Manual Review |
|-----------|------------|-------------------|---------------|
| Context Generator | ✅ | ✅ | ✅ |
| Quality Validator | ✅ | ❌ | ✅ |
| Re-indexing Engine | ✅ | ✅ | ❌ |
| Parallel Processor | ✅ | ❌ | ❌ |
| Search Integration | ❌ | ✅ | ✅ |

---

## Deployment Architecture

### Phase 1: Development

```
Local Environment
├─ Ollama (local LLM)
├─ Test database (100 entities)
└─ Development server
```

### Phase 2: Staging

```
Staging Environment
├─ Ollama or OpenAI
├─ Staging database (1,175 entities)
├─ A/B testing framework
└─ Monitoring and logging
```

### Phase 3: Production

```
Production Environment
├─ Ollama (primary) + OpenAI (fallback)
├─ Production database
├─ Full monitoring and alerting
├─ Cost tracking
└─ Performance metrics
```

---

## Conclusion

This architecture provides a robust, scalable, and cost-effective implementation of Contextual Retrieval. Key design decisions:

- **Modularity**: Clear separation of concerns
- **Resilience**: Multiple fallback levels
- **Performance**: Parallel processing with checkpointing
- **Quality**: Multi-level validation
- **Cost**: Ollama as primary, OpenAI as fallback

**Expected Results**:
- +35-49% accuracy improvement (per Anthropic research)
- <$10 total cost (or $0 with Ollama)
- 10-15 minutes re-indexing time
- No search performance degradation

---

**Status**: ✅ ARCHITECTURE DESIGN COMPLETE
**Next**: Implementation Plan
**Ready for**: Implementation
