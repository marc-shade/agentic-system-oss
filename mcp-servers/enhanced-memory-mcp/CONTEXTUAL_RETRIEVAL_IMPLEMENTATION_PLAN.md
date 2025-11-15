# Contextual Retrieval Implementation Plan

**Date**: November 9, 2025
**Status**: Ready for Implementation
**Tier**: RAG Tier 3.1 - Context Enhancement
**Expected Timeline**: 2-3 days
**Expected Improvement**: +35-49% accuracy
**Complexity**: High (7/10)

---

## Executive Summary

This implementation plan provides a step-by-step guide for implementing Contextual Retrieval, Anthropic's proven method for adding LLM-generated context to chunks. The plan follows a phased approach:

**Phase 1**: Core implementation (context generation, quality validation)
**Phase 2**: Re-indexing engine (parallel processing, checkpointing)
**Phase 3**: MCP integration (tools, search integration)
**Phase 4**: Testing and validation
**Phase 5**: Deployment and monitoring

**Prerequisites**:
- ✅ Specification complete
- ✅ Architecture design complete
- ✅ NMF/Qdrant operational
- ✅ Ollama or OpenAI API available

---

## Phase 1: Core Implementation (Day 1, 6-8 hours)

### Step 1.1: Create File Structure (15 minutes)

**File**: `contextual_retrieval_tools.py`

**Initial Structure**:
```python
"""
Contextual Retrieval Implementation - RAG Tier 3.1
Adds LLM-generated context to chunks before embedding
"""
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Data models
# LLM provider interface
# Context generator
# Quality validator
# Re-indexing engine
# MCP tool registration
```

**Verification**: File created with imports and structure comments

---

### Step 1.2: Implement Data Models (30 minutes)

**Component**: Data classes

**Order of Implementation**:

1. **ContextualChunk** (10 minutes):
```python
@dataclass
class ContextualChunk:
    """Chunk with contextual prefix"""
    chunk_id: str
    entity_id: str
    original_content: str
    contextual_prefix: str
    contextualized_content: str
    document_title: str
    document_type: str
    generation_timestamp: datetime
    quality_score: float
    token_count: int
    llm_provider: str
    llm_model: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
```

2. **QualityScore** (10 minutes):
```python
@dataclass
class QualityScore:
    """Context quality assessment"""
    overall_score: float  # 0.0-1.0
    length_score: float
    relevance_score: float
    coherence_score: float
    specificity_score: float
    issues: List[str]
    recommendations: List[str]
```

3. **ReindexingProgress** (10 minutes):
```python
@dataclass
class ReindexingProgress:
    """Re-indexing progress tracking"""
    total_entities: int
    processed_entities: int
    failed_entities: List[str]
    start_time: datetime
    last_update_time: datetime
    estimated_completion: datetime
    status: str  # "in_progress", "completed", "failed"
    avg_time_per_entity: float
    total_tokens_used: int
    estimated_cost: float
```

**Verification**: All data models can serialize to dict

---

### Step 1.3: Implement LLM Provider Interface (45 minutes)

**Component**: Abstract provider + implementations

**1. Abstract Interface** (10 minutes):
```python
class LLMProvider(ABC):
    """Abstract LLM provider interface"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> str:
        """Generate text from prompt"""

    @abstractmethod
    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token count"""

    @abstractmethod
    def get_model_name(self) -> str:
        """Get model name"""
```

**2. Ollama Provider** (20 minutes):
```python
class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, model: str = "llama3"):
        self.model = model
        self.base_url = "http://localhost:11434"

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> str:
        """Generate using Ollama API"""
        # Implementation:
        # 1. Build request to Ollama API
        # 2. POST to /api/generate
        # 3. Stream response
        # 4. Return generated text
```

**3. OpenAI Provider** (15 minutes):
```python
class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo"
    ):
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> str:
        """Generate using OpenAI API"""
        # Implementation:
        # 1. Call OpenAI chat completion
        # 2. Extract response
        # 3. Track tokens
        # 4. Return generated text
```

**Verification**: Test both providers with sample prompt

---

### Step 1.4: Implement Quality Validator (60 minutes)

**Component**: Context quality validation

**1. Key Term Extraction** (15 minutes):
```python
def extract_key_terms(text: str) -> Set[str]:
    """
    Extract key terms from text

    Simple implementation:
    1. Tokenize and lowercase
    2. Remove stop words
    3. Keep nouns, verbs, adjectives (if POS tagging available)
    4. Return unique terms
    """
```

