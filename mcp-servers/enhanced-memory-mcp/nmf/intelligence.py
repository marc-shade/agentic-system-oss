"""
LLM Intelligence features for Neural Memory Fabric.

Phase 4 intelligence features including:
- Keyword extraction
- Context description generation
- Importance scoring
- Result re-ranking

Extracted from neural_memory_fabric.py for modularity.
"""

import os
from typing import Any, Dict, List, Optional

from .config import logger


async def extract_keywords_llm(content: str) -> List[str]:
    """
    Extract keywords using LLM (Phase 4 Intelligence).

    Args:
        content: Memory content

    Returns:
        List of extracted keywords
    """
    # Try Google Gemini
    try:
        import google.generativeai as genai

        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""Extract 3-7 key keywords or phrases from this text. Return ONLY a comma-separated list, no explanation.

Text: {content[:1000]}

Keywords:"""

            response = model.generate_content(prompt)
            keywords_text = response.text.strip()

            # Parse comma-separated keywords
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            keywords = keywords[:7]  # Limit to 7

            logger.debug(f"Extracted keywords: {keywords}")
            return keywords

    except Exception as e:
        logger.debug(f"LLM keyword extraction failed: {e}")

    # Fallback: Simple extraction from content
    words = content.lower().split()
    # Get unique words longer than 4 characters
    keywords = list(set([w.strip('.,!?;:') for w in words if len(w) > 4]))[:5]
    return keywords


async def generate_context_description_llm(content: str) -> str:
    """
    Generate context description using LLM (Phase 4 Intelligence).

    Args:
        content: Memory content

    Returns:
        Brief context description
    """
    # Try Google Gemini
    try:
        import google.generativeai as genai

        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""Summarize this text in ONE concise sentence (max 100 chars). Focus on the main topic and key points.

Text: {content[:1000]}

Summary:"""

            response = model.generate_content(prompt)
            description = response.text.strip()

            # Limit length
            if len(description) > 200:
                description = description[:197] + "..."

            logger.debug(f"Generated description: {description}")
            return description

    except Exception as e:
        logger.debug(f"LLM context generation failed: {e}")

    # Fallback: First 200 characters
    return content[:200]


async def calculate_importance_llm(content: str, metadata: Optional[Dict]) -> float:
    """
    Calculate importance score using LLM (Phase 4 Intelligence).

    Args:
        content: Memory content
        metadata: Additional context

    Returns:
        Importance score (0.0 to 1.0)
    """
    # Check if user provided explicit importance
    if metadata and 'importance' in metadata:
        return float(metadata['importance'])

    # Try Google Gemini
    try:
        import google.generativeai as genai

        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""Rate the importance of this memory on a scale of 0.0 to 1.0, where:
- 0.0-0.3: Trivial, temporary information
- 0.4-0.6: Moderate importance, useful reference
- 0.7-0.9: Important information, key knowledge
- 1.0: Critical, must-remember information

Text: {content[:500]}

Return ONLY a number between 0.0 and 1.0, no explanation.

Importance:"""

            response = model.generate_content(prompt)
            score_text = response.text.strip()

            # Parse score
            try:
                score = float(score_text)
                score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                logger.debug(f"LLM importance score: {score}")
                return score
            except ValueError:
                logger.debug(f"Could not parse importance: {score_text}")

    except Exception as e:
        logger.debug(f"LLM importance scoring failed: {e}")

    # Fallback: Heuristic based on length and metadata
    base_score = 0.5

    # Longer content is often more important
    if len(content) > 500:
        base_score += 0.1
    if len(content) > 1000:
        base_score += 0.1

    # Has tags = more important
    if metadata and metadata.get('tags'):
        base_score += 0.1

    return min(1.0, base_score)


async def llm_rerank_results(
    query: str,
    results: List[Dict[str, Any]],
    limit: int
) -> List[Dict[str, Any]]:
    """
    Use LLM to re-rank recall results based on query relevance.

    Applies cross-encoder style re-ranking using an LLM to score
    each result against the query for improved relevance.

    Args:
        query: Original search query
        results: Current recall results
        limit: Maximum results to return

    Returns:
        Re-ranked results
    """
    # Only re-rank if we have multiple results and LLM is available
    if len(results) <= 1:
        return results

    try:
        # Lazy import to avoid circular dependencies
        from model_router import chat

        # Prepare results for LLM scoring (limit to avoid token overflow)
        candidates = results[:min(10, len(results))]

        # Build prompt for re-ranking
        candidates_text = "\n".join([
            f"[{i}] {r.get('content', '')[:200]}..."
            for i, r in enumerate(candidates)
        ])

        prompt = f"""Rate the relevance of each memory result to the query on a scale of 0-10.
Return ONLY a comma-separated list of scores in order (e.g., "8,6,9,3,7").

Query: "{query}"

Results:
{candidates_text}

Scores (comma-separated):"""

        response = await chat(
            model="gpt-4o-mini",  # Fast model for re-ranking
            messages=[
                {"role": "system", "content": "You are a relevance scoring assistant. Return only comma-separated numbers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.1  # Low temperature for consistent scoring
        )

        # Parse scores from response
        scores_text = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                scores_text = block.text.strip()
                break

        # Parse comma-separated scores
        try:
            scores = [float(s.strip()) for s in scores_text.split(',')]
            if len(scores) == len(candidates):
                # Apply LLM scores to results
                for i, score in enumerate(scores):
                    candidates[i]['llm_relevance_score'] = score / 10.0
                    # Blend LLM score with existing score
                    existing_score = candidates[i].get('rank_score', candidates[i].get('similarity_score', 0.5))
                    candidates[i]['rank_score'] = (existing_score * 0.4) + (score / 10.0 * 0.6)

                # Re-sort by blended score
                candidates.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
                logger.info(f"LLM re-ranked {len(candidates)} results")

                # Merge re-ranked candidates back with remaining results
                remaining = results[len(candidates):]
                return (candidates + remaining)[:limit]

        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse LLM re-ranking scores: {scores_text}")

    except ImportError:
        logger.debug("model_router not available for LLM re-ranking")
    except Exception as e:
        logger.warning(f"LLM re-ranking failed: {e}")

    return results


async def generate_cluster_summary(combined_content: str) -> Optional[str]:
    """
    Generate abstract summary for memory cluster using LLM.

    Args:
        combined_content: Combined content from cluster members

    Returns:
        Abstract summary or None
    """
    try:
        import google.generativeai as genai

        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""Create a concise abstract summary that captures the key themes and insights from these related memories. Focus on patterns, connections, and higher-order understanding.

Memories:
{combined_content[:2000]}

Abstract Summary (2-3 sentences):"""

        response = model.generate_content(prompt)
        summary = response.text.strip()

        logger.info(f"Generated cluster summary: {summary[:100]}...")
        return summary

    except Exception as e:
        logger.error(f"Cluster summary generation failed: {e}")
        return None


__all__ = [
    'extract_keywords_llm',
    'generate_context_description_llm',
    'calculate_importance_llm',
    'llm_rerank_results',
    'generate_cluster_summary',
]
