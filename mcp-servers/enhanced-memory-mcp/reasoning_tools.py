"""
Reasoning Prioritization Tools for Enhanced Memory MCP

Integrates 75/15 rule from AI vision research into memory operations.
"""
import sqlite3
import json
from typing import Dict, List, Any
from datetime import datetime

from reasoning_prioritizer import get_prioritizer, ContentCategory


def register_reasoning_tools(app, db_path):
    """Register reasoning-prioritized tools with the MCP server."""

    prioritizer = get_prioritizer()

    @app.tool()
    async def classify_memory_content(content: str) -> Dict[str, Any]:
        """
        Classify memory content according to 75/15 rule.

        Research finding: Reasoning-centric content (code/math/science) should
        be prioritized for storage and retrieval.

        Args:
            content: Text content to classify

        Returns:
            Classification with category, weight, and scores
        """
        priority = prioritizer.classify_content(content)

        return {
            "category": priority.category.value,
            "weight": priority.weight,
            "reasoning_score": priority.reasoning_score,
            "visual_score": priority.visual_score,
            "confidence": priority.confidence,
            "interpretation": _interpret_priority(priority),
            "storage_recommendation": {
                "should_prioritize": priority.category == ContentCategory.REASONING_CENTRIC,
                "compression_level": prioritizer.get_compression_level(content),
                "recommended_tier": prioritizer.calculate_tier_priority(content, 0)
            }
        }

    @app.tool()
    async def search_with_reasoning_priority(
        query: str,
        limit: int = 10,
        boost_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Search memories with reasoning-first prioritization.

        Research finding: Boost reasoning-centric results by 1.3x for
        optimal retrieval aligned with 75/15 rule.

        Args:
            query: Search query
            limit: Maximum results (default: 10)
            boost_reasoning: Whether to boost reasoning content (default: True)

        Returns:
            Ranked search results with priority scores
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all entities
        cursor.execute('''
            SELECT e.id, e.name, e.entity_type, e.tier, e.access_count,
                   GROUP_CONCAT(o.content, ' ') as observations
            FROM entities e
            LEFT JOIN observations o ON e.id = o.entity_id
            GROUP BY e.id
        ''')

        results = cursor.fetchall()
        conn.close()

        # Convert to dictionaries
        memories = []
        for r in results:
            memories.append({
                "id": r[0],
                "name": r[1],
                "entityType": r[2],
                "tier": r[3],
                "access_count": r[4],
                "observations": r[5] or ""
            })

        # Rank with reasoning prioritization
        ranked = prioritizer.rank_memories(memories, query, boost_reasoning)

        # Format results
        formatted_results = []
        for memory, score in ranked[:limit]:
            # Classify memory
            content = memory.get("observations", "")
            priority = prioritizer.classify_content(content)

            formatted_results.append({
                "entity": {
                    "id": memory["id"],
                    "name": memory["name"],
                    "type": memory["entityType"],
                    "tier": memory["tier"]
                },
                "relevance_score": score,
                "content_category": priority.category.value,
                "priority_weight": priority.weight,
                "reasoning_score": priority.reasoning_score,
                "observations_preview": content[:200] + "..." if len(content) > 200 else content
            })

        # Analyze query
        query_priority = prioritizer.classify_content(query)

        return {
            "query_analysis": {
                "category": query_priority.category.value,
                "weight": query_priority.weight,
                "reasoning_score": query_priority.reasoning_score
            },
            "results": formatted_results,
            "total_results": len(formatted_results),
            "reasoning_boost_applied": boost_reasoning,
            "summary": _generate_search_summary(formatted_results, query_priority)
        }

    @app.tool()
    async def analyze_memory_distribution() -> Dict[str, Any]:
        """
        Analyze current memory distribution vs optimal 75/15 rule.

        Returns distribution breakdown and recommendations for optimization.

        Returns:
            Distribution analysis with recommendations
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all entities with observations
        cursor.execute('''
            SELECT GROUP_CONCAT(o.content, ' ') as observations
            FROM entities e
            LEFT JOIN observations o ON e.id = o.entity_id
            GROUP BY e.id
        ''')

        results = cursor.fetchall()
        conn.close()

        # Classify all memories
        categories = {
            "reasoning_centric": 0,
            "visual_centric": 0,
            "general": 0
        }

        total_memories = 0
        for r in results:
            content = r[0] or ""
            if not content.strip():
                continue

            priority = prioritizer.classify_content(content)
            categories[priority.category.value] += 1
            total_memories += 1

        if total_memories == 0:
            return {
                "error": "No memories found",
                "recommendation": "Add memories to analyze distribution"
            }

        # Calculate percentages
        current_distribution = {
            "reasoning_centric": categories["reasoning_centric"] / total_memories,
            "visual_centric": categories["visual_centric"] / total_memories,
            "general": categories["general"] / total_memories
        }

        optimal_distribution = {
            "reasoning_centric": 0.75,
            "visual_centric": 0.15,
            "general": 0.10
        }

        # Calculate gaps
        gaps = {
            key: optimal_distribution[key] - current_distribution[key]
            for key in optimal_distribution
        }

        return {
            "total_memories": total_memories,
            "current_distribution": {
                key: f"{value:.1%}"
                for key, value in current_distribution.items()
            },
            "optimal_distribution": {
                key: f"{value:.1%}"
                for key, value in optimal_distribution.items()
            },
            "gaps": {
                key: f"{value:+.1%}"
                for key, value in gaps.items()
            },
            "recommendations": _generate_distribution_recommendations(gaps, current_distribution),
            "compliance_score": _calculate_compliance_score(current_distribution, optimal_distribution)
        }

    @app.tool()
    async def optimize_memory_tiers() -> Dict[str, Any]:
        """
        Optimize memory tier assignments based on 75/15 rule.

        Reasoning-centric content gets priority tiers (core/working).
        Visual and general content moved to reference tier.

        Returns:
            Optimization results with tier changes
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all entities
        cursor.execute('''
            SELECT e.id, e.name, e.access_count, e.tier,
                   GROUP_CONCAT(o.content, ' ') as observations
            FROM entities e
            LEFT JOIN observations o ON e.id = o.entity_id
            GROUP BY e.id
        ''')

        results = cursor.fetchall()

        changes = []
        for r in results:
            entity_id, name, access_count, current_tier, observations = r
            content = observations or ""

            # Calculate optimal tier
            optimal_tier = prioritizer.calculate_tier_priority(content, access_count)

            if optimal_tier != current_tier:
                # Update tier
                cursor.execute('''
                    UPDATE entities
                    SET tier = ?
                    WHERE id = ?
                ''', (optimal_tier, entity_id))

                # Classify for reason
                priority = prioritizer.classify_content(content)

                changes.append({
                    "entity_id": entity_id,
                    "name": name,
                    "from_tier": current_tier,
                    "to_tier": optimal_tier,
                    "category": priority.category.value,
                    "reason": _explain_tier_change(current_tier, optimal_tier, priority, access_count)
                })

        conn.commit()
        conn.close()

        return {
            "total_changes": len(changes),
            "changes": changes,
            "summary": f"Optimized {len(changes)} entities based on 75/15 rule"
        }


def _interpret_priority(priority) -> str:
    """Generate human-readable interpretation of priority."""
    if priority.category == ContentCategory.REASONING_CENTRIC:
        return (
            f"Reasoning-centric content (weight: {priority.weight}). "
            "Prioritize for storage and retrieval. Use lower compression to preserve detail."
        )
    elif priority.category == ContentCategory.VISUAL_CENTRIC:
        return (
            f"Visual-descriptive content (weight: {priority.weight}). "
            "Useful for visual anchoring. Higher compression acceptable."
        )
    else:
        return (
            f"General content (weight: {priority.weight}). "
            "Lowest priority. Maximum compression recommended."
        )


def _generate_search_summary(results: List[Dict], query_priority) -> str:
    """Generate summary of search results."""
    if not results:
        return "No results found"

    reasoning_count = sum(1 for r in results if r["content_category"] == "reasoning_centric")
    visual_count = sum(1 for r in results if r["content_category"] == "visual_centric")

    summary = f"Found {len(results)} results. "
    if reasoning_count > 0:
        summary += f"{reasoning_count} reasoning-centric (prioritized). "
    if visual_count > 0:
        summary += f"{visual_count} visual. "

    if query_priority.category == ContentCategory.REASONING_CENTRIC:
        summary += "Query is reasoning-focused - boosting technical content."

    return summary


def _generate_distribution_recommendations(gaps: Dict, current: Dict) -> List[str]:
    """Generate recommendations based on distribution gaps."""
    recommendations = []

    if gaps["reasoning_centric"] > 0.1:
        recommendations.append(
            f"Add {gaps['reasoning_centric']:.0%} more code, math, or science content "
            "for optimal 75/15 ratio"
        )

    if gaps["reasoning_centric"] < -0.1:
        recommendations.append(
            f"Current memory is {current['reasoning_centric']:.0%} reasoning-centric "
            "(above optimal 75%). Consider archiving older reasoning content."
        )

    if gaps["visual_centric"] > 0.05:
        recommendations.append(
            f"Add {gaps['visual_centric']:.0%} more visual descriptions "
            "for better balance"
        )

    if not recommendations:
        recommendations.append("Memory distribution is optimal!")

    return recommendations


def _calculate_compliance_score(current: Dict, optimal: Dict) -> float:
    """Calculate compliance score (0-1) with optimal distribution."""
    total_deviation = sum(
        abs(optimal[key] - current[key])
        for key in optimal
    )

    # Perfect compliance = 0 deviation, score = 1.0
    # Maximum deviation = 2.0 (all in wrong categories), score = 0.0
    compliance = 1.0 - (total_deviation / 2.0)
    return max(0.0, min(1.0, compliance))


def _explain_tier_change(from_tier: str, to_tier: str, priority, access_count: int) -> str:
    """Explain why tier was changed."""
    if priority.category == ContentCategory.REASONING_CENTRIC:
        if to_tier == "core":
            return f"Promoted to core: high-value reasoning content (accessed {access_count} times)"
        elif to_tier == "working":
            return "Promoted to working: reasoning-centric content deserves higher tier"
        else:
            return "Low access count despite reasoning content"

    elif priority.category == ContentCategory.VISUAL_CENTRIC:
        if to_tier == "reference":
            return "Moved to reference: visual content is lower priority"
        else:
            return f"Kept in {to_tier}: high access count ({access_count})"

    else:  # General
        return "Moved to reference: general content is lowest priority"
