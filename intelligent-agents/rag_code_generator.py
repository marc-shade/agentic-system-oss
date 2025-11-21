#!/usr/bin/env python3
"""
RAG Code Generator
==================

Retrieval-Augmented Generation system for code optimization.
Stores successful modifications and retrieves similar patterns to improve code generation quality.

Research Foundation:
- RAP-Gen (arXiv:2309.06057): Retrieval-Augmented Planning + Generation
- WizardCoder: Evol-Instruct methodology

Key Features:
- Code embedding using sentence-transformers (code-specific model)
- Storage in Qdrant vector database + enhanced-memory for metadata
- Similarity-based retrieval of past successful modifications
- Context building from historical patterns
- LLM generation augmented with retrieved knowledge

Integration:
- Works with autonomous_recursive_agi_loop.py
- Stores in Qdrant collection "code_modifications"
- Uses enhanced-memory-mcp for structured metadata
- Connects to Ollama for code generation
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import sys

# Third-party imports
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from sentence_transformers import SentenceTransformer

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logger = logging.getLogger("rag-code-generator")


class CodeEmbedder:
    """
    Code embedding using sentence-transformers.

    Uses a model optimized for code similarity rather than general text.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize code embedder.

        Args:
            model_name: HuggingFace model name
                        Default is fast/efficient general model
                        For production, consider: "microsoft/codebert-base" or "codeparrot/codeparrot-small"
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self.embedding_dim}")

    def embed(self, code: str) -> List[float]:
        """
        Embed code into vector representation.

        Args:
            code: Source code string

        Returns:
            Vector embedding as list of floats
        """
        # Normalize code: remove extra whitespace, standardize formatting
        normalized = self._normalize_code(code)

        # Generate embedding
        embedding = self.model.encode(normalized, convert_to_numpy=True)

        return embedding.tolist()

    def embed_batch(self, codes: List[str]) -> List[List[float]]:
        """
        Embed multiple code snippets efficiently.

        Args:
            codes: List of source code strings

        Returns:
            List of vector embeddings
        """
        normalized = [self._normalize_code(c) for c in codes]
        embeddings = self.model.encode(normalized, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    @staticmethod
    def _normalize_code(code: str) -> str:
        """
        Normalize code for better embedding similarity.

        - Remove excessive whitespace
        - Standardize indentation
        - Keep semantic structure
        """
        lines = code.split('\n')
        normalized_lines = []

        for line in lines:
            # Strip trailing whitespace but preserve leading indentation structure
            stripped = line.rstrip()
            if stripped:  # Skip empty lines
                normalized_lines.append(stripped)

        return '\n'.join(normalized_lines)


class RAGCodeGenerator:
    """
    Retrieval-Augmented Generation for code optimization.

    Workflow:
    1. Store successful modifications with embeddings
    2. When generating new code, retrieve similar past modifications
    3. Build context from retrieved patterns
    4. Generate code using LLM with augmented context
    5. Quality improves from learning past successes
    """

    COLLECTION_NAME = "code_modifications"

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        ollama_host: str = "http://localhost:11434",
<<<<<<< HEAD
        base_path: str = "/Volumes/SSDRAID0/agentic-system"
=======
        base_path: str = "/mnt/agentic-system"
>>>>>>> origin/main
    ):
        """
        Initialize RAG Code Generator.

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            ollama_host: Ollama API endpoint
            base_path: Base path for system files
        """
        self.base_path = Path(base_path)

        # Initialize code embedder
        logger.info("Initializing code embedder...")
        self.embedder = CodeEmbedder()

        # Connect to Qdrant
        logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}")
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)

        # Ollama configuration
        self.ollama_host = ollama_host

        # Initialize collection
        self._ensure_collection_exists()

        logger.info("RAG Code Generator initialized successfully")

    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists with correct configuration."""
        collections = self.qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.COLLECTION_NAME not in collection_names:
            logger.info(f"Creating Qdrant collection: {self.COLLECTION_NAME}")
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.embedder.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info("Collection created successfully")
        else:
            logger.info(f"Collection {self.COLLECTION_NAME} already exists")

    async def store_successful_modification(
        self,
        modification_id: str,
        target_function: str,
        code_before: str,
        code_after: str,
        optimization_type: str,
        performance_gain: float,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a successful code modification for future retrieval.

        Args:
            modification_id: Unique identifier
            target_function: Name of function/module modified
            code_before: Original code
            code_after: Optimized code
            optimization_type: Type of optimization (e.g., "algorithm", "caching", "vectorization")
            performance_gain: Percentage improvement (e.g., 15.7 for 15.7%)
            reasoning: Explanation of why this optimization worked
            metadata: Additional metadata

        Returns:
            Point ID in Qdrant
        """
        logger.info(f"Storing modification {modification_id}: {optimization_type} (+{performance_gain}%)")

        # Generate embedding from code_after (the optimized version)
        embedding = self.embedder.embed(code_after)

        # Create payload with all modification data
        payload = {
            "modification_id": modification_id,
            "target_function": target_function,
            "code_before": code_before,
            "code_after": code_after,
            "optimization_type": optimization_type,
            "performance_gain": performance_gain,
            "reasoning": reasoning,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        # Generate unique point ID from modification content
        point_id = self._generate_point_id(modification_id)

        # Store in Qdrant
        self.qdrant.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )

        logger.info(f"Stored in Qdrant with point_id: {point_id}")

        # Also store metadata in enhanced-memory for structured queries
        await self._store_in_enhanced_memory(modification_id, payload)

        return str(point_id)

    async def _store_in_enhanced_memory(self, modification_id: str, payload: Dict):
        """Store modification metadata in enhanced-memory for structured access."""
        try:
            # Import here to avoid circular dependencies
            sys.path.insert(0, str(self.base_path / "mcp-servers" / "enhanced-memory-mcp"))
            from server import create_entities

            entity = {
                "name": f"code_modification_{modification_id}",
                "entityType": "code_optimization",
                "observations": [
                    f"target: {payload['target_function']}",
                    f"type: {payload['optimization_type']}",
                    f"gain: {payload['performance_gain']}%",
                    f"reasoning: {payload['reasoning']}"
                ]
            }

            await create_entities([entity])
            logger.info(f"Stored metadata in enhanced-memory")

        except Exception as e:
            logger.warning(f"Could not store in enhanced-memory: {e}")
            # Non-critical: Qdrant storage is primary

    async def retrieve_similar_modifications(
        self,
        target_code: str,
        limit: int = 5,
        min_performance_gain: float = 5.0,
        optimization_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past modifications using vector similarity.

        Args:
            target_code: Code to optimize (query)
            limit: Maximum number of results
            min_performance_gain: Minimum performance improvement to consider
            optimization_type: Filter by optimization type (optional)

        Returns:
            List of similar modifications with metadata
        """
        logger.info(f"Retrieving similar modifications (limit={limit}, min_gain={min_performance_gain}%)")

        # Embed target code
        query_vector = self.embedder.embed(target_code)

        # Build filter
        filter_conditions = []
        filter_conditions.append(
            FieldCondition(
                key="performance_gain",
                range={"gte": min_performance_gain}
            )
        )

        if optimization_type:
            filter_conditions.append(
                FieldCondition(
                    key="optimization_type",
                    match=MatchValue(value=optimization_type)
                )
            )

        # Search Qdrant
        search_results = self.qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            query_filter=Filter(must=filter_conditions) if filter_conditions else None,
            with_payload=True,
            with_vectors=False
        )

        # Format results
        modifications = []
        for result in search_results:
            mod = result.payload.copy()
            mod['similarity_score'] = result.score
            modifications.append(mod)

        logger.info(f"Retrieved {len(modifications)} similar modifications")

        return modifications

    def _build_context_from_history(self, similar_modifications: List[Dict]) -> str:
        """
        Build context string from retrieved modifications.

        Format examples in a clear, structured way for LLM consumption.
        """
        if not similar_modifications:
            return "No similar past optimizations found."

        context_parts = ["SIMILAR PAST OPTIMIZATIONS:\n"]

        for i, mod in enumerate(similar_modifications, 1):
            context_parts.append(f"\n--- Example {i} (Similarity: {mod['similarity_score']:.2f}, Gain: +{mod['performance_gain']}%) ---")
            context_parts.append(f"Type: {mod['optimization_type']}")
            context_parts.append(f"Target: {mod['target_function']}")
            context_parts.append(f"\nBefore:\n{mod['code_before']}")
            context_parts.append(f"\nAfter:\n{mod['code_after']}")
            context_parts.append(f"\nReasoning: {mod['reasoning']}\n")

        return '\n'.join(context_parts)

    async def generate_with_rag(
        self,
        target_code: str,
        target_function: str,
        insights: List[str],
        optimization_goal: str = "performance"
    ) -> Tuple[str, str]:
        """
        Generate optimized code using retrieval-augmented generation.

        Args:
            target_code: Code to optimize
            target_function: Name of function/module
            insights: Recent insights from research/analysis
            optimization_goal: Goal (performance, memory, readability, etc.)

        Returns:
            (optimized_code, reasoning)
        """
        logger.info(f"Generating optimized code for: {target_function}")

        # Step 1: Retrieve similar past modifications
        similar = await self.retrieve_similar_modifications(
            target_code=target_code,
            limit=5,
            min_performance_gain=5.0
        )

        # Step 2: Build context from history
        context = self._build_context_from_history(similar)

        # Step 3: Build prompt with retrieved context
        insights_text = "\n".join(f"- {insight}" for insight in insights)

        prompt = f"""You are an expert code optimizer with access to historical optimization patterns.

OPTIMIZATION GOAL: {optimization_goal}

{context}

RECENT INSIGHTS:
{insights_text}

CURRENT CODE TO OPTIMIZE:
Function: {target_function}
```python
{target_code}
```

TASK:
Based on the similar past optimizations and recent insights, generate an optimized version of the current code.
Follow successful patterns from the examples above. Explain your reasoning clearly.

Return in this exact format:
OPTIMIZED CODE:
```python
[your optimized code here]
```

REASONING:
[explain what you changed and why, referencing similar patterns]
"""

        # Step 4: Call LLM
        try:
            response = await self._call_ollama(prompt)

            # Step 5: Parse response
            optimized_code, reasoning = self._parse_llm_response(response)

            logger.info(f"Generated optimized code ({len(optimized_code)} chars)")

            return optimized_code, reasoning

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def _call_ollama(self, prompt: str, model: str = "gpt-oss:20b") -> str:
        """
        Call Ollama API for code generation.

        Args:
            prompt: Generation prompt
            model: Model name

        Returns:
            Generated text
        """
        import aiohttp

        url = f"{self.ollama_host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,  # Lower temperature for more consistent code
                "num_predict": 2048
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama API error: {resp.status}")

                data = await resp.json()
                return data.get("response", "")

    def _parse_llm_response(self, response: str) -> Tuple[str, str]:
        """
        Parse LLM response to extract code and reasoning.

        Expected format:
        OPTIMIZED CODE:
        ```python
        [code]
        ```

        REASONING:
        [reasoning]
        """
        # Extract code block
        code_start = response.find("```python")
        code_end = response.find("```", code_start + 9)

        if code_start == -1 or code_end == -1:
            raise ValueError("Could not parse LLM response: no code block found")

        code = response[code_start + 9:code_end].strip()

        # Extract reasoning
        reasoning_start = response.find("REASONING:", code_end)
        if reasoning_start == -1:
            reasoning = "No reasoning provided"
        else:
            reasoning = response[reasoning_start + 10:].strip()

        return code, reasoning

    @staticmethod
    def _generate_point_id(modification_id: str) -> int:
        """Generate consistent numeric point ID from string ID."""
        hash_obj = hashlib.md5(modification_id.encode())
        # Use first 8 bytes of hash as integer
        return int.from_bytes(hash_obj.digest()[:8], byteorder='big') % (2**63 - 1)

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored modifications."""
        collection_info = self.qdrant.get_collection(self.COLLECTION_NAME)

        # Get all points to analyze
        scroll_result = self.qdrant.scroll(
            collection_name=self.COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )

        points = scroll_result[0]

        # Analyze
        total = len(points)
        if total == 0:
            return {"total_modifications": 0}

        gains = [p.payload['performance_gain'] for p in points]
        types = {}
        for p in points:
            opt_type = p.payload['optimization_type']
            types[opt_type] = types.get(opt_type, 0) + 1

        return {
            "total_modifications": total,
            "avg_performance_gain": sum(gains) / len(gains),
            "max_performance_gain": max(gains),
            "optimization_types": types,
            "collection_size_bytes": collection_info.vectors_count
        }


async def main():
    """Test RAG Code Generator."""
    logger.info("Testing RAG Code Generator...")

    rag = RAGCodeGenerator()

    # Store some example successful modifications
    logger.info("\n=== Storing Example Modifications ===")

    # Example 1: List comprehension optimization
    await rag.store_successful_modification(
        modification_id="example_001",
        target_function="process_data",
        code_before="""
result = []
for item in data:
    if item > 0:
        result.append(item * 2)
return result
""",
        code_after="""
return [item * 2 for item in data if item > 0]
""",
        optimization_type="list_comprehension",
        performance_gain=23.5,
        reasoning="Replaced explicit loop with list comprehension. Faster due to C-level iteration and no repeated append calls."
    )

    # Example 2: Caching optimization
    await rag.store_successful_modification(
        modification_id="example_002",
        target_function="calculate_fibonacci",
        code_before="""
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
""",
        code_after="""
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
""",
        optimization_type="memoization",
        performance_gain=99.8,
        reasoning="Added memoization using lru_cache. Eliminates exponential time complexity by caching results."
    )

    # Example 3: Vectorization
    await rag.store_successful_modification(
        modification_id="example_003",
        target_function="apply_transformation",
        code_before="""
result = []
for value in values:
    result.append(math.sqrt(value) * 2.5)
return result
""",
        code_after="""
import numpy as np
return np.sqrt(np.array(values)) * 2.5
""",
        optimization_type="vectorization",
        performance_gain=87.3,
        reasoning="Replaced Python loop with NumPy vectorization. Orders of magnitude faster for large arrays."
    )

    logger.info("\n=== Retrieving Similar Modifications ===")

    # Test retrieval with similar code
    test_code = """
filtered = []
for x in numbers:
    if x % 2 == 0:
        filtered.append(x * x)
return filtered
"""

    similar = await rag.retrieve_similar_modifications(test_code, limit=3)

    logger.info(f"Found {len(similar)} similar modifications:")
    for mod in similar:
        logger.info(f"  - {mod['optimization_type']}: +{mod['performance_gain']}% (similarity: {mod['similarity_score']:.3f})")

    logger.info("\n=== Generating with RAG ===")

    # Test generation
    optimized, reasoning = await rag.generate_with_rag(
        target_code=test_code,
        target_function="filter_and_square",
        insights=[
            "List comprehensions are faster than explicit loops",
            "Avoid repeated list.append() calls"
        ],
        optimization_goal="performance"
    )

    logger.info(f"\nOptimized Code:\n{optimized}")
    logger.info(f"\nReasoning:\n{reasoning}")

    logger.info("\n=== Statistics ===")
    stats = await rag.get_statistics()
    logger.info(json.dumps(stats, indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
