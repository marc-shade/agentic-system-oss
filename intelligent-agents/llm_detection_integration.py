#!/usr/bin/env python3
"""
LLM Detection Integration for Autonomous AGI Loop

This module provides the integration layer between the autonomous loop
and the LLM-based code analyzer. Use this to replace hardcoded detection.

Usage in autonomous_recursive_agi_loop.py:
    from llm_detection_integration import detect_improvements_with_llm

    # Replace:
    # modifications = await self._detect_improvements(insights)
    # With:
    # modifications = await detect_improvements_with_llm(self, insights)
"""

import json
import logging
from pathlib import Path
from typing import List

from darwin_godel_machine import DarwinGodelMachine, ModificationType
from llm_code_analyzer import create_llm_detector

logger = logging.getLogger(__name__)


async def detect_improvements_with_llm(loop_instance, insights: List) -> List:
    """
    Detect improvement opportunities using LLM-based analysis.

    This replaces hardcoded detection with AI that can analyze ANY code.
    Based on SymPrompt (arXiv:2507.05619) - Execution-Path-Guided Code Generation.

    Args:
        loop_instance: Instance of AutonomousRecursiveAGILoop
        insights: List of synthesized insights from knowledge acquisition

    Returns:
        List of modification proposals from Darwin Gödel Machine
    """
    logger.info("  Analyzing system for improvement opportunities (LLM mode)...")

    # Lazy initialization of LLM detector
    if not hasattr(loop_instance, 'llm_detector') or loop_instance.llm_detector is None:
        logger.info("  Initializing LLM code detector...")
        loop_instance.llm_detector = create_llm_detector(use_ollama=True)

    # Load configuration to get target files
    config_path = Path("/Volumes/SSDRAID0/agentic-system/agi_config.json")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config: {e}, using default target")
        config = {"target_files": {"practice_targets": ["intelligent-agents/sample_module.py"]}}

    # Determine which targets to analyze
    target_config = config.get("target_files", {})
    use_production = target_config.get("use_production_targets", False)

    if use_production:
        target_files = target_config.get("production_targets", [])
        logger.info(f"  Using PRODUCTION targets: {len(target_files)} files")
    else:
        target_files = target_config.get("practice_targets", [])
        logger.info(f"  Using PRACTICE targets: {len(target_files)} files")

    if not target_files:
        logger.warning("  No target files configured")
        return []

    modifications = []

    # Analyze each target file with LLM
    for target_file in target_files[:1]:  # Start with first file
        target_path = Path("/Volumes/SSDRAID0/agentic-system") / target_file

        if not target_path.exists():
            logger.error(f"  Target file not found: {target_file}")
            continue

        logger.info(f"  Analyzing: {target_file}")

        # Read the target file
        try:
            with open(target_path, 'r') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f"  Failed to read target file: {e}")
            continue

        # Use LLM to detect improvements
        try:
            proposals = loop_instance.llm_detector.detect_improvements(
                code=file_content,
                target_file=target_file,
                insights=insights
            )

            # Convert LLM proposals to Darwin Gödel modifications
            for proposal in proposals:
                modification = loop_instance.darwin_godel.propose_modification(
                    code_before=proposal.code_before,
                    code_after=proposal.code_after,
                    modification_type=ModificationType.ALGORITHM_IMPROVE,
                    description=f"{proposal.description} (LLM confidence: {proposal.confidence_score:.2f})"
                )
                modifications.append(modification)

                logger.info(f"  ✓ LLM detected: {proposal.function_name}")
                logger.info(f"    Type: {proposal.optimization_type.value}")
                logger.info(f"    Expected improvement: {proposal.expected_improvement:.1%}")
                logger.info(f"    Confidence: {proposal.confidence_score:.2f}")
                logger.info(f"    Safety score: {proposal.safety_score:.2f}")

        except Exception as e:
            logger.error(f"  LLM detection failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    if not modifications:
        logger.info("  No improvements detected in this cycle")

    return modifications