**2. Quality Checks** (45 minutes):
```python
class ContextQualityValidator:
    """Validate context quality"""

    def __init__(self):
        self.stop_words = set([...])  # Common English stop words

    def validate(
        self,
        context: str,
        chunk: str
    ) -> QualityScore:
        """
        Validate context quality

        Returns detailed quality assessment
        """
        # 1. Length check (10 min)
        length_score = self._check_length(context)

        # 2. Relevance check (15 min)
        relevance_score = self._check_relevance(context, chunk)

        # 3. Coherence check (10 min)
        coherence_score = self._check_coherence(context)

        # 4. Specificity check (10 min)
        specificity_score = self._check_specificity(context)

        # 5. Calculate overall score
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
            issues=self._collect_issues(...),
            recommendations=self._generate_recommendations(...)
        )
```

**Verification**: Test with known good/bad contexts

---

### Step 1.5: Implement Prompt Builder (30 minutes)

**Component**: Builds prompts for LLM

```python
class PromptBuilder:
    """Build prompts for context generation"""

    CONTEXT_PROMPT_TEMPLATE = """You are helping improve search by adding context to text chunks.

Given a document and a specific chunk from that document, generate a brief
(50-100 word) contextual prefix that explains:
1. What this chunk is about
2. How it relates to the larger document
3. Key domain/technical context

Document Title: {title}
Document Type: {doc_type}

Full Document (or summary):
{document}

Specific Chunk to Contextualize:
{chunk}

Generate a 50-100 word contextual prefix that will help someone searching
for this information. Be specific and include key terms.

Contextual Prefix:"""

    def build_context_prompt(
        self,
        chunk: str,
        document: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Build prompt for generating contextual prefix

        Steps:
        1. Extract title, type from metadata
        2. Truncate document if too long (>2000 chars)
        3. Fill template
        4. Return prompt
        """
        title = metadata.get("title", "Unknown")
        doc_type = metadata.get("type", "document")

        # Truncate document if too long
        if len(document) > 2000:
            document = document[:2000] + "..."

        return self.CONTEXT_PROMPT_TEMPLATE.format(
            title=title,
            doc_type=doc_type,
            document=document,
            chunk=chunk
        )
```

**Verification**: Test prompt building with sample inputs

---

### Step 1.6: Implement Context Generator (90 minutes)

**Component**: Main context generation logic

```python
class ContextGenerator:
    """Generate contextual prefixes for chunks"""

    def __init__(
        self,
        llm_provider: LLMProvider,
        max_retries: int = 3
    ):
        self.llm = llm_provider
        self.prompt_builder = PromptBuilder()
        self.validator = ContextQualityValidator()
        self.max_retries = max_retries

    async def generate_context(
        self,
        chunk: str,
        document: str,
        metadata: Dict[str, Any],
        entity_id: str = None
    ) -> ContextualChunk:
        """
        Generate context for chunk

        Process:
        1. Build prompt
        2. Call LLM (with retry logic)
        3. Validate quality
        4. Return contextualized chunk
        """
        # Build prompt
        prompt = self.prompt_builder.build_context_prompt(
            chunk=chunk,
            document=document,
            metadata=metadata
        )

        # Generate with retries
        for attempt in range(self.max_retries):
            try:
                # Call LLM
                context = await self.llm.generate(
                    prompt=prompt,
                    max_tokens=150,
                    temperature=0.3
                )

                # Validate quality
                quality = self.validator.validate(context, chunk)

                # Check if acceptable
                if quality.overall_score >= 0.7:
                    # Success
                    return ContextualChunk(
                        chunk_id=f"{entity_id}_chunk",
                        entity_id=entity_id or "unknown",
                        original_content=chunk,
                        contextual_prefix=context.strip(),
                        contextualized_content=f"{context.strip()} {chunk}",
                        document_title=metadata.get("title", "Unknown"),
                        document_type=metadata.get("type", "document"),
                        generation_timestamp=datetime.now(),
                        quality_score=quality.overall_score,
                        token_count=len(prompt.split()) + len(context.split()),
                        llm_provider=self.llm.__class__.__name__,
                        llm_model=self.llm.get_model_name()
                    )

                # Quality too low - retry
                logger.warning(
                    f"Context quality {quality.overall_score:.2f} too low, "
                    f"retrying ({attempt + 1}/{self.max_retries})"
                )

            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                if attempt == self.max_retries - 1:
                    # Last retry - return empty context
                    break

        # All retries failed - return chunk without context
        logger.warning("All context generation attempts failed")
        return ContextualChunk(
            chunk_id=f"{entity_id}_chunk",
            entity_id=entity_id or "unknown",
            original_content=chunk,
            contextual_prefix="",
            contextualized_content=chunk,
            document_title=metadata.get("title", "Unknown"),
            document_type=metadata.get("type", "document"),
            generation_timestamp=datetime.now(),
            quality_score=0.0,
            token_count=0,
            llm_provider=self.llm.__class__.__name__,
            llm_model=self.llm.get_model_name()
        )
```

