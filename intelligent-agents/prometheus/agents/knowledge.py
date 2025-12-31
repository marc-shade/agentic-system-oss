"""
Knowledge Agent - Retrieves information from multiple sources.

Priority order (from Manus patterns):
1. enhanced-memory (our persistent memory)
2. Datasource APIs (authoritative sources)
3. Web search (internet)
4. Research papers (academic sources)
5. Internal knowledge (LLM training data - last resort)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of knowledge sources."""
    MEMORY = "enhanced_memory"
    API = "datasource_api"
    WEB = "web_search"
    RESEARCH = "research_papers"
    INTERNAL = "internal_knowledge"


@dataclass
class KnowledgeItem:
    """Single piece of retrieved knowledge."""
    content: str
    source: SourceType
    source_url: str = ""
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class Knowledge:
    """Collection of retrieved knowledge."""
    items: list[KnowledgeItem]
    query: str
    total_confidence: float = 0.0

    def __post_init__(self):
        if self.items:
            self.total_confidence = sum(i.confidence for i in self.items) / len(self.items)

    def to_context(self) -> str:
        """Format for inclusion in LLM context."""
        lines = [f"## Knowledge Retrieved for: {self.query}\n"]

        for item in self.items:
            lines.append(f"**Source**: {item.source.value}")
            if item.source_url:
                lines.append(f"**URL**: {item.source_url}")
            lines.append(f"**Content**: {item.content}")
            lines.append("")

        return "\n".join(lines)

    def get_best(self, n: int = 3) -> list[KnowledgeItem]:
        """Get top N items by confidence."""
        return sorted(self.items, key=lambda x: x.confidence, reverse=True)[:n]


