"""
LLM Council Core Logic
======================

3-stage deliberation system where multiple LLMs collaboratively answer questions:

Stage 1: Collect individual responses from all council models
Stage 2: Anonymized peer review - models rank each other's responses
Stage 3: Chairman synthesizes final answer from all inputs

Key innovation: Anonymization in Stage 2 prevents models from playing favorites.
"""

import asyncio
import logging
import re
import string
from typing import Dict, List, Tuple, Any, Optional

from .config import (
    PROVIDER_MODE,
    CLI_COUNCIL_MODELS,
    CLI_CHAIRMAN_MODEL,
    MAX_RANKING_RETRIES,
)
from .cli_providers import query_providers_parallel, query_cli_provider

logger = logging.getLogger(__name__)


def _create_label_mapping(models: List[str]) -> Dict[str, str]:
    """Create mapping from anonymous labels to model names."""
    labels = list(string.ascii_uppercase[:len(models)])
    return {f"Response {label}": model for label, model in zip(labels, models)}


def _anonymize_responses(responses: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """
    Anonymize responses for peer review.

    Returns:
        Tuple of (formatted_text, label_to_model_mapping)
    """
    models = list(responses.keys())
    label_mapping = _create_label_mapping(models)

    # Reverse mapping for formatting
    model_to_label = {v: k for k, v in label_mapping.items()}

    formatted_parts = []
    for model, response in responses.items():
        label = model_to_label[model]
        formatted_parts.append(f"### {label}\n\n{response}\n")

    return "\n".join(formatted_parts), label_mapping


def parse_ranking_from_text(text: str) -> List[str]:
    """
    Extract ranking from evaluation text.

    Looks for "FINAL RANKING:" section with numbered list.
    Falls back to regex extraction of Response X patterns.
    """
    # Try to find FINAL RANKING section
    ranking_match = re.search(
        r'FINAL RANKING[:\s]*\n((?:[\d]+[.\)]\s*Response\s+[A-Z].*\n?)+)',
        text,
        re.IGNORECASE
    )

    if ranking_match:
        ranking_section = ranking_match.group(1)
        # Extract Response labels in order
        labels = re.findall(r'Response\s+([A-Z])', ranking_section)
        return [f"Response {label}" for label in labels]

    # Fallback: find all Response X mentions in order
    all_mentions = re.findall(r'Response\s+([A-Z])', text)
    if all_mentions:
        # Take unique labels in order of first appearance
        seen = set()
        ordered = []
        for label in all_mentions:
            if label not in seen:
                seen.add(label)
                ordered.append(f"Response {label}")
        return ordered

    return []


def calculate_aggregate_rankings(
    rankings: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all peer evaluations.

    Returns list of models sorted by average rank position.
    """
    # Collect all rank positions for each label
    rank_positions: Dict[str, List[int]] = {label: [] for label in label_to_model}

    for ranking in rankings:
        parsed = ranking.get("parsed_ranking", [])
        for position, label in enumerate(parsed, 1):
            if label in rank_positions:
                rank_positions[label].append(position)

    # Calculate averages and format results
    results = []
    for label, model in label_to_model.items():
        positions = rank_positions[label]
        if positions:
            avg_rank = sum(positions) / len(positions)
            results.append({
                "model": model,
                "label": label,
                "average_rank": round(avg_rank, 2),
                "vote_count": len(positions),
                "positions": positions,
            })

    # Sort by average rank (lower is better)
    results.sort(key=lambda x: x["average_rank"])
    return results


async def stage1_collect_responses(
    question: str,
    models: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Stage 1: Collect individual responses from council models.

    Args:
        question: The user's question
        models: Optional list of models (defaults to config)

    Returns:
        Dict mapping model names to their responses
    """
    if models is None:
        models = CLI_COUNCIL_MODELS

    prompt = f"""Please provide a thorough, well-reasoned answer to the following question:

{question}

Focus on accuracy, clarity, and completeness in your response."""

    logger.info(f"Stage 1: Querying {len(models)} models")

    results = await query_providers_parallel(models, prompt)

    # Filter to successful responses
    responses = {}
    for model, result in results.items():
        if result.get("content"):
            responses[model] = result["content"]
        else:
            logger.warning(f"Model {model} failed: {result.get('error')}")

    logger.info(f"Stage 1 complete: {len(responses)}/{len(models)} responses")
    return responses


async def stage2_collect_rankings(
    question: str,
    responses: Dict[str, str],
    models: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Collect anonymized peer rankings.

    Args:
        question: Original question for context
        responses: Dict of model responses from Stage 1
        models: Optional list of evaluator models

    Returns:
        Tuple of (rankings_list, label_to_model_mapping)
    """
    if models is None:
        models = CLI_COUNCIL_MODELS

    # Anonymize responses
    formatted_responses, label_to_model = _anonymize_responses(responses)

    ranking_prompt = f"""You are evaluating responses to this question:

{question}

Here are the anonymized responses:

{formatted_responses}

Please evaluate each response for:
1. Accuracy and correctness
2. Completeness and depth
3. Clarity and organization
4. Practical usefulness

After your evaluation, provide your final ranking in this exact format:

FINAL RANKING:
1. Response X
2. Response Y
3. Response Z

(Replace X, Y, Z with the actual labels, ranked from best to worst)"""

    logger.info(f"Stage 2: Collecting rankings from {len(models)} models")

    results = await query_providers_parallel(models, ranking_prompt)

    rankings = []
    for model, result in results.items():
        if result.get("content"):
            parsed = parse_ranking_from_text(result["content"])
            rankings.append({
                "evaluator": model,
                "raw_evaluation": result["content"],
                "parsed_ranking": parsed,
            })
        else:
            logger.warning(f"Evaluator {model} failed: {result.get('error')}")

    logger.info(f"Stage 2 complete: {len(rankings)}/{len(models)} rankings")
    return rankings, label_to_model


async def stage3_synthesize_final(
    question: str,
    responses: Dict[str, str],
    rankings: List[Dict[str, Any]],
    aggregate_rankings: List[Dict[str, Any]],
    chairman: Optional[str] = None
) -> str:
    """
    Stage 3: Chairman synthesizes final answer.

    Args:
        question: Original question
        responses: All model responses
        rankings: Individual peer rankings
        aggregate_rankings: Calculated aggregate rankings
        chairman: Optional chairman model override

    Returns:
        Final synthesized answer
    """
    if chairman is None:
        chairman = CLI_CHAIRMAN_MODEL

    # Format responses with rankings context
    ranked_responses = []
    for rank_info in aggregate_rankings:
        model = rank_info["model"]
        if model in responses:
            ranked_responses.append(
                f"### {model} (Avg Rank: {rank_info['average_rank']})\n\n"
                f"{responses[model]}"
            )

    synthesis_prompt = f"""You are the chairman synthesizing a final answer.

Original question: {question}

The council has provided and ranked these responses (ordered by peer-ranking quality):

{chr(10).join(ranked_responses)}

Aggregate Rankings:
{chr(10).join(f"- {r['model']}: avg rank {r['average_rank']}" for r in aggregate_rankings)}

Please synthesize a comprehensive final answer that:
1. Incorporates the best insights from the highest-ranked responses
2. Addresses any important points from lower-ranked responses
3. Resolves any conflicts between responses
4. Provides a clear, authoritative answer

Your synthesized response:"""

    logger.info(f"Stage 3: Chairman {chairman} synthesizing")

    result = await query_cli_provider(chairman, synthesis_prompt)

    if result.get("content"):
        logger.info("Stage 3 complete: Synthesis successful")
        return result["content"]
    else:
        logger.error(f"Chairman synthesis failed: {result.get('error')}")
        # Fallback to top-ranked response
        if aggregate_rankings and aggregate_rankings[0]["model"] in responses:
            return f"[Chairman synthesis failed. Top-ranked response:]\n\n{responses[aggregate_rankings[0]['model']]}"
        return "[Synthesis failed. No valid responses available.]"


async def run_full_council(
    question: str,
    council_models: Optional[List[str]] = None,
    chairman_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run complete 3-stage council deliberation.

    Args:
        question: The question to deliberate
        council_models: Optional list of council models
        chairman_model: Optional chairman model

    Returns:
        Dict with stage1, stage2, stage3 results and metadata
    """
    # Stage 1: Collect responses
    responses = await stage1_collect_responses(question, council_models)

    if not responses:
        return {
            "success": False,
            "error": "No responses collected in Stage 1",
            "stage1": {},
            "stage2": {"rankings": [], "label_to_model": {}},
            "stage3": None,
        }

    # Stage 2: Peer ranking
    rankings, label_to_model = await stage2_collect_rankings(
        question, responses, council_models
    )

    # Calculate aggregate rankings
    aggregate = calculate_aggregate_rankings(rankings, label_to_model)

    # Stage 3: Synthesis
    final_answer = await stage3_synthesize_final(
        question, responses, rankings, aggregate, chairman_model
    )

    return {
        "success": True,
        "stage1": responses,
        "stage2": {
            "rankings": rankings,
            "label_to_model": label_to_model,
            "aggregate_rankings": aggregate,
        },
        "stage3": final_answer,
        "metadata": {
            "council_models": council_models or CLI_COUNCIL_MODELS,
            "chairman_model": chairman_model or CLI_CHAIRMAN_MODEL,
            "response_count": len(responses),
            "ranking_count": len(rankings),
        }
    }
