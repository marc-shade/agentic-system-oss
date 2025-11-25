#!/usr/bin/env python3
"""
Context Synthesis Engine for AGI System
=======================================

Gathers context from multiple sources, scores relevance, resolves conflicts,
and compresses to essential information. Enables agents to work with optimal
context without overwhelming token budgets.

Key Capabilities:
- Multi-source context gathering (files, memory, APIs, sensors)
- Relevance scoring and ranking
- Conflict resolution
- Context compression
- Adaptive context windows
- Token budget optimization

Integration:
- Enhanced Memory for persistent context
- SAFLA for vector similarity
- Code execution for preprocessing
"""

import asyncio
import json
import logging
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ContextSource:
    """Context information source"""
    source_id: str
    source_type: str  # file, memory, api, sensor, etc.
    content: str
    metadata: Dict
    timestamp: datetime
    freshness_score: float  # 0.0-1.0, how recent
    reliability_score: float  # 0.0-1.0, how trustworthy


@dataclass
class ContextChunk:
    """Compressed context chunk"""
    chunk_id: str
    content: str
    relevance_score: float
    token_count: int
    sources: List[str]  # Source IDs
    compressed: bool


@dataclass
class SynthesizedContext:
    """Final synthesized context"""
    context_id: str
    query: str
    chunks: List[ContextChunk]
    total_tokens: int
    compression_ratio: float  # original/final
    synthesis_time_ms: int
    sources_used: List[str]
    metadata: Dict