**Verification**: Test context generation with sample chunks

---

## Phase 2: Re-indexing Engine (Day 1-2, 6-8 hours)

### Step 2.1: Implement Progress Tracker (45 minutes)

**Component**: Track re-indexing progress

```python
class ProgressTracker:
    """Track re-indexing progress"""

    def __init__(self, total_entities: int):
        self.total = total_entities
        self.processed = 0
        self.failed = []
        self.start_time = datetime.now()
        self.last_update = datetime.now()
        self.token_count = 0
        self.cost = 0.0

    def update(
        self,
        entity_id: str,
        success: bool,
        tokens: int = 0,
        cost: float = 0.0
    ):
        """Update progress"""
        self.processed += 1
        self.last_update = datetime.now()
        self.token_count += tokens
        self.cost += cost

        if not success:
            self.failed.append(entity_id)

    def get_progress(self) -> ReindexingProgress:
        """Get current progress"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        avg_time = elapsed / max(self.processed, 1)
        remaining = (self.total - self.processed) * avg_time
        eta = datetime.now() + timedelta(seconds=remaining)

        return ReindexingProgress(
            total_entities=self.total,
            processed_entities=self.processed,
            failed_entities=self.failed,
            start_time=self.start_time,
            last_update_time=self.last_update,
            estimated_completion=eta,
            status="in_progress" if self.processed < self.total else "completed",
            avg_time_per_entity=avg_time,
            total_tokens_used=self.token_count,
            estimated_cost=self.cost
        )

    def get_percentage(self) -> float:
        """Get completion percentage"""
        return (self.processed / self.total * 100) if self.total > 0 else 0.0
```

**Verification**: Test progress tracking with mock data

---

### Step 2.2: Implement Checkpoint Manager (45 minutes)

**Component**: Save and restore checkpoints

```python
import json
import os

class CheckpointManager:
    """Manage re-indexing checkpoints"""

    def __init__(self, checkpoint_file: str = ".reindex_checkpoint.json"):
        self.checkpoint_file = checkpoint_file

    def save_checkpoint(self, progress: ReindexingProgress):
        """Save checkpoint to disk"""
        checkpoint = {
            "total_entities": progress.total_entities,
            "processed_entities": progress.processed_entities,
            "failed_entities": progress.failed_entities,
            "start_time": progress.start_time.isoformat(),
            "last_update_time": progress.last_update_time.isoformat(),
            "status": progress.status,
            "total_tokens_used": progress.total_tokens_used,
            "estimated_cost": progress.estimated_cost
        }

        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        logger.info(f"Checkpoint saved: {progress.processed_entities}/{progress.total_entities}")

    def load_checkpoint(self) -> Optional[Dict]:
        """Load last checkpoint"""
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def clear_checkpoint(self):
        """Clear checkpoint after completion"""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            logger.info("Checkpoint cleared")
```

**Verification**: Test save/load/clear checkpoint

---

### Step 2.3: Implement Re-indexing Engine (120 minutes)

**Component**: Main re-indexing logic

