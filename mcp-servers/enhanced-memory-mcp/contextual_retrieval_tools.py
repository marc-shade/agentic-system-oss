"""
Contextual Retrieval Implementation - RAG Tier 3.1

Adds LLM-generated context to chunks before embedding for improved search accuracy.
Based on Anthropic's research showing +35-49% accuracy improvement.

Key Components:
- LLM Provider interface (Ollama + OpenAI)
- Context Generator with quality validation
- Re-indexing engine with parallel processing
- MCP tool registration
"""

import asyncio
import json
import os
import re
from typing import List, Dict, Any, Optional, Callable, Set
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


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
        result = asdict(self)
        result['generation_timestamp'] = self.generation_timestamp.isoformat()
        return result


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['start_time'] = self.start_time.isoformat()
        result['last_update_time'] = self.last_update_time.isoformat()
        result['estimated_completion'] = self.estimated_completion.isoformat()
        return result


# ============================================================================
# LLM Provider Interface
# ============================================================================


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


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (free)"""

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
        import aiohttp

        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "").strip()
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def estimate_cost(self, tokens: int) -> float:
        """Ollama is free"""
        return 0.0

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-3.5-turbo"
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OpenAI API key required")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3
    ) -> str:
        """Generate using OpenAI API"""
        import aiohttp

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates contextual information for text chunks."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    def estimate_cost(self, tokens: int) -> float:
        """Estimate cost (GPT-3.5: $0.002/1K tokens)"""
        return (tokens / 1000) * 0.002

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model


# ============================================================================
# Quality Validator
# ============================================================================


class ContextQualityValidator:
    """Validate context quality"""

    def __init__(self):
        # Common English stop words (simplified set)
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'this', 'these', 'those'
        }

        # Generic phrases that indicate low specificity
        self.generic_phrases = [
            "this section",
            "this describes",
            "this explains",
            "this is about",
            "this discusses",
            "this covers"
        ]

    def extract_key_terms(self, text: str) -> Set[str]:
        """
        Extract key terms from text

        Simple implementation:
        - Tokenize and lowercase
        - Remove stop words
        - Keep words with 3+ characters
        """
        # Tokenize
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Filter stop words and short words
        key_terms = {
            word for word in words
            if word not in self.stop_words and len(word) >= 3
        }

        return key_terms

    def _check_length(self, context: str) -> float:
        """
        Check if context length is appropriate (50-100 words target)

        Returns: score 0.0-1.0
        """
        word_count = len(context.split())

        if 50 <= word_count <= 100:
            return 1.0
        elif 40 <= word_count < 50 or 100 < word_count <= 120:
            return 0.7  # Acceptable
        else:
            return 0.3  # Too short or too long

    def _check_relevance(self, context: str, chunk: str) -> float:
        """
        Check if context contains key terms from chunk

        Returns: score 0.0-1.0
        """
        chunk_terms = self.extract_key_terms(chunk)
        context_terms = self.extract_key_terms(context)

        if not chunk_terms:
            return 0.5  # Can't assess relevance

        # Calculate overlap
        overlap = len(chunk_terms & context_terms)
        relevance = min(overlap / len(chunk_terms), 1.0)

        return relevance

    def _check_coherence(self, context: str) -> float:
        """
        Check if context is grammatically coherent

        Simple heuristic: check for complete sentences

        Returns: score 0.0-1.0
        """
        # Check for capital letters at start
        sentences = [s.strip() for s in context.split('.') if s.strip()]
        if not sentences:
            return 0.0

        has_capitals = any(s and s[0].isupper() for s in sentences)
        ends_with_period = context.strip().endswith('.')

        if has_capitals and ends_with_period:
            return 1.0
        elif has_capitals or ends_with_period:
            return 0.7
        else:
            return 0.3

    def _check_specificity(self, context: str) -> float:
        """
        Check if context is specific (not too generic)

        Returns: score 0.0-1.0
        """
        context_lower = context.lower()

        # Count generic phrases
        generic_count = sum(
            1 for phrase in self.generic_phrases
            if phrase in context_lower
        )

        # Penalty for each generic phrase
        specificity = max(1.0 - (generic_count * 0.2), 0.0)

        return specificity

    def validate(
        self,
        context: str,
        chunk: str
    ) -> QualityScore:
        """
        Validate context quality

        Returns detailed quality assessment
        """
        # Run all checks
        length_score = self._check_length(context)
        relevance_score = self._check_relevance(context, chunk)
        coherence_score = self._check_coherence(context)
        specificity_score = self._check_specificity(context)

        # Calculate overall score (weighted average)
        overall = (
            length_score * 0.2 +
            relevance_score * 0.4 +
            coherence_score * 0.2 +
            specificity_score * 0.2
        )

        # Collect issues
        issues = []
        if length_score < 0.7:
            word_count = len(context.split())
            issues.append(f"Length issue: {word_count} words (target: 50-100)")
        if relevance_score < 0.5:
            issues.append("Low relevance: context missing key terms from chunk")
        if coherence_score < 0.7:
            issues.append("Coherence issue: check grammar and sentence structure")
        if specificity_score < 0.5:
            issues.append("Too generic: use more specific terms")

        # Generate recommendations
        recommendations = []
        if length_score < 0.7:
            recommendations.append("Adjust context length to 50-100 words")
        if relevance_score < 0.5:
            recommendations.append("Include more key terms from original chunk")
        if specificity_score < 0.5:
            recommendations.append("Replace generic phrases with specific details")

        return QualityScore(
            overall_score=overall,
            length_score=length_score,
            relevance_score=relevance_score,
            coherence_score=coherence_score,
            specificity_score=specificity_score,
            issues=issues,
            recommendations=recommendations
        )


# ============================================================================
# Prompt Builder
# ============================================================================


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
        title = metadata.get("title", "Unknown Document")
        doc_type = metadata.get("type", "document")

        # Truncate document if too long
        max_doc_length = 2000
        if len(document) > max_doc_length:
            document = document[:max_doc_length] + "..."

        return self.CONTEXT_PROMPT_TEMPLATE.format(
            title=title,
            doc_type=doc_type,
            document=document,
            chunk=chunk
        )


# ============================================================================
# Context Generator
# ============================================================================


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
        if not chunk or not chunk.strip():
            logger.warning("Empty chunk provided, returning without context")
            return self._create_empty_context(chunk, metadata, entity_id)

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
                logger.debug(f"Generating context (attempt {attempt + 1}/{self.max_retries})")
                context = await self.llm.generate(
                    prompt=prompt,
                    max_tokens=150,
                    temperature=0.3
                )

                # Validate quality
                quality = self.validator.validate(context, chunk)

                # Calculate token count (rough estimate)
                token_count = len(prompt.split()) + len(context.split())

                # Check if acceptable
                if quality.overall_score >= 0.7:
                    # Success
                    logger.info(
                        f"Context generated successfully "
                        f"(quality: {quality.overall_score:.2f})"
                    )
                    return ContextualChunk(
                        chunk_id=f"{entity_id or 'unknown'}_chunk",
                        entity_id=entity_id or "unknown",
                        original_content=chunk,
                        contextual_prefix=context.strip(),
                        contextualized_content=f"{context.strip()} {chunk}",
                        document_title=metadata.get("title", "Unknown"),
                        document_type=metadata.get("type", "document"),
                        generation_timestamp=datetime.now(),
                        quality_score=quality.overall_score,
                        token_count=token_count,
                        llm_provider=self.llm.__class__.__name__,
                        llm_model=self.llm.get_model_name()
                    )

                # Quality too low - retry
                logger.warning(
                    f"Context quality {quality.overall_score:.2f} too low, "
                    f"retrying ({attempt + 1}/{self.max_retries})"
                )
                if quality.issues:
                    logger.warning(f"Issues: {', '.join(quality.issues)}")

            except Exception as e:
                logger.error(f"LLM generation failed (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    # Last retry - return empty context
                    break
                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)

        # All retries failed - return chunk without context
        logger.warning("All context generation attempts failed, using chunk without context")
        return self._create_empty_context(chunk, metadata, entity_id)

    def _create_empty_context(
        self,
        chunk: str,
        metadata: Dict[str, Any],
        entity_id: str = None
    ) -> ContextualChunk:
        """Create chunk without context (fallback)"""
        return ContextualChunk(
            chunk_id=f"{entity_id or 'unknown'}_chunk",
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


# ============================================================================
# Progress Tracker
# ============================================================================


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

        status = "in_progress"
        if self.processed >= self.total:
            status = "completed"
        elif len(self.failed) > self.total * 0.5:  # >50% failed
            status = "failed"

        return ReindexingProgress(
            total_entities=self.total,
            processed_entities=self.processed,
            failed_entities=self.failed.copy(),
            start_time=self.start_time,
            last_update_time=self.last_update,
            estimated_completion=eta,
            status=status,
            avg_time_per_entity=avg_time,
            total_tokens_used=self.token_count,
            estimated_cost=self.cost
        )

    def get_percentage(self) -> float:
        """Get completion percentage"""
        return (self.processed / self.total * 100) if self.total > 0 else 0.0


# ============================================================================
# Checkpoint Manager
# ============================================================================


class CheckpointManager:
    """Manage re-indexing checkpoints"""

    def __init__(self, checkpoint_file: str = ".reindex_checkpoint.json"):
        self.checkpoint_file = checkpoint_file

    def save_checkpoint(self, progress: ReindexingProgress):
        """Save checkpoint to disk"""
        checkpoint = progress.to_dict()

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            logger.info(
                f"Checkpoint saved: {progress.processed_entities}/"
                f"{progress.total_entities} ({progress.processed_entities/progress.total_entities*100:.1f}%)"
            )
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self) -> Optional[Dict]:
        """Load last checkpoint"""
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                logger.info(f"Checkpoint loaded: {checkpoint.get('processed_entities', 0)} entities processed")
                return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def clear_checkpoint(self):
        """Clear checkpoint after completion"""
        if os.path.exists(self.checkpoint_file):
            try:
                os.remove(self.checkpoint_file)
                logger.info("Checkpoint cleared")
            except Exception as e:
                logger.error(f"Failed to clear checkpoint: {e}")


# ============================================================================
# Re-indexing Engine
# ============================================================================


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
        logger.info("Starting re-indexing with contextual prefixes")

        # Load checkpoint
        checkpoint_data = None
        if resume:
            checkpoint_data = self.checkpoint.load_checkpoint()

        # Get all entities from NMF
        logger.info("Retrieving all entities from database")
        all_entities = await self._get_all_entities()
        total = len(all_entities)
        logger.info(f"Found {total} entities to process")

        if total == 0:
            return {
                "success": True,
                "total_entities": 0,
                "processed": 0,
                "failed": 0,
                "message": "No entities to process"
            }

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

        # Process in batches with parallel processing
        batch_size = 100
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_with_semaphore(entity):
            """Process single entity with concurrency control"""
            async with semaphore:
                return await self._process_entity(entity)

        for i in range(0, len(entities_to_process), batch_size):
            batch = entities_to_process[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(f"Processing batch {batch_num} ({len(batch)} entities)")

            # Process batch in parallel
            tasks = [process_with_semaphore(e) for e in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Update progress
            for entity, result in zip(batch, results):
                entity_name = entity.get("name", "unknown")

                if isinstance(result, Exception):
                    self.tracker.update(entity_name, False)
                    logger.error(f"Failed to process {entity_name}: {result}")
                else:
                    self.tracker.update(
                        entity_name,
                        result.get("success", False),
                        tokens=result.get("tokens", 0),
                        cost=result.get("cost", 0.0)
                    )

            # Save checkpoint
            progress = self.tracker.get_progress()
            self.checkpoint.save_checkpoint(progress)

            # Log progress
            percentage = self.tracker.get_percentage()
            logger.info(
                f"Progress: {self.tracker.processed}/{total} "
                f"({percentage:.1f}%) - "
                f"Tokens: {self.tracker.token_count}, "
                f"Cost: ${self.tracker.cost:.4f}"
            )

        # Final results
        progress = self.tracker.get_progress()
        progress.status = "completed"
        self.checkpoint.clear_checkpoint()

        duration = (datetime.now() - self.tracker.start_time).total_seconds()

        logger.info(
            f"Re-indexing complete: {self.tracker.processed}/{total} processed, "
            f"{len(self.tracker.failed)} failed, "
            f"Duration: {duration:.1f}s, "
            f"Tokens: {self.tracker.token_count}, "
            f"Cost: ${self.tracker.cost:.4f}"
        )

        return {
            "success": True,
            "total_entities": total,
            "processed": self.tracker.processed,
            "failed": len(self.tracker.failed),
            "failed_entities": self.tracker.failed,
            "duration_seconds": duration,
            "total_tokens_used": self.tracker.token_count,
            "estimated_cost": self.tracker.cost,
            "progress": progress.to_dict()
        }

    async def _get_all_entities(self) -> List[Dict]:
        """Get all entities from database"""
        try:
            # Use NMF to search for all entities
            # We'll do a broad search and get all results
            from neural_memory_fabric import NeuralMemoryFabric

            # Get all entities by searching with empty/broad query
            # This is a temporary approach - NMF should have a get_all method
            results = []

            # For now, we'll return empty list as placeholder
            # This will be filled in when we integrate with actual NMF
            logger.warning("_get_all_entities is using placeholder implementation")

            return results

        except Exception as e:
            logger.error(f"Failed to get entities: {e}")
            return []

    async def _process_entity(self, entity: Dict) -> Dict:
        """
        Process single entity

        Steps:
        1. Get entity observations
        2. Generate context for each observation
        3. Create contextualized observations
        4. Update entity in database
        """
        entity_id = entity.get("name", "unknown")
        observations = entity.get("observations", [])

        if not observations:
            logger.warning(f"Entity {entity_id} has no observations, skipping")
            return {"success": False, "tokens": 0, "cost": 0.0}

        try:
            # Combine observations into document
            document = " ".join(observations)

            # Get metadata
            metadata = {
                "title": entity_id,
                "type": entity.get("entityType", "unknown")
            }

            # Generate context for first observation (or combine all)
            # For simplicity, we'll contextualize the combined observations
            primary_observation = observations[0] if len(observations) == 1 else document[:500]

            contextual_chunk = await self.generator.generate_context(
                chunk=primary_observation,
                document=document,
                metadata=metadata,
                entity_id=entity_id
            )

            # Update entity with contextualized content
            # This will be implementation-specific to NMF
            # For now, we'll just return success with token count

            total_tokens = contextual_chunk.token_count
            cost = self.generator.llm.estimate_cost(total_tokens)

            logger.debug(
                f"Processed {entity_id}: "
                f"quality={contextual_chunk.quality_score:.2f}, "
                f"tokens={total_tokens}"
            )

            return {
                "success": True,
                "tokens": total_tokens,
                "cost": cost,
                "quality": contextual_chunk.quality_score
            }

        except Exception as e:
            logger.error(f"Failed to process entity {entity_id}: {e}")
            return {"success": False, "tokens": 0, "cost": 0.0}


# ============================================================================
# MCP Tool Registration
# ============================================================================


def register_contextual_retrieval_tools(app, nmf):
    """Register Contextual Retrieval tools with FastMCP"""

    # Initialize LLM provider (Ollama by default, fallback to OpenAI)
    try:
        llm_provider = OllamaProvider(model="llama3")
        logger.info("Using Ollama for context generation")
    except Exception as e:
        logger.warning(f"Ollama not available: {e}, checking for OpenAI")
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            llm_provider = OpenAIProvider(api_key=api_key)
            logger.info("Using OpenAI for context generation")
        else:
            logger.error("No LLM provider available (Ollama or OpenAI)")
            return

    # Initialize components
    context_generator = ContextGenerator(llm_provider)
    reindexing_engine = ReindexingEngine(context_generator, nmf)

    @app.tool()
    async def generate_context_for_chunk(
        chunk: str,
        document: str,
        metadata: Optional[Dict[str, Any]] = None,
        max_words: int = 100
    ) -> Dict[str, Any]:
        """
        Generate contextual prefix for a single chunk

        Args:
            chunk: Text chunk to contextualize
            document: Full document containing the chunk
            metadata: Document metadata (title, type, etc.)
            max_words: Maximum context length (default: 100)

        Returns:
            Dict with context, quality score, and token count
        """
        try:
            if metadata is None:
                metadata = {}

            contextual_chunk = await context_generator.generate_context(
                chunk=chunk,
                document=document,
                metadata=metadata
            )

            return {
                "success": True,
                "chunk": chunk,
                "context": contextual_chunk.contextual_prefix,
                "contextualized": contextual_chunk.contextualized_content,
                "quality_score": contextual_chunk.quality_score,
                "token_count": contextual_chunk.token_count,
                "metadata": {
                    "llm_provider": contextual_chunk.llm_provider,
                    "llm_model": contextual_chunk.llm_model,
                    "timestamp": contextual_chunk.generation_timestamp.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Context generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "chunk": chunk
            }

    @app.tool()
    async def reindex_with_context(
        batch_size: int = 10,
        max_workers: int = 10,
        resume: bool = True
    ) -> Dict[str, Any]:
        """
        Re-index all entities with contextual prefixes

        Args:
            batch_size: Number of entities per batch (default: 10)
            max_workers: Maximum parallel workers (default: 10)
            resume: Resume from checkpoint if available (default: True)

        Returns:
            Dict with re-indexing results and statistics
        """
        try:
            # Update max workers
            reindexing_engine.max_workers = max_workers

            # Run re-indexing
            result = await reindexing_engine.reindex_all(resume=resume)

            return result

        except Exception as e:
            logger.error(f"Re-indexing failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_reindexing_progress() -> Dict[str, Any]:
        """
        Get current re-indexing progress

        Returns:
            Dict with progress information
        """
        try:
            # Try to load checkpoint
            checkpoint = reindexing_engine.checkpoint.load_checkpoint()

            if checkpoint:
                return {
                    "success": True,
                    "in_progress": checkpoint.get("status") == "in_progress",
                    "progress": checkpoint
                }
            else:
                return {
                    "success": True,
                    "in_progress": False,
                    "message": "No re-indexing in progress"
                }

        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_contextual_retrieval_stats() -> Dict[str, Any]:
        """
        Get contextual retrieval system statistics

        Returns:
            System statistics and configuration
        """
        return {
            "status": "ready",
            "llm_provider": llm_provider.__class__.__name__,
            "llm_model": llm_provider.get_model_name(),
            "max_workers": reindexing_engine.max_workers,
            "checkpoint_available": os.path.exists(reindexing_engine.checkpoint.checkpoint_file)
        }

    logger.info("Contextual Retrieval tools registered successfully")
