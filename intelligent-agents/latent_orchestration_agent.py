"""
Latent Orchestration Agent
==========================

AGI agent for orchestrating latent manipulation workflows.

This agent integrates with the DiffusionLatentHacker to enable:
- Automated style library building
- Consistent character/persona generation
- Latent space exploration and discovery
- Cross-model capability arbitrage

Based on Richard Aragon's "Mathematical Hacking" paper:
Reconstructing hidden diffusion dynamics via exposed constraint surfaces.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "image-gen-mcp" / "src"))

from image_gen_mcp.latent_hacker import DiffusionLatentHacker, LatentState, image_from_base64
from image_gen_mcp.latent_guided_provider import LatentGuidedProvider, MultiProviderLatentRouter

logger = logging.getLogger("latent-orchestration")


@dataclass
class StyleLibraryEntry:
    """Entry in the style library."""
    name: str
    description: str
    category: str  # e.g., "artistic", "photorealistic", "abstract"
    model_id: str
    example_prompt: str
    created_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    average_rating: float = 0.0


@dataclass
class GenerationPlan:
    """Plan for a multi-image generation workflow."""
    name: str
    images: List[Dict[str, Any]]  # List of {prompt, style, params}
    consistency_style: Optional[str] = None  # Style to apply for visual consistency
    total_count: int = 0
    completed_count: int = 0


class LatentOrchestrationAgent:
    """
    AGI agent for orchestrating complex latent manipulation workflows.

    Integrates with the 6-phase AGI orchestrator workflow:
    1. Goal Decomposition - Break visual goals into sub-tasks
    2. Context Synthesis - Gather style references and constraints
    3. Multi-Agent Coordination - Parallel style exploration
    4. Meta-Learning - Track successful style combinations
    5. Skill Evolution - Improve style transfer effectiveness
    6. Darwin Godel - Propose new manipulation techniques
    """

    def __init__(
        self,
        latent_hacker: Optional[DiffusionLatentHacker] = None,
        style_library_path: Optional[Path] = None,
    ):
        """
        Initialize latent orchestration agent.

        Args:
            latent_hacker: DiffusionLatentHacker instance
            style_library_path: Path to persist style library
        """
        self.latent_hacker = latent_hacker or DiffusionLatentHacker()
        self.style_library_path = style_library_path or Path.home() / ".claude" / "style_library"
        self.style_library_path.mkdir(parents=True, exist_ok=True)

        # Style library metadata
        self.style_library: Dict[str, StyleLibraryEntry] = {}

        # Active generation plans
        self.active_plans: Dict[str, GenerationPlan] = {}

        # Learning statistics
        self.stats = {
            "styles_created": 0,
            "styles_applied": 0,
            "cross_model_transfers": 0,
            "interpolations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
        }

        logger.info("LatentOrchestrationAgent initialized")

    async def build_style_from_description(
        self,
        style_name: str,
        description: str,
        category: str = "general",
        model: str = "flux-dev",
        provider: str = "huggingface",
        num_samples: int = 1,
    ) -> List[LatentState]:
        """
        Build a style latent from a text description.

        Generates reference images and captures their latents.

        Args:
            style_name: Name for the style
            description: Text description of the style
            category: Style category for organization
            model: Model to use for generation
            provider: Provider to use
            num_samples: Number of reference images to generate

        Returns:
            List of captured LatentState objects
        """
        # This would integrate with the image generation provider
        # For now, we prepare the structure

        prompt = f"{description}, highly detailed, professional quality"

        entry = StyleLibraryEntry(
            name=style_name,
            description=description,
            category=category,
            model_id=model,
            example_prompt=prompt,
        )

        self.style_library[style_name] = entry
        self.stats["styles_created"] += 1

        logger.info(f"Prepared style '{style_name}' for generation with {model}")

        # Return empty list - actual generation would be done via MCP tools
        return []

    async def create_consistent_series(
        self,
        base_style: str,
        prompts: List[str],
        strength: float = 0.8,
    ) -> GenerationPlan:
        """
        Create a plan for generating a visually consistent series.

        All images will share the style characteristics of base_style.

        Args:
            base_style: Name of style to apply for consistency
            prompts: List of prompts for each image
            strength: How strongly to apply the style

        Returns:
            GenerationPlan for the series
        """
        plan_name = f"series_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        images = []
        for i, prompt in enumerate(prompts):
            # Get guided parameters
            try:
                transfer = self.latent_hacker.apply_style_latent(
                    target_prompt=prompt,
                    style_name=base_style,
                    strength=strength,
                )
                images.append({
                    "index": i,
                    "original_prompt": prompt,
                    "guided_prompt": transfer.guided_prompt,
                    "seed": transfer.guided_seed,
                    "params": transfer.params,
                    "status": "pending",
                })
            except ValueError as e:
                logger.warning(f"Failed to apply style to prompt {i}: {e}")
                images.append({
                    "index": i,
                    "original_prompt": prompt,
                    "guided_prompt": prompt,
                    "seed": None,
                    "params": {},
                    "status": "fallback",
                })

        plan = GenerationPlan(
            name=plan_name,
            images=images,
            consistency_style=base_style,
            total_count=len(prompts),
        )

        self.active_plans[plan_name] = plan

        logger.info(f"Created generation plan '{plan_name}' with {len(prompts)} images")
        return plan

    async def explore_latent_space(
        self,
        base_style: str,
        dimensions: int = 5,
        samples_per_dim: int = 3,
        variation_strength: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Systematically explore latent space around a base style.

        Useful for discovering emergent visual styles and understanding
        the constraint surface geometry.

        Args:
            base_style: Starting style to explore from
            dimensions: Number of random directions to explore
            samples_per_dim: Samples along each direction
            variation_strength: How far to deviate from base

        Returns:
            List of exploration points with their parameters
        """
        if base_style not in self.latent_hacker._latent_cache:
            self.latent_hacker._load_latent(base_style)

        if base_style not in self.latent_hacker._latent_cache:
            raise ValueError(f"Style '{base_style}' not found")

        base_latent = self.latent_hacker._latent_cache[base_style]

        import numpy as np

        explorations = []

        for dim in range(dimensions):
            # Generate random direction in noise space
            direction = np.random.randn(*base_latent.noise_recovered.shape)
            direction = direction / np.linalg.norm(direction)

            for i, alpha in enumerate(np.linspace(-variation_strength, variation_strength, samples_per_dim)):
                # Create variation
                varied_noise = base_latent.noise_recovered + alpha * direction

                # Hash for seed
                import hashlib
                noise_hash = hashlib.sha256(varied_noise.tobytes()).hexdigest()
                seed = int(noise_hash[:8], 16) % (2**31)

                explorations.append({
                    "dimension": dim,
                    "sample": i,
                    "alpha": alpha,
                    "seed": seed,
                    "description": f"Exploration dim={dim}, alpha={alpha:.2f}",
                })

        logger.info(f"Generated {len(explorations)} exploration points from '{base_style}'")
        return explorations

    async def find_similar_styles(
        self,
        target_style: str,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find styles most similar to a target style.

        Uses latent space similarity for comparison.

        Args:
            target_style: Style to find matches for
            top_k: Number of results to return

        Returns:
            List of (style_name, similarity_score) tuples
        """
        similarities = []

        for style_name in self.latent_hacker._latent_cache:
            if style_name == target_style or style_name.startswith("_"):
                continue

            try:
                sim = self.latent_hacker.compute_style_similarity(target_style, style_name)
                similarities.append((style_name, sim))
            except Exception:
                continue

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    async def cross_model_arbitrage(
        self,
        prompt: str,
        quality_model: str = "flux-dev",
        speed_model: str = "sdxl-turbo",
        strength: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Implement capability arbitrage: quality model -> speed model.

        Generate high-quality reference with slow model, then transfer
        style to fast model for rapid iteration.

        Args:
            prompt: Generation prompt
            quality_model: High-quality (slow) model
            speed_model: Fast model for production
            strength: Transfer strength

        Returns:
            Parameters for fast generation with quality style
        """
        # This creates a workflow plan for the arbitrage
        plan = {
            "phase_1_quality": {
                "model": quality_model,
                "prompt": prompt,
                "purpose": "Generate high-quality reference",
                "capture_as": f"_arbitrage_{hash(prompt) % 10000}",
            },
            "phase_2_transfer": {
                "target_model": speed_model,
                "apply_style": f"_arbitrage_{hash(prompt) % 10000}",
                "strength": strength,
                "purpose": "Transfer quality style to fast model",
            },
            "expected_benefit": {
                "quality_time_ms": 20000,  # Typical for flux-dev
                "speed_time_ms": 5000,    # Typical for sdxl-turbo
                "speedup": 4.0,
                "quality_preserved": f"{strength * 100:.0f}%",
            },
        }

        self.stats["cross_model_transfers"] += 1

        logger.info(f"Created arbitrage plan: {quality_model} -> {speed_model}")
        return plan

    async def blend_styles_experiment(
        self,
        style_a: str,
        style_b: str,
        prompt: str,
        num_samples: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Create a series of blended styles between two endpoints.

        Useful for finding interesting style combinations.

        Args:
            style_a: First style
            style_b: Second style
            prompt: Test prompt for all blends
            num_samples: Number of blend points

        Returns:
            List of blend parameters
        """
        import numpy as np

        blends = []

        for alpha in np.linspace(0.0, 1.0, num_samples):
            try:
                result = self.latent_hacker.interpolate_styles(
                    style_a=style_a,
                    style_b=style_b,
                    alpha=alpha,
                    target_prompt=prompt,
                )

                blends.append({
                    "alpha": alpha,
                    "style_a_weight": 1 - alpha,
                    "style_b_weight": alpha,
                    "guided_prompt": result.guided_prompt,
                    "guided_seed": result.guided_seed,
                    "description": f"{style_a} ({(1-alpha)*100:.0f}%) + {style_b} ({alpha*100:.0f}%)",
                })

            except Exception as e:
                logger.warning(f"Failed to blend at alpha={alpha}: {e}")

        self.stats["interpolations"] += len(blends)

        logger.info(f"Created {len(blends)} blend experiments between '{style_a}' and '{style_b}'")
        return blends

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        return {
            **self.stats,
            "cached_styles": len(self.latent_hacker._latent_cache),
            "library_styles": len(self.style_library),
            "active_plans": len(self.active_plans),
        }

    def get_style_categories(self) -> Dict[str, List[str]]:
        """Get styles organized by category."""
        categories: Dict[str, List[str]] = {}

        for name, entry in self.style_library.items():
            if entry.category not in categories:
                categories[entry.category] = []
            categories[entry.category].append(name)

        return categories


# Integration with AGI Orchestrator
async def integrate_with_agi_orchestrator():
    """
    Integration point for the AGI Orchestrator.

    This function demonstrates how LatentOrchestrationAgent
    fits into the 6-phase AGI workflow.
    """
    agent = LatentOrchestrationAgent()

    # Phase 1: Goal Decomposition
    # When goal involves visual content, decompose into:
    # - Style requirements
    # - Consistency constraints
    # - Model selection

    # Phase 2: Context Synthesis
    # Gather from memory:
    # - Previous successful styles
    # - User preferences
    # - Available models

    # Phase 3: Multi-Agent Coordination
    # Parallel execution of:
    # - Style generation
    # - Quality assessment
    # - Consistency verification

    # Phase 4: Meta-Learning
    # Track:
    # - Which styles work well together
    # - Optimal transfer strengths
    # - Model-specific behaviors

    # Phase 5: Skill Evolution
    # Improve:
    # - Style capture timing
    # - Blend ratios
    # - Cross-model mappings

    # Phase 6: Darwin Godel
    # Propose:
    # - New noise schedule experiments
    # - Novel interpolation methods
    # - Architecture-specific optimizations

    return agent


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    async def demo():
        agent = LatentOrchestrationAgent()

        print("LatentOrchestrationAgent Demo")
        print("=" * 50)

        # Check stats
        stats = agent.get_stats()
        print(f"\nInitial stats: {stats}")

        # Create arbitrage plan
        plan = await agent.cross_model_arbitrage(
            prompt="A majestic dragon in a crystal cave",
            quality_model="flux-dev",
            speed_model="sdxl-turbo",
        )
        print(f"\nArbitrage plan: {plan}")

        print("\nDemo complete!")

    asyncio.run(demo())
