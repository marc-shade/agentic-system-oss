#!/usr/bin/env python3
"""
LLM integration for contextual prefix generation.

Uses Claude API (Anthropic) to generate concise contextual prefixes
that help improve retrieval accuracy.

Part of RAG Tier 1 Strategy - Week 1, Day 5-7
"""

import os
import logging
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

# Try to import Anthropic SDK
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not installed. Install with: pip install anthropic")


class ContextualPrefixGenerator:
    """
    Generates contextual prefixes for memory chunks using Claude.

    Based on Anthropic's Contextual Retrieval research:
    https://www.anthropic.com/news/contextual-retrieval

    Example:
        Original: "The cross-encoder achieved 45% precision improvement"
        Enriched: "[Context: RAG optimization study comparing re-ranking methods]
                   The cross-encoder achieved 45% precision improvement"
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4.5-20250929",
        max_tokens: int = 200,
        temperature: float = 0.0
    ):
        """
        Initialize contextual prefix generator.

        Args:
            model: Claude model to use (haiku for speed and cost)
            max_tokens: Maximum tokens for prefix (keep concise)
            temperature: Temperature for generation (0.0 for deterministic)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize client
        self.client = None
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = AsyncAnthropic(api_key=api_key)
                logger.info(f"✅ Contextual prefix generator initialized with {model}")
            else:
                logger.warning("ANTHROPIC_API_KEY not set - using fallback mode")
        else:
            logger.warning("Anthropic SDK not available - using fallback mode")

        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def generate_prefix(
        self,
        entity_name: str,
        entity_type: str,
        observations: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, int, int]:
        """
        Generate contextual prefix for an entity.

        Args:
            entity_name: Name of the entity
            entity_type: Type of the entity
            observations: List of observations about the entity
            metadata: Optional metadata

        Returns:
            Tuple of (prefix, input_tokens, output_tokens)
        """
        if not self.client:
            # Fallback to heuristic-based prefix
            return self._generate_fallback_prefix(entity_name, entity_type, observations)

        try:
            # Prepare context for LLM
            context_lines = []
            context_lines.append(f"Entity Name: {entity_name}")
            context_lines.append(f"Entity Type: {entity_type}")

            if observations:
                context_lines.append(f"Observations: {len(observations)}")
                # Include first few observations
                for i, obs in enumerate(observations[:3]):
                    obs_str = str(obs)
                    if len(obs_str) > 200:
                        obs_str = obs_str[:200] + "..."
                    context_lines.append(f"  {i + 1}. {obs_str}")

            context = "\n".join(context_lines)

            # Generate prefix using Claude
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{
                    "role": "user",
                    "content": f"""Given the following entity information, generate a concise contextual prefix (1-2 sentences) that would help a retrieval system understand what this entity is about.

{context}

Format the prefix as: [Context: <your concise description>]

Keep it under 50 words and focus on the key purpose/domain of this entity.

Respond with ONLY the contextual prefix, nothing else."""
                }]
            )

            # Extract prefix and token counts
            prefix = message.content[0].text.strip()

            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            return prefix, input_tokens, output_tokens

        except Exception as e:
            logger.error(f"Error generating prefix with LLM: {e}")
            # Fall back to heuristic
            return self._generate_fallback_prefix(entity_name, entity_type, observations)

    def _generate_fallback_prefix(
        self,
        entity_name: str,
        entity_type: str,
        observations: list
    ) -> tuple[str, int, int]:
        """
        Generate prefix using simple heuristics (fallback mode).

        Args:
            entity_name: Name of the entity
            entity_type: Type of the entity
            observations: List of observations

        Returns:
            Tuple of (prefix, 0, 0) - no tokens used in fallback mode
        """
        prefix = f"[Context: This is a {entity_type} entity named '{entity_name}'"

        if observations:
            first_obs = observations[0] if isinstance(observations, list) else str(observations)
            first_obs_str = str(first_obs)
            if len(first_obs_str) > 50:
                first_obs_str = first_obs_str[:50] + "..."
            prefix += f" with information about {first_obs_str}"

        prefix += "] "

        return prefix, 0, 0

    def get_cost_estimate(self) -> float:
        """
        Estimate cost based on tokens used.

        Returns:
            Total cost in USD
        """
        # Haiku pricing (as of 2024)
        COST_PER_1K_INPUT = 0.00025
        COST_PER_1K_OUTPUT = 0.00125

        input_cost = (self.total_input_tokens / 1000) * COST_PER_1K_INPUT
        output_cost = (self.total_output_tokens / 1000) * COST_PER_1K_OUTPUT

        return input_cost + output_cost

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": self.get_cost_estimate(),
            "model": self.model,
            "anthropic_available": ANTHROPIC_AVAILABLE,
            "using_fallback": not bool(self.client)
        }


# Global instance
_generator = None


def get_prefix_generator() -> ContextualPrefixGenerator:
    """Get or create global prefix generator instance."""
    global _generator
    if _generator is None:
        _generator = ContextualPrefixGenerator()
    return _generator
