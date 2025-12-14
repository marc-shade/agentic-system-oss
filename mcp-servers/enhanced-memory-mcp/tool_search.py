#!/usr/bin/env python3
"""
Tool Search - On-Demand Tool Discovery

Based on Anthropic's Advanced Tool Use Pattern (Nov 2025)
Instead of loading 100+ tool definitions upfront (50-100k tokens),
use this ~500 token search tool to discover relevant tools on demand.

Flow:
1. Model describes what it wants to do
2. tool_search finds matching tools from catalog
3. Only matched tools (3-5) are loaded into context
4. Model uses specific tools

Expected Token Savings: 77k → 8.7k (89% reduction)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from tool_catalog import (
    TOOL_CATALOG,
    ToolDefinition,
    ToolTier,
    CATEGORIES,
    ALWAYS_LOAD,
    get_tools_by_tier,
    get_tools_by_category,
)

@dataclass
class SearchResult:
    """Result from tool search"""
    tool_name: str
    relevance_score: float
    description: str
    tier: str
    category: str
    parameters: List[str]
    example: Optional[Dict] = None

def calculate_relevance(query: str, tool: ToolDefinition) -> float:
    """Calculate relevance score between query and tool"""
    query_lower = query.lower()
    search_text = tool.to_search_text()

    score = 0.0

    # Direct name match (highest weight)
    if tool.name.lower() in query_lower or query_lower in tool.name.lower():
        score += 0.5

    # Keyword matches
    for keyword in tool.keywords:
        if keyword.lower() in query_lower:
            score += 0.15

    # Category match
    if tool.category.lower() in query_lower:
        score += 0.1
    if tool.subcategory.lower() in query_lower:
        score += 0.1

    # Description similarity
    desc_ratio = SequenceMatcher(None, query_lower, tool.description.lower()).ratio()
    score += desc_ratio * 0.2

    # Word overlap
    query_words = set(query_lower.split())
    search_words = set(search_text.split())
    overlap = len(query_words & search_words)
    if query_words:
        score += (overlap / len(query_words)) * 0.1

    # Tier bonus (prefer HOT tools when relevance is similar)
    if tool.tier == ToolTier.HOT:
        score += 0.05
    elif tool.tier == ToolTier.WARM:
        score += 0.02

    return min(score, 1.0)

def search_tools(
    query: str,
    limit: int = 5,
    include_examples: bool = True,
    category_filter: Optional[str] = None,
    tier_filter: Optional[str] = None,
) -> List[SearchResult]:
    """
    Search for relevant tools based on natural language query.

    Args:
        query: Natural language description of what you want to do
        limit: Maximum number of tools to return
        include_examples: Whether to include usage examples
        category_filter: Only search within specific category
        tier_filter: Only search within specific tier (hot, warm, cold)

    Returns:
        List of matching tools sorted by relevance
    """
    candidates = list(TOOL_CATALOG.values())

    # Apply filters
    if category_filter:
        candidates = [t for t in candidates if t.category == category_filter.lower()]

    if tier_filter:
        tier_map = {"hot": ToolTier.HOT, "warm": ToolTier.WARM, "cold": ToolTier.COLD}
        if tier_filter.lower() in tier_map:
            candidates = [t for t in candidates if t.tier == tier_map[tier_filter.lower()]]

    # Score all candidates
    scored = []
    for tool in candidates:
        score = calculate_relevance(query, tool)
        if score > 0.05:  # Minimum threshold
            scored.append((tool, score))

    # Sort by relevance
    scored.sort(key=lambda x: x[1], reverse=True)

    # Build results
    results = []
    for tool, score in scored[:limit]:
        result = SearchResult(
            tool_name=tool.name,
            relevance_score=round(score, 3),
            description=tool.description,
            tier=tool.tier.value,
            category=tool.category,
            parameters=tool.parameters,
            example=tool.example if include_examples else None
        )
        results.append(result)

    return results

def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get full schema for a specific tool"""
    if tool_name not in TOOL_CATALOG:
        return None

    tool = TOOL_CATALOG[tool_name]
    return {
        "name": tool.name,
        "description": tool.description,
        "tier": tool.tier.value,
        "category": tool.category,
        "subcategory": tool.subcategory,
        "keywords": tool.keywords,
        "parameters": tool.parameters,
        "module": tool.module,
        "example": tool.example
    }