```python
class ReindexingEngine:
    """Re-index entities with contextual prefixes"""

    def __init__(
        self,
        context_generator: ContextGenerator,
        nmf,  # NeuralMemoryFabric instance
        max_workers: int = 10
    ):
        self.generator = context_generator
        self.nmf = nmf
        self.max_workers = max_workers
        self.checkpoint = CheckpointManager()
        self.tracker = None

    async def reindex_all(
        self,
        resume: bool = True
    ) -> Dict[str, Any]:
        """
        Re-index all entities with contextual prefixes

        Process:
        1. Load checkpoint if resume=True
        2. Get all entities
        3. Process in parallel batches
        4. Update database
        5. Save checkpoints
        6. Return results
        """
        # Load checkpoint
        checkpoint_data = None
        if resume:
            checkpoint_data = self.checkpoint.load_checkpoint()

        # Get all entities
        all_entities = await self._get_all_entities()
        total = len(all_entities)

        # Resume from checkpoint
        start_index = 0
        if checkpoint_data:
            start_index = checkpoint_data.get("processed_entities", 0)
            logger.info(f"Resuming from checkpoint: {start_index}/{total}")
            entities_to_process = all_entities[start_index:]
        else:
            entities_to_process = all_entities

        # Initialize progress tracker
        self.tracker = ProgressTracker(total)
        if checkpoint_data:
            # Restore progress
            self.tracker.processed = start_index
            self.tracker.failed = checkpoint_data.get("failed_entities", [])
            self.tracker.token_count = checkpoint_data.get("total_tokens_used", 0)
            self.tracker.cost = checkpoint_data.get("estimated_cost", 0.0)

        # Process in batches
        batch_size = 100
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(entity):
            """Process single entity with concurrency control"""
            async with semaphore:
                return await self._process_entity(entity)

        for i in range(0, len(entities_to_process), batch_size):
            batch = entities_to_process[i:i + batch_size]

            # Process batch in parallel
            tasks = [process_with_semaphore(e) for e in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Update progress
            for entity, result in zip(batch, results):
                if isinstance(result, Exception):
                    self.tracker.update(entity["name"], False)
                    logger.error(f"Failed to process {entity['name']}: {result}")
                else:
                    self.tracker.update(
                        entity["name"],
                        True,
                        tokens=result.get("tokens", 0),
                        cost=result.get("cost", 0.0)
                    )

            # Save checkpoint
            progress = self.tracker.get_progress()
            self.checkpoint.save_checkpoint(progress)

            # Log progress
            percentage = self.tracker.get_percentage()
            logger.info(
                f"Progress: {self.tracker.processed}/{total} ({percentage:.1f}%)"
            )

        # Final results
        progress = self.tracker.get_progress()
        progress.status = "completed"
        self.checkpoint.clear_checkpoint()

        return {
            "success": True,
            "total_entities": total,
            "processed": self.tracker.processed,
            "failed": len(self.tracker.failed),
            "failed_entities": self.tracker.failed,
            "duration_seconds": (datetime.now() - self.tracker.start_time).total_seconds(),
            "total_tokens_used": self.tracker.token_count,
            "estimated_cost": self.tracker.cost,
            "progress": progress.to_dict()
        }

    async def _get_all_entities(self) -> List[Dict]:
        """Get all entities from database"""
        # Use NMF to get all entities
        # This will be implementation-specific
        return []  # Placeholder

    async def _process_entity(self, entity: Dict) -> Dict:
        """
        Process single entity

        Steps:
        1. Get entity observations
        2. Generate context for each observation
        3. Create contextualized observations
        4. Update entity in database
        """
        entity_id = entity.get("name")
        observations = entity.get("observations", [])

        contextualized_obs = []
        total_tokens = 0

        for obs in observations:
            # Generate context
            contextual_chunk = await self.generator.generate_context(
                chunk=obs,
                document=" ".join(observations),  # Use all observations as document
                metadata={
                    "title": entity_id,
                    "type": entity.get("entityType", "unknown")
                },
                entity_id=entity_id
            )

            # Add contextualized observation
            contextualized_obs.append(contextual_chunk.contextualized_content)
            total_tokens += contextual_chunk.token_count

        # Update entity
        # (Implementation will use NMF update method)

        return {
            "success": True,
            "tokens": total_tokens,
            "cost": self.generator.llm.estimate_cost(total_tokens)
        }
```

**Verification**: Test re-indexing with small dataset (10 entities)

---

## Phase 3: MCP Integration (Day 2, 4-6 hours)

### Step 3.1: Implement MCP Tools (90 minutes)

**Tools to Create**:

1. **`generate_context_for_chunk`** (20 minutes)
2. **`reindex_with_context`** (30 minutes)
3. **`get_reindexing_progress`** (15 minutes)
4. **`search_with_contextual_retrieval`** (15 minutes)
5. **`get_contextual_retrieval_stats`** (10 minutes)

**Implementation** (see specification for detailed API design)

**Verification**: Each tool callable via MCP