class KnowledgeAgent:
    """
    Retrieves information from multiple sources.

    Follows priority order to prefer authoritative sources
    over general web content.
    """

    # Priority order for source types
    SOURCE_PRIORITY = [
        SourceType.MEMORY,     # Our persistent memory (highest)
        SourceType.API,        # Authoritative APIs
        SourceType.WEB,        # Web search
        SourceType.RESEARCH,   # Academic papers
        SourceType.INTERNAL,   # LLM knowledge (lowest)
    ]

    def __init__(self, mcp_client=None, llm_client=None):
        """
        Initialize knowledge agent.

        Args:
            mcp_client: MCP client for memory and research access
            llm_client: LLM client for synthesis
        """
        self.mcp_client = mcp_client
        self.llm_client = llm_client

    async def retrieve(
        self,
        query: str,
        context: str = "",
        max_items: int = 5,
        sources: list[SourceType] = None
    ) -> Knowledge:
        """
        Retrieve knowledge for a query.

        Args:
            query: Search query
            context: Additional context
            max_items: Maximum items to return
            sources: Specific sources to query (default: all in priority order)

        Returns:
            Knowledge collection
        """
        logger.info(f"Retrieving knowledge for: {query[:50]}...")

        items = []
        sources_to_try = sources or self.SOURCE_PRIORITY

        for source in sources_to_try:
            if len(items) >= max_items:
                break

            try:
                source_items = await self._query_source(source, query, context)
                items.extend(source_items)
                logger.info(f"Got {len(source_items)} items from {source.value}")

            except Exception as e:
                logger.warning(f"Failed to query {source.value}: {e}")
                continue

        return Knowledge(
            items=items[:max_items],
            query=query
        )

    async def _query_source(
        self,
        source: SourceType,
        query: str,
        context: str
    ) -> list[KnowledgeItem]:
        """Query a specific source."""

        if source == SourceType.MEMORY:
            return await self._query_memory(query)

        elif source == SourceType.API:
            return await self._query_apis(query)

        elif source == SourceType.WEB:
            return await self._query_web(query)

        elif source == SourceType.RESEARCH:
            return await self._query_research(query)

        elif source == SourceType.INTERNAL:
            return []  # LLM knowledge is implicit

        return []

    async def _query_memory(self, query: str) -> list[KnowledgeItem]:
        """Query enhanced-memory-mcp."""
        logger.debug(f"Querying enhanced-memory for: {query}")

        if not self.mcp_client:
            logger.debug("No MCP client configured, skipping memory search")
            return []

        try:
            result = await self.mcp_client.memory_search(query, limit=10)

            if not result.success:
                logger.warning(f"Memory search failed: {result.error}")
                return []

            items = []
            for node in result.data:
                items.append(KnowledgeItem(
                    content=str(node.get("observations", node.get("content", ""))),
                    source=SourceType.MEMORY,
                    source_url=f"memory://{node.get('name', 'unknown')}",
                    confidence=0.9,  # High confidence for our own memory
                    metadata={
                        "entity_type": node.get("entityType", "unknown"),
                        "name": node.get("name", "unknown")
                    }
                ))
            return items

        except Exception as e:
            logger.warning(f"Memory query failed: {e}")
            return []

    async def _query_apis(self, query: str) -> list[KnowledgeItem]:
        """Query authoritative APIs."""
        # Would query things like:
        # - GitHub API for code
        # - Documentation APIs
        # - Weather/finance APIs
        logger.debug(f"Querying APIs for: {query}")
        return []

    async def _query_web(self, query: str) -> list[KnowledgeItem]:
        """Query web search."""
        # Uses WebSearch native tool
        logger.debug(f"Querying web for: {query}")
        return []

    async def _query_research(self, query: str) -> list[KnowledgeItem]:
        """Query research papers via research-paper-mcp."""
        logger.debug(f"Querying research papers for: {query}")

        if not self.mcp_client:
            return []

        try:
            result = await self.mcp_client.search_arxiv(query, max_results=5)

            if not result.success:
                logger.warning(f"arXiv search failed: {result.error}")
                return []

            items = []
            for paper in result.data:
                items.append(KnowledgeItem(
                    content=paper.get("summary", paper.get("abstract", "")),
                    source=SourceType.RESEARCH,
                    source_url=paper.get("url", paper.get("arxiv_url", "")),
                    confidence=0.85,
                    metadata={
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", []),
                        "published": paper.get("published", "")
                    }
                ))
            return items

        except Exception as e:
            logger.warning(f"Research query failed: {e}")
            return []

    async def synthesize(
        self,
        knowledge: Knowledge,
        question: str
    ) -> str:
        """
        Synthesize knowledge into an answer.

        Args:
            knowledge: Retrieved knowledge
            question: Question to answer

        Returns:
            Synthesized answer with citations
        """
        if not knowledge.items:
            return f"No relevant knowledge found for: {question}"

        # Format knowledge for synthesis
        context = knowledge.to_context()

        if not self.llm_client:
            # Without LLM, return formatted knowledge
            return context

        # Use LLM to synthesize an answer
        system_prompt = """You are a knowledge synthesis agent.
Given retrieved information, synthesize a clear, accurate answer.
Include citations to sources where appropriate."""

        user_prompt = f"""Question: {question}

Retrieved Knowledge:
{context}

Synthesize a comprehensive answer based on the retrieved knowledge.
Cite sources when using specific information."""

        try:
            answer = await self.llm_client.generate(
                system=system_prompt,
                user=user_prompt,
                temperature=0.3  # Low temperature for factual synthesis
            )
            return answer + "\n\n" + self.format_citations(knowledge.items)

        except Exception as e:
            logger.warning(f"Synthesis failed: {e}")
            return context

    def format_citations(self, items: list[KnowledgeItem]) -> str:
        """Format items as citations."""
        lines = ["## Sources"]
        for i, item in enumerate(items, 1):
            source_name = item.source.value.replace("_", " ").title()
            if item.source_url:
                lines.append(f"{i}. [{source_name}]({item.source_url})")
            else:
                lines.append(f"{i}. {source_name}")
        return "\n".join(lines)
