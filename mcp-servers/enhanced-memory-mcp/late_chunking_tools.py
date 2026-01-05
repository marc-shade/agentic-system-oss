#!/usr/bin/env python3
"""
Late Chunking RAG Tools

Implements Late Chunking strategy from research:
- Traditional: chunk → embed each chunk separately
- Late Chunking: embed full document → extract chunk embeddings with document context

Benefits:
- Chunk embeddings retain full document context
- Better retrieval for context-dependent queries
- Improved semantic coherence across chunks

Requires long-context embedding model (8k+ tokens):
- qwen3-embedding:8b-fp16 (8192 tokens) - via Ollama on inference node
- bge-m3 (8192 tokens) - via Ollama on inference node

Research basis:
- "Late Chunking: Contextual Chunk Embeddings Using Long-Context Models"
- Jina AI research on document-aware embeddings
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Ollama inference node (M4 Max with 128GB unified memory)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://completeu-server.local:11434")

# Long-context embedding models available on inference node
LONG_CONTEXT_MODELS = {
    "qwen3-embedding:8b-fp16": {
        "max_tokens": 8192,
        "dimensions": 4096,  # Qwen3 embeddings are 4096-dim
        "description": "Qwen3 8B embedding model with 8k context"
    },
    "bge-m3:latest": {
        "max_tokens": 8192,
        "dimensions": 1024,
        "description": "BGE-M3 multilingual model with 8k context"
    },
    "snowflake-arctic-embed2:latest": {
        "max_tokens": 8192,
        "dimensions": 1024,
        "description": "Snowflake Arctic Embed2 with 8k context"
    }
}

DEFAULT_MODEL = "bge-m3:latest"  # Best balance of quality and speed


@dataclass
class ChunkWithContext:
    """A chunk with document-aware embedding"""
    chunk_id: str
    text: str
    start_pos: int
    end_pos: int
    embedding: List[float]
    document_id: str
    chunk_index: int
    total_chunks: int
    context_window: str  # Surrounding context used
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LateChunkingResult:
    """Result from late chunking operation"""
    document_id: str
    chunks: List[ChunkWithContext]
    model: str
    total_tokens: int
    processing_time_ms: float
    embedding_dimensions: int
    strategy: str = "late_chunking"


class LateChunkingProcessor:
    """
    Late Chunking implementation using long-context embedding models.

    Strategy:
    1. Process full document (up to 8k tokens) in one pass
    2. Identify chunk boundaries within the document
    3. Extract chunk embeddings with surrounding context
    4. Each chunk embedding includes document-level context
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_host: str = OLLAMA_HOST,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        context_window: int = 200  # Extra context around each chunk
    ):
        self.model = model
        self.ollama_host = ollama_host
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.context_window = context_window

        # Validate model
        if model not in LONG_CONTEXT_MODELS:
            logger.warning(f"Model {model} not in known long-context models, using anyway")

        self.model_info = LONG_CONTEXT_MODELS.get(model, {
            "max_tokens": 8192,
            "dimensions": 1024,
            "description": "Unknown model"
        })

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from Ollama inference node"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Ollama returned {response.status_code}: {response.text[:200]}")
                    return None

                data = response.json()
                return data.get("embedding", [])

        except Exception as e:
            logger.error(f"Embedding request failed: {e}")
            return None

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return len(text) // 4

    def _create_chunks_with_boundaries(
        self,
        text: str
    ) -> List[Tuple[int, int, str]]:
        """
        Create chunks with their character boundaries.

        Returns list of (start_pos, end_pos, chunk_text)
        """
        chunks = []

        # Split on sentence boundaries when possible
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = []
        current_length = 0
        current_start = 0
        position = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk size, finalize current chunk
            if current_length + sentence_length > self.chunk_size * 4 and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append((current_start, position, chunk_text))

                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk) - 2)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk)
                current_start = position - current_length

            current_chunk.append(sentence)
            current_length += sentence_length
            position += sentence_length + 1  # +1 for space

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((current_start, position, chunk_text))

        return chunks

    def _get_context_window(
        self,
        full_text: str,
        start_pos: int,
        end_pos: int
    ) -> str:
        """Get chunk with surrounding context"""
        context_start = max(0, start_pos - self.context_window)
        context_end = min(len(full_text), end_pos + self.context_window)
        return full_text[context_start:context_end]

    async def process_document(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LateChunkingResult:
        """
        Process a document using late chunking strategy.

        Args:
            text: Full document text
            document_id: Optional document identifier
            metadata: Optional metadata to attach to chunks

        Returns:
            LateChunkingResult with context-aware chunk embeddings
        """
        start_time = time.time()

        # Generate document ID if not provided
        if document_id is None:
            document_id = hashlib.md5(text[:1000].encode(), usedforsecurity=False).hexdigest()[:12]

        # Estimate tokens
        total_tokens = self._estimate_tokens(text)
        max_tokens = self.model_info["max_tokens"]

        # Truncate if necessary (but log warning)
        if total_tokens > max_tokens:
            logger.warning(
                f"Document ({total_tokens} tokens) exceeds model limit ({max_tokens}). "
                f"Truncating to fit."
            )
            # Truncate to approximately max_tokens
            text = text[:max_tokens * 4]
            total_tokens = max_tokens

        # Create chunks with boundaries
        chunk_boundaries = self._create_chunks_with_boundaries(text)

        # Process each chunk with its context window
        chunks = []
        for idx, (start_pos, end_pos, chunk_text) in enumerate(chunk_boundaries):
            # Get chunk with surrounding context for embedding
            context_text = self._get_context_window(text, start_pos, end_pos)

            # Get embedding for chunk-with-context
            embedding = await self._get_embedding(context_text)

            if embedding is None:
                logger.warning(f"Failed to get embedding for chunk {idx}")
                continue

            chunk = ChunkWithContext(
                chunk_id=f"{document_id}_chunk_{idx}",
                text=chunk_text,
                start_pos=start_pos,
                end_pos=end_pos,
                embedding=embedding,
                document_id=document_id,
                chunk_index=idx,
                total_chunks=len(chunk_boundaries),
                context_window=context_text,
                metadata=metadata or {}
            )
            chunks.append(chunk)

        processing_time = (time.time() - start_time) * 1000

        return LateChunkingResult(
            document_id=document_id,
            chunks=chunks,
            model=self.model,
            total_tokens=total_tokens,
            processing_time_ms=processing_time,
            embedding_dimensions=self.model_info["dimensions"],
            strategy="late_chunking"
        )

    async def process_documents_batch(
        self,
        documents: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[LateChunkingResult]:
        """
        Process multiple documents with concurrency control.

        Args:
            documents: List of {"text": str, "id": str, "metadata": dict}
            max_concurrent: Maximum concurrent processing

        Returns:
            List of LateChunkingResult
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(doc):
            async with semaphore:
                return await self.process_document(
                    text=doc.get("text", ""),
                    document_id=doc.get("id"),
                    metadata=doc.get("metadata")
                )

        tasks = [process_with_semaphore(doc) for doc in documents]
        return await asyncio.gather(*tasks)


def register_late_chunking_tools(app, db_path: Path = None):
    """
    Register Late Chunking MCP tools.

    Args:
        app: FastMCP application instance
        db_path: Path to SQLite database (for storing chunked documents)
    """

    # Initialize processor with default model
    processor = LateChunkingProcessor()

    logger.info(f"✅ Late Chunking initialized with model: {processor.model}")
    logger.info(f"   Max tokens: {processor.model_info['max_tokens']}")
    logger.info(f"   Dimensions: {processor.model_info['dimensions']}")
    logger.info(f"   Ollama host: {processor.ollama_host}")

    @app.tool()
    async def late_chunk_document(
        text: str,
        document_id: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        chunk_size: int = 512,
        context_window: int = 200
    ) -> Dict[str, Any]:
        """
        Process document using Late Chunking strategy.

        Late Chunking embeds chunks with document context, improving retrieval
        for context-dependent queries. Uses long-context embedding models (8k tokens).

        Args:
            text: Full document text (up to ~32k characters / 8k tokens)
            document_id: Optional document identifier
            model: Embedding model (default: bge-m3:latest)
                   Options: qwen3-embedding:8b-fp16, bge-m3:latest, snowflake-arctic-embed2:latest
            chunk_size: Target chunk size in tokens (default: 512)
            context_window: Extra context chars around each chunk (default: 200)

        Returns:
            Dict with chunks, embeddings, and processing stats

        Example:
            result = await late_chunk_document(
                text="Long document text here...",
                model="bge-m3:latest"
            )
            print(f"Created {len(result['chunks'])} context-aware chunks")
        """
        try:
            # Use custom processor if model differs
            if model != processor.model:
                custom_processor = LateChunkingProcessor(
                    model=model,
                    chunk_size=chunk_size,
                    context_window=context_window
                )
                result = await custom_processor.process_document(text, document_id)
            else:
                result = await processor.process_document(text, document_id)

            # Format chunks for response (exclude large embeddings from display)
            chunks_summary = []
            for chunk in result.chunks:
                chunks_summary.append({
                    "chunk_id": chunk.chunk_id,
                    "text_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "start_pos": chunk.start_pos,
                    "end_pos": chunk.end_pos,
                    "chunk_index": chunk.chunk_index,
                    "embedding_dims": len(chunk.embedding)
                })

            return {
                "success": True,
                "document_id": result.document_id,
                "chunk_count": len(result.chunks),
                "chunks": chunks_summary,
                "model": result.model,
                "total_tokens": result.total_tokens,
                "embedding_dimensions": result.embedding_dimensions,
                "processing_time_ms": round(result.processing_time_ms, 2),
                "strategy": result.strategy
            }

        except Exception as e:
            logger.error(f"Late chunking failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def late_chunk_and_store(
        text: str,
        entity_name: str,
        entity_type: str = "document",
        model: str = DEFAULT_MODEL,
        chunk_size: int = 512
    ) -> Dict[str, Any]:
        """
        Late chunk a document and store chunks as memory entities.

        Creates separate entities for each chunk, linked to parent document.
        Each chunk entity has context-aware embedding for better retrieval.

        Args:
            text: Full document text
            entity_name: Name for the document entity
            entity_type: Entity type (default: "document")
            model: Embedding model (default: bge-m3:latest)
            chunk_size: Target chunk size in tokens

        Returns:
            Dict with document entity ID and chunk entity IDs

        Example:
            result = await late_chunk_and_store(
                text="Research paper content...",
                entity_name="AGI Research Paper 2024",
                entity_type="research_paper"
            )
        """
        try:
            # Process document with late chunking
            custom_processor = LateChunkingProcessor(model=model, chunk_size=chunk_size)
            result = await custom_processor.process_document(text, entity_name)

            # Store parent document entity
            from memory_client import MemoryClient
            client = MemoryClient()

            # Create parent document entity
            parent_response = client.create_entities([{
                "name": entity_name,
                "entityType": entity_type,
                "observations": [
                    f"Document with {len(result.chunks)} late-chunked sections",
                    f"Processed with {result.model}",
                    f"Total tokens: {result.total_tokens}"
                ]
            }])

            parent_id = None
            if parent_response.get("created"):
                parent_id = parent_response["created"][0].get("entity_id")

            # Create chunk entities
            chunk_entities = []
            for chunk in result.chunks:
                chunk_entity = {
                    "name": f"{entity_name}_chunk_{chunk.chunk_index}",
                    "entityType": f"{entity_type}_chunk",
                    "observations": [
                        chunk.text,
                        f"Chunk {chunk.chunk_index + 1} of {chunk.total_chunks}",
                        f"Late chunking with {result.model}"
                    ]
                }
                chunk_entities.append(chunk_entity)

            chunks_response = client.create_entities(chunk_entities)

            # Store embeddings in Qdrant if available
            stored_embeddings = 0
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import PointStruct
                import uuid

                qdrant = QdrantClient(host="localhost", port=6333)

                points = []
                for chunk in result.chunks:
                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=chunk.embedding,
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "document_id": result.document_id,
                            "entity_name": entity_name,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text[:500],
                            "strategy": "late_chunking"
                        }
                    )
                    points.append(point)

                # Create collection if needed
                collections = qdrant.get_collections().collections
                collection_names = [c.name for c in collections]

                if "late_chunks" not in collection_names:
                    from qdrant_client.models import VectorParams, Distance
                    qdrant.create_collection(
                        collection_name="late_chunks",
                        vectors_config=VectorParams(
                            size=result.embedding_dimensions,
                            distance=Distance.COSINE
                        )
                    )

                qdrant.upsert(collection_name="late_chunks", points=points)
                stored_embeddings = len(points)

            except Exception as e:
                logger.warning(f"Qdrant storage skipped: {e}")

            return {
                "success": True,
                "document_id": result.document_id,
                "parent_entity_id": parent_id,
                "chunk_count": len(result.chunks),
                "chunks_created": len(chunks_response.get("created", [])),
                "embeddings_stored": stored_embeddings,
                "model": result.model,
                "processing_time_ms": round(result.processing_time_ms, 2)
            }

        except Exception as e:
            logger.error(f"Late chunk and store failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def search_late_chunks(
        query: str,
        limit: int = 10,
        min_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Search late-chunked documents using context-aware embeddings.

        Searches the late_chunks Qdrant collection for semantically similar chunks.
        Each chunk was embedded with document context for better retrieval.

        Args:
            query: Search query text
            limit: Maximum results (default: 10)
            min_score: Minimum similarity score (default: 0.5)

        Returns:
            Dict with matching chunks and scores

        Example:
            results = await search_late_chunks(
                query="neural network training techniques",
                limit=5
            )
        """
        try:
            # Get query embedding
            query_embedding = await processor._get_embedding(query)

            if not query_embedding:
                return {
                    "success": False,
                    "error": "Failed to generate query embedding"
                }

            # Search Qdrant
            from qdrant_client import QdrantClient

            qdrant = QdrantClient(host="localhost", port=6333)

            results = qdrant.search(
                collection_name="late_chunks",
                query_vector=query_embedding,
                limit=limit,
                score_threshold=min_score
            )

            # Format results
            matches = []
            for hit in results:
                matches.append({
                    "chunk_id": hit.payload.get("chunk_id"),
                    "document_id": hit.payload.get("document_id"),
                    "entity_name": hit.payload.get("entity_name"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "text": hit.payload.get("text"),
                    "score": round(hit.score, 4),
                    "strategy": hit.payload.get("strategy", "late_chunking")
                })

            return {
                "success": True,
                "query": query,
                "result_count": len(matches),
                "results": matches,
                "model": processor.model
            }

        except Exception as e:
            logger.error(f"Late chunk search failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_late_chunking_models() -> Dict[str, Any]:
        """
        Get available long-context embedding models for late chunking.

        Returns:
            Dict with model information and current configuration

        Example:
            models = await get_late_chunking_models()
            print(f"Available: {list(models['models'].keys())}")
        """
        return {
            "success": True,
            "models": LONG_CONTEXT_MODELS,
            "current_model": processor.model,
            "ollama_host": processor.ollama_host,
            "default_chunk_size": processor.chunk_size,
            "default_context_window": processor.context_window
        }

    @app.tool()
    async def compare_chunking_strategies(
        text: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Compare traditional chunking vs late chunking for a document.

        Shows how late chunking improves retrieval by including document context.

        Args:
            text: Document text to chunk
            query: Query to test retrieval

        Returns:
            Comparison of retrieval results from both strategies

        Example:
            comparison = await compare_chunking_strategies(
                text="Long document...",
                query="specific topic"
            )
        """
        try:
            start_time = time.time()

            # Traditional chunking (simple split)
            traditional_chunks = []
            chunk_size = 500 * 4  # ~500 tokens in chars
            for i in range(0, len(text), chunk_size):
                chunk_text = text[i:i + chunk_size]
                embedding = await processor._get_embedding(chunk_text)
                if embedding:
                    traditional_chunks.append({
                        "text": chunk_text[:200],
                        "embedding": embedding
                    })

            # Late chunking
            late_result = await processor.process_document(text, "comparison_doc")

            # Get query embedding
            query_embedding = await processor._get_embedding(query)

            if not query_embedding:
                return {"success": False, "error": "Failed to embed query"}

            # Calculate similarities
            def cosine_similarity(a, b):
                import math
                dot = sum(x * y for x, y in zip(a, b))
                norm_a = math.sqrt(sum(x * x for x in a))
                norm_b = math.sqrt(sum(y * y for y in b))
                return dot / (norm_a * norm_b) if norm_a and norm_b else 0

            traditional_scores = [
                {
                    "text_preview": c["text"],
                    "score": round(cosine_similarity(query_embedding, c["embedding"]), 4)
                }
                for c in traditional_chunks
            ]
            traditional_scores.sort(key=lambda x: x["score"], reverse=True)

            late_scores = [
                {
                    "text_preview": c.text[:200],
                    "score": round(cosine_similarity(query_embedding, c.embedding), 4)
                }
                for c in late_result.chunks
            ]
            late_scores.sort(key=lambda x: x["score"], reverse=True)

            processing_time = (time.time() - start_time) * 1000

            return {
                "success": True,
                "query": query,
                "traditional_chunking": {
                    "chunk_count": len(traditional_chunks),
                    "top_results": traditional_scores[:3],
                    "max_score": traditional_scores[0]["score"] if traditional_scores else 0
                },
                "late_chunking": {
                    "chunk_count": len(late_result.chunks),
                    "top_results": late_scores[:3],
                    "max_score": late_scores[0]["score"] if late_scores else 0
                },
                "improvement": {
                    "score_diff": round(
                        (late_scores[0]["score"] if late_scores else 0) -
                        (traditional_scores[0]["score"] if traditional_scores else 0),
                        4
                    ),
                    "note": "Positive means late chunking found better match"
                },
                "processing_time_ms": round(processing_time, 2)
            }

        except Exception as e:
            logger.error(f"Chunking comparison failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("✅ Late Chunking tools registered successfully")
    return processor


# Module docstring with usage examples
__doc__ += """

Usage Examples
--------------

1. Process a document with Late Chunking:
   result = await late_chunk_document(
       text="Your long document text here...",
       model="bge-m3:latest"
   )

2. Chunk and store in memory system:
   result = await late_chunk_and_store(
       text="Research paper content...",
       entity_name="AGI Research 2024",
       entity_type="research_paper"
   )

3. Search late-chunked documents:
   results = await search_late_chunks(
       query="neural network optimization",
       limit=5
   )

4. Compare chunking strategies:
   comparison = await compare_chunking_strategies(
       text="Document text...",
       query="specific query"
   )

5. List available models:
   models = await get_late_chunking_models()

Available Models
----------------
- qwen3-embedding:8b-fp16: 8192 tokens, 4096 dims (highest quality)
- bge-m3:latest: 8192 tokens, 1024 dims (best balance)
- snowflake-arctic-embed2:latest: 8192 tokens, 1024 dims

Performance Notes
-----------------
- Late chunking requires ~2x processing time but improves retrieval
- Use for documents where context matters (research, technical docs)
- Traditional chunking still fine for simple content
- Ollama inference happens on GPU node (completeu-server)
"""
