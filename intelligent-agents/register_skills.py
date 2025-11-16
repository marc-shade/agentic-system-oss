#!/usr/bin/env python3
"""
Skill Registration Script
=========================

Registers initial skill library with the Skill Evolution System.
"""

import asyncio
import logging
from skill_evolution_system import SkillEvolutionSystem
from skills import (
    filter_positive_numbers,
    batch_processor,
    data_transformer,
    complexity_analyzer,
    import_detector,
    function_counter,
    regex_matcher,
    structural_pattern_finder,
    anomaly_detector,
    query_optimizer,
    CacheManager,
    batch_optimizer,
    safe_executor,
    retry_handler,
    graceful_degrader
)
import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_all_skills():
    """Register all skills from the initial library."""
    system = SkillEvolutionSystem()

    skills = [
        # Data Processing
        (filter_positive_numbers, "Data processing: filter positive numbers"),
        (batch_processor, "Data processing: batch items for efficiency"),
        (data_transformer, "Data processing: apply transformations"),

        # Code Analysis
        (complexity_analyzer, "Code analysis: measure complexity metrics"),
        (import_detector, "Code analysis: detect imports"),
        (function_counter, "Code analysis: count functions"),

        # Pattern Matching
        (regex_matcher, "Pattern matching: regex pattern finder"),
        (structural_pattern_finder, "Pattern matching: structural patterns in data"),
        (anomaly_detector, "Pattern matching: detect anomalies"),

        # Optimization
        (query_optimizer, "Optimization: optimize query strings"),
        (batch_optimizer, "Optimization: batch items optimally"),

        # Error Handling
        (safe_executor, "Error handling: safe function execution"),
        (retry_handler, "Error handling: retry logic decorator"),
        (graceful_degrader, "Error handling: graceful degradation"),
    ]

    logger.info(f"Registering {len(skills)} skills...")

    for func, description in skills:
        try:
            # Get function source code
            code = inspect.getsource(func)

            # Register skill
            skill = system.register_skill(
                skill_name=func.__name__,
                code=code,
                description=description
            )

            logger.info(f"✓ Registered: {func.__name__} (v{skill.version})")

        except Exception as e:
            logger.error(f"✗ Failed to register {func.__name__}: {e}")

    logger.info(f"\n✓ Skill registration complete!")
    logger.info(f"Total skills: {len(skills)}")


if __name__ == "__main__":
    register_all_skills()