def get_related_tools(tool_name: str, limit: int = 3) -> List[str]:
    """Get tools related to a specific tool (same category/subcategory)"""
    if tool_name not in TOOL_CATALOG:
        return []

    tool = TOOL_CATALOG[tool_name]
    related = []

    for name, other in TOOL_CATALOG.items():
        if name == tool_name:
            continue
        if other.category == tool.category and other.subcategory == tool.subcategory:
            related.append(name)
        elif other.category == tool.category:
            related.append(name)

    return related[:limit]

def format_search_results_for_context(results: List[SearchResult]) -> str:
    """Format search results for inclusion in model context"""
    if not results:
        return "No matching tools found."

    output = []
    output.append(f"Found {len(results)} relevant tools:\n")

    for r in results:
        output.append(f"### {r.tool_name}")
        output.append(f"**Description**: {r.description}")
        output.append(f"**Category**: {r.category} | **Tier**: {r.tier}")
        output.append(f"**Parameters**: {', '.join(r.parameters) if r.parameters else 'none'}")

        if r.example:
            output.append(f"**Example**: {r.example.get('description', '')}")

        output.append("")

    return "\n".join(output)

# =============================================================================
# TOOL SEARCH TOOL - Register with FastMCP
# =============================================================================

def register_tool_search(app):
    """Register the tool_search tool with FastMCP app"""

    @app.tool()
    async def tool_search(
        query: str,
        limit: int = 5,
        include_examples: bool = True,
        category: str = None,
    ) -> Dict[str, Any]:
        """
        Search for memory tools based on what you want to accomplish.

        This is a META-TOOL for discovering other tools on demand.
        Instead of having 100+ tools loaded, describe what you want to do
        and this will find the most relevant tools.

        Args:
            query: Natural language description of what you want to do
                   Examples: "store a new memory", "search past experiences",
                   "track my beliefs", "analyze causal relationships"
            limit: Maximum number of tools to return (default: 5)
            include_examples: Include usage examples in results (default: True)
            category: Filter by category (memory, cluster, learning, cognition, agent)

        Returns:
            List of relevant tools with descriptions and examples

        Categories available:
        - memory: Core memory operations (store, search, retrieve)
        - cluster: Multi-node cluster operations
        - learning: Action tracking, self-improvement
        - cognition: Beliefs, causality, metacognition
        - agent: Identity, sessions
        """
        results = search_tools(
            query=query,
            limit=limit,
            include_examples=include_examples,
            category_filter=category,
        )

        return {
            "query": query,
            "results_count": len(results),
            "tools": [
                {
                    "name": r.tool_name,
                    "relevance": r.relevance_score,
                    "description": r.description,
                    "tier": r.tier,
                    "category": r.category,
                    "parameters": r.parameters,
                    "example": r.example
                }
                for r in results
            ],
            "hint": "Use the specific tool names above to perform your task. "
                    "For batch operations, consider using execute_code with programmatic calling."
        }

    @app.tool()
    async def tool_info(tool_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tool.

        Use this after tool_search to get full details about a tool
        before using it.

        Args:
            tool_name: Name of the tool to get info for

        Returns:
            Complete tool schema including examples and related tools
        """
        schema = get_tool_schema(tool_name)
        if not schema:
            return {
                "error": f"Tool '{tool_name}' not found",
                "suggestion": "Use tool_search to find available tools"
            }

        related = get_related_tools(tool_name)
        schema["related_tools"] = related

        return schema

    @app.tool()
    async def list_tool_categories() -> Dict[str, Any]:
        """
        List all available tool categories and their subcategories.

        Use this to understand the tool organization before searching.

        Returns:
            Dictionary of categories with their subcategories and tool counts
        """
        category_info = {}

        for category, subcats in CATEGORIES.items():
            tools_in_cat = get_tools_by_category(category)
            category_info[category] = {
                "subcategories": subcats,
                "tool_count": len(tools_in_cat),
                "hot_tools": len([t for t in tools_in_cat if t.tier == ToolTier.HOT]),
                "sample_tools": [t.name for t in tools_in_cat[:3]]
            }

        return {
            "total_tools": len(TOOL_CATALOG),
            "always_loaded": list(ALWAYS_LOAD),
            "categories": category_info
        }

    return True

if __name__ == "__main__":
    # Test the search functionality
    test_queries = [
        "store a new memory about python patterns",
        "search for past experiences",
        "track my beliefs about this project",
        "find causal relationships",
        "batch process multiple memories",
        "cluster knowledge sharing",
    ]

    print("Tool Search Test Results\n" + "="*50)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = search_tools(query, limit=3)
        for r in results:
            print(f"  [{r.relevance_score:.2f}] {r.tool_name}: {r.description[:60]}...")