---

### Step 3.2: Server Integration (30 minutes)

**File**: `server.py` (add after multi-query RAG, around line 1021)

```python
# Register Contextual Retrieval tools (RAG Tier 3 Strategy) - Context Enhancement
if nmf_instance:
    try:
        from contextual_retrieval_tools import register_contextual_retrieval_tools
        register_contextual_retrieval_tools(app, nmf_instance)
        logger.info("✅ Contextual Retrieval (RAG Tier 3) integrated - Expected +35-49% accuracy")
    except Exception as e:
        logger.warning(f"⚠️  Contextual Retrieval integration skipped: {e}")
else:
    logger.warning("⚠️  Contextual Retrieval skipped: NMF not available")
```

**Verification**: Server starts, logs show integration

---

## Phase 4: Testing (Day 2-3, 4-6 hours)

### Step 4.1: Unit Tests (120 minutes)

**File**: `test_contextual_retrieval.py`

**Tests** (10 total):
1. test_context_generation
2. test_quality_validation (length, relevance, coherence, specificity)
3. test_llm_retry_logic
4. test_progress_tracking
5. test_checkpoint_save_load
6. test_parallel_processing
7. test_provider_fallback
8. test_error_handling
9. test_data_model_conversion
10. test_backwards_compatibility

**Verification**: All unit tests pass

---

### Step 4.2: Integration Tests (90 minutes)

**File**: `test_contextual_retrieval_mcp.py`

**Tests** (5 total):
1. test_generate_context_tool
2. test_reindex_small_dataset (10 entities)
3. test_search_improvement
4. test_mcp_tools_availability
5. test_cost_tracking

**Verification**: All integration tests pass

---

### Step 4.3: Manual Quality Review (60 minutes)

**Process**:
1. Re-index 50 random entities
2. Manual review of contexts
3. Rate quality (1-5 scale)
4. Document findings

**Success Criteria**: Average quality ≥ 4.0/5.0

---

## Phase 5: Deployment (Day 3, 2-4 hours)

### Step 5.1: Full Re-indexing (60-90 minutes)

**Process**:
1. Run `reindex_with_context` on all 1,175 entities
2. Monitor progress
3. Handle any failures
4. Validate completion

**Expected Time**: 10-15 minutes actual re-indexing + monitoring

---

### Step 5.2: A/B Testing (60 minutes)

**Comparison**:
- Control: Current search (no context)
- Treatment: Contextual retrieval search

**Metrics**:
- Accuracy improvement
- Latency change
- Sample query performance

**Expected**: +35-49% accuracy improvement

---

### Step 5.3: Documentation (60 minutes)

**Documents to Create**:
1. Implementation documentation
2. Session summary
3. Update status documents

---

## Success Criteria

### Implementation Success
- ✅ All components implemented
- ✅ All tests passing (15+ tests)
- ✅ Re-indexing completes successfully
- ✅ Cost within budget (<$10 or $0 with Ollama)

### Quality Success
- ✅ Context quality ≥ 0.8 average
- ✅ +35-49% accuracy improvement (validated)
- ✅ No search performance degradation

### Production Success
- ✅ All MCP tools working
- ✅ No breaking changes
- ✅ Complete documentation
- ✅ Monitoring in place

---

## Risk Mitigation

See specification document for detailed risk mitigation strategies.

---

## Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Core Implementation | 6-8 hours | Day 1 |
| Phase 2: Re-indexing Engine | 6-8 hours | Day 1-2 |
| Phase 3: MCP Integration | 4-6 hours | Day 2 |
| Phase 4: Testing | 4-6 hours | Day 2-3 |
| Phase 5: Deployment | 2-4 hours | Day 3 |

**Total**: 2-3 days

---

## Conclusion

This implementation plan provides a complete roadmap for Contextual Retrieval. Following this plan will result in:

- ✅ Production-ready contextual retrieval
- ✅ +35-49% accuracy improvement (per Anthropic research)
- ✅ Complete test coverage
- ✅ Full documentation
- ✅ Cost-effective implementation

**Status**: ✅ PLANNING COMPLETE
**Ready for**: Implementation
**Next Action**: Begin Phase 1 - Core Implementation

---

**Implementation Plan Complete**
**Date**: November 9, 2025
**Ready for**: Full Implementation
**Expected Duration**: 2-3 days
**Expected Improvement**: +35-49% accuracy