class ContextSynthesisEngine:
    """
    Synthesizes optimal context from multiple sources with compression
    and relevance scoring for efficient agent operation.
    """

    def __init__(self, max_tokens: int = 100000):
        """Initialize context synthesis engine"""
        self.max_tokens = max_tokens
        self.cache: Dict[str, SynthesizedContext] = {}
        self.cache_ttl = timedelta(minutes=30)

    async def gather_sources(self, query: str, source_types: Optional[List[str]] = None) -> List[ContextSource]:
        """
        Gather context from multiple sources.

        Source types:
        - file: Local files
        - memory: Enhanced memory MCP
        - code: Code repositories
        - docs: Documentation
        - api: External APIs
        - sensors: Arduino/hardware sensors
        """
        sources = []

        # Default to all source types if not specified
        if not source_types:
            source_types = ["file", "memory", "code"]

        # File sources
        if "file" in source_types:
            file_sources = await self._gather_file_sources(query)
            sources.extend(file_sources)

        # Memory sources
        if "memory" in source_types:
            memory_sources = await self._gather_memory_sources(query)
            sources.extend(memory_sources)

        # Code sources
        if "code" in source_types:
            code_sources = await self._gather_code_sources(query)
            sources.extend(code_sources)

        # Documentation sources
        if "docs" in source_types:
            doc_sources = await self._gather_doc_sources(query)
            sources.extend(doc_sources)

        logger.info(f"Gathered {len(sources)} context sources for query: {query}")

        return sources

    async def _gather_file_sources(self, query: str) -> List[ContextSource]:
        """Gather context from local files"""
        sources = []

        # Example: Search for relevant files
        # In production, would use actual file search
        base_path = Path("/mnt/agentic-system")

        # Search for relevant files (simplified)
        for file_path in base_path.rglob("*.py"):
            if file_path.stat().st_size > 1024 * 1024:  # Skip large files
                continue

            try:
                content = file_path.read_text()
                # Simple relevance check
                if any(word.lower() in content.lower() for word in query.split()):
                    sources.append(ContextSource(
                        source_id=str(file_path),
                        source_type="file",
                        content=content[:10000],  # Limit size
                        metadata={"path": str(file_path), "size": len(content)},
                        timestamp=datetime.fromtimestamp(file_path.stat().st_mtime),
                        freshness_score=self._calculate_freshness(
                            datetime.fromtimestamp(file_path.stat().st_mtime)
                        ),
                        reliability_score=0.9
                    ))

                    if len(sources) >= 10:  # Limit sources
                        break
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
                continue

        return sources

    async def _gather_memory_sources(self, query: str) -> List[ContextSource]:
        """Gather context from enhanced memory"""
        sources = []

        # In production, would call enhanced-memory MCP search_nodes
        # Simulated for now
        memory_results = [
            {
                "id": "mem_001",
                "content": f"Memory about {query}",
                "score": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        ]

        for result in memory_results:
            sources.append(ContextSource(
                source_id=result["id"],
                source_type="memory",
                content=result["content"],
                metadata={"score": result["score"]},
                timestamp=datetime.fromisoformat(result["timestamp"]),
                freshness_score=self._calculate_freshness(
                    datetime.fromisoformat(result["timestamp"])
                ),
                reliability_score=result["score"]
            ))

        return sources

    async def _gather_code_sources(self, query: str) -> List[ContextSource]:
        """Gather context from code repositories"""
        # Would use grep/search tools in production
        return []

    async def _gather_doc_sources(self, query: str) -> List[ContextSource]:
        """Gather context from documentation"""
        # Would search documentation in production
        return []

    def _calculate_freshness(self, timestamp: datetime) -> float:
        """Calculate freshness score (0.0-1.0) based on age"""
        age = datetime.now() - timestamp
        days_old = age.total_seconds() / (24 * 3600)

        # Exponential decay - half-life of 7 days
        freshness = 2 ** (-days_old / 7)
        return max(0.0, min(1.0, freshness))

    def score_relevance(self, source: ContextSource, query: str) -> float:
        """
        Score how relevant a source is to the query.

        Factors:
        - Keyword overlap
        - Freshness
        - Reliability
        - Source type priority
        """
        # Keyword overlap
        query_words = set(query.lower().split())
        content_words = set(source.content.lower().split())
        overlap = len(query_words & content_words) / max(len(query_words), 1)

        # Weighted combination
        relevance = (
            overlap * 0.5 +
            source.freshness_score * 0.2 +
            source.reliability_score * 0.3
        )

        return min(1.0, relevance)

    def resolve_conflicts(self, sources: List[ContextSource]) -> List[ContextSource]:
        """
        Resolve conflicting information from different sources.

        Strategy:
        - Prefer more recent information
        - Prefer higher reliability sources
        - Flag conflicts for human review
        """
        # Group by content similarity (simplified)
        content_groups = defaultdict(list)

        for source in sources:
            # Simple grouping by first 100 chars
            key = source.content[:100].lower()
            content_groups[key].append(source)

        resolved = []

        for group in content_groups.values():
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Multiple sources with similar content - pick best
                best = max(group, key=lambda s: (
                    s.freshness_score * 0.5 + s.reliability_score * 0.5
                ))
                resolved.append(best)

        return resolved

    def compress_content(self, content: str, target_ratio: float = 0.3) -> Tuple[str, float]:
        """
        Compress content while preserving key information.

        Methods:
        - Remove redundancy
        - Extract key sentences
        - Summarize paragraphs
        """
        # Simple compression: remove comments, blank lines, excessive whitespace
        lines = content.split('\n')

        # Remove comments
        lines = [line for line in lines if not line.strip().startswith('#')]

        # Remove blank lines
        lines = [line for line in lines if line.strip()]

        # Join and remove excessive whitespace
        compressed = '\n'.join(lines)
        compressed = re.sub(r'\s+', ' ', compressed)

        # Calculate actual compression ratio
        original_size = len(content)
        compressed_size = len(compressed)
        ratio = compressed_size / original_size if original_size > 0 else 1.0

        return compressed, ratio

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimate: 1 token ~= 4 characters
        return len(text) // 4

    async def synthesize(self, query: str, source_types: Optional[List[str]] = None,
                        target_tokens: Optional[int] = None) -> SynthesizedContext:
        """
        Synthesize optimal context for a query.

        Steps:
        1. Gather sources
        2. Score relevance
        3. Resolve conflicts
        4. Compress and prioritize
        5. Fit to token budget
        """
        start_time = datetime.now()

        # Check cache
        cache_key = self._generate_cache_key(query, source_types)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - datetime.fromisoformat(cached.metadata["cached_at"]) < self.cache_ttl:
                logger.info(f"Using cached context for: {query}")
                return cached

        # Use default target if not specified
        if target_tokens is None:
            target_tokens = self.max_tokens // 2  # Use half of max by default

        # Gather sources
        sources = await self.gather_sources(query, source_types)

        # Score relevance
        scored_sources = [(source, self.score_relevance(source, query)) for source in sources]
        scored_sources.sort(key=lambda x: x[1], reverse=True)

        # Resolve conflicts
        resolved_sources = self.resolve_conflicts([s[0] for s in scored_sources])

        # Create chunks and compress
        chunks = []
        total_tokens = 0
        sources_used = []

        for source in resolved_sources:
            if total_tokens >= target_tokens:
                break

            # Compress content
            compressed_content, compression_ratio = self.compress_content(source.content)
            token_count = self._estimate_tokens(compressed_content)

            # Check if it fits
            if total_tokens + token_count <= target_tokens:
                chunk = ContextChunk(
                    chunk_id=hashlib.md5(compressed_content.encode()).hexdigest()[:8],
                    content=compressed_content,
                    relevance_score=self.score_relevance(source, query),
                    token_count=token_count,
                    sources=[source.source_id],
                    compressed=True
                )

                chunks.append(chunk)
                total_tokens = total_tokens + token_count
                sources_used.append(source.source_id)

        # Calculate overall compression
        original_tokens = sum(self._estimate_tokens(s[0].content) for s in scored_sources)
        final_compression = original_tokens / total_tokens if total_tokens > 0 else 1.0

        # Create synthesized context
        synthesis_time = int((datetime.now() - start_time).total_seconds() * 1000)

        context = SynthesizedContext(
            context_id=hashlib.md5(query.encode()).hexdigest()[:16],
            query=query,
            chunks=chunks,
            total_tokens=total_tokens,
            compression_ratio=final_compression,
            synthesis_time_ms=synthesis_time,
            sources_used=sources_used,
            metadata={
                "cached_at": datetime.now().isoformat(),
                "source_types": source_types or ["all"],
                "target_tokens": target_tokens
            }
        )

        # Cache result
        self.cache[cache_key] = context

        logger.info(f"Synthesized context: {len(chunks)} chunks, {total_tokens} tokens, "
                   f"{final_compression:.1f}x compression, {synthesis_time}ms")

        return context

    def _generate_cache_key(self, query: str, source_types: Optional[List[str]]) -> str:
        """Generate cache key for context"""
        types_str = ",".join(sorted(source_types)) if source_types else "all"
        key = f"{query}:{types_str}"
        return hashlib.md5(key.encode()).hexdigest()

    def get_context_summary(self, context: SynthesizedContext) -> Dict:
        """Get summary of synthesized context"""
        return {
            "context_id": context.context_id,
            "query": context.query,
            "total_chunks": len(context.chunks),
            "total_tokens": context.total_tokens,
            "compression_ratio": f"{context.compression_ratio:.1f}x",
            "synthesis_time_ms": context.synthesis_time_ms,
            "sources_used": len(context.sources_used),
            "avg_relevance": sum(c.relevance_score for c in context.chunks) / len(context.chunks) if context.chunks else 0
        }


async def main():
    """Demo of context synthesis engine"""
    engine = ContextSynthesisEngine(max_tokens=100000)

    # Synthesize context for a query
    context = await engine.synthesize(
        query="multi-agent coordination system implementation",
        source_types=["file", "memory"],
        target_tokens=10000
    )

    # Print summary
    summary = engine.get_context_summary(context)
    print("\nContext Synthesis Summary:")
    print(json.dumps(summary, indent=2))

    # Print first chunk
    if context.chunks:
        print(f"\nFirst Chunk (relevance={context.chunks[0].relevance_score:.2f}):")
        print(context.chunks[0].content[:500])
        print("...")


if __name__ == "__main__":
    asyncio.run(main())
