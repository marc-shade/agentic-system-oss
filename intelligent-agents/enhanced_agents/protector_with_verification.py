#!/usr/bin/env python3
"""
Enhanced Code Evolution Protector with Chain of Verification

Wraps the existing Code Evolution Protector with advanced prompting techniques:
- Chain of Verification for evolution vs bug decisions
- Edge Case Learning for protection patterns
- Reasoning Scaffolds for complex code analysis

This demonstrates integration without rewriting existing agents.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "specialized"))
sys.path.insert(0, str(Path(__file__).parent.parent / "advanced_prompting"))

from code_evolution_protector import CodeEvolutionProtector
from chain_of_verification import ChainOfVerification
from edge_case_learning import EdgeCaseLearner, EdgeCaseSeverity
from reasoning_scaffolds import build_full_scaffold

logger = logging.getLogger(__name__)


class EnhancedCodeEvolutionProtector(CodeEvolutionProtector):
    """
    Code Evolution Protector with advanced prompting integration.

    Adds:
    - Chain of Verification for evolution vs bug decisions
    - Edge Case Learning for protection patterns
    - Reasoning Scaffolds for complex code analysis
    """

    def __init__(self, evolution_config_path: str, enable_verification: bool = True):
        """
        Initialize enhanced protector.

        Args:
            evolution_config_path: Path to evolution phases config
            enable_verification: Whether to enable verification (default: True)
        """
        super().__init__(evolution_config_path)

        self.enable_verification = enable_verification

        # Initialize advanced prompting components
        if self.enable_verification:
            self.verifier = ChainOfVerification(
                cli_tool=self.cli_tool,
                adversarial_enabled=True,
                confidence_threshold=0.75  # Slightly stricter for code changes
            )
            logger.info("✅ Chain of Verification enabled")
        else:
            self.verifier = None
            logger.info("⚠️  Chain of Verification disabled")

        # Initialize edge case learner
        self.edge_learner = EdgeCaseLearner()
        logger.info(f"✅ Edge Case Learner initialized ({len(self.edge_learner.edge_cases)} cases loaded)")

        # Track verification outcomes
        self.verification_stats = {
            "total_verifications": 0,
            "passed": 0,
            "failed": 0,
            "prevented_bugs": 0,
            "allowed_evolution": 0
        }

    async def enhanced_change_analysis(
        self,
        file_path: str,
        change_description: str,
        context: Dict[str, Any] = None
    ) -> Tuple[bool, str, float]:
        """
        Analyze code change with verification if needed.

        Args:
            file_path: Path to changed file
            change_description: Description of change
            context: Additional context

        Returns:
            (allowed, reasoning, confidence)
        """
        context = context or {}

        # First, use base class logic
        base_allowed, base_reasoning = self.is_change_allowed(file_path, change_description)

        # If base logic is confident, respect it
        if "BLOCKED" in base_reasoning and "Security concern" in base_reasoning:
            # Security block - don't override
            logger.warning(f"🚫 Security block: {base_reasoning}")
            return False, base_reasoning, 1.0

        # For uncertain cases, use verification
        if self.enable_verification and ("uncertain" in base_reasoning.lower() or not base_allowed):
            logger.info(f"🔍 Uncertain code change, running verification: {file_path}")

            try:
                verification_result = await self.verifier.verify_decision(
                    decision=f"Allow code change: {change_description}",
                    context={
                        "file_path": file_path,
                        "change_description": change_description,
                        "base_reasoning": base_reasoning,
                        "current_phase": self.current_phase.get("name") if self.current_phase else None,
                        **context
                    },
                    agent=self
                )

                self.verification_stats["total_verifications"] += 1

                if verification_result.passed:
                    self.verification_stats["passed"] += 1

                    # Check if this was allowing evolution or preventing bug
                    if "evolution" in verification_result.final_decision.lower():
                        self.verification_stats["allowed_evolution"] += 1
                        logger.info(f"✅ Verification PASSED - Evolution allowed")
                    else:
                        logger.info(f"✅ Verification PASSED")

                    return True, verification_result.final_decision, verification_result.confidence
                else:
                    self.verification_stats["failed"] += 1
                    self.verification_stats["prevented_bugs"] += 1
                    logger.warning(f"❌ Verification FAILED - Bug prevented")

                    # Learn from this edge case
                    await self._record_protection_edge_case(
                        file_path, change_description, verification_result, context
                    )

                    return False, f"BLOCKED: {verification_result.failures[0]}", verification_result.confidence

            except Exception as e:
                logger.error(f"Verification error: {e}")
                # On verification error, be cautious - block
                return False, f"BLOCKED: Verification error (being cautious): {e}", 0.5

        # No verification needed - use base decision
        return base_allowed, base_reasoning, 0.6

    async def _record_protection_edge_case(
        self,
        file_path: str,
        change_description: str,
        verification_result: Any,
        context: Dict[str, Any]
    ):
        """Record a protection edge case for learning"""
        try:
            edge_case = self.edge_learner.record_edge_case(
                input_text=f"File: {file_path}\nChange: {change_description}",
                expected_output="BLOCK",
                actual_output="Would have ALLOWED without verification",
                category="code_protection",
                context={
                    "file_path": file_path,
                    "failures": verification_result.failures,
                    "confidence": verification_result.confidence,
                    **context
                }
            )

            logger.info(f"📝 Recorded edge case: {edge_case.id} ({edge_case.severity.value})")

        except Exception as e:
            logger.error(f"Failed to record edge case: {e}")

    async def analyze_with_scaffold(
        self,
        file_path: str,
        change_description: str,
        analysis_type: str = "analysis"
    ) -> str:
        """
        Analyze code change using reasoning scaffolds.

        Args:
            file_path: Path to file
            change_description: Description of change
            analysis_type: Type of analysis (analysis, debug, design)

        Returns:
            Scaffolded analysis
        """
        logger.info(f"📊 Analyzing with scaffold: {file_path}")

        # Build scaffold for code analysis
        problem = f"""Analyze this code change:

File: {file_path}
Change: {change_description}

Current Evolution Phase: {self.current_phase.get('name') if self.current_phase else 'None'}

Determine:
1. Is this intentional evolution or a bug?
2. Does it match expected evolution patterns?
3. Are there security concerns?
4. Should this change be allowed?
"""

        scaffold = await build_full_scaffold(
            problem=problem,
            context_tags=["code_analysis", "security", "evolution"],
            template_type=analysis_type,
            memory_client=self.memory if self.memory.is_enabled() else None
        )

        logger.info(f"Scaffold created ({len(scaffold)} chars)")

        return scaffold

    def get_edge_case_insights(self) -> Dict[str, Any]:
        """Get insights from edge case learning"""
        metrics = self.edge_learner.get_quality_metrics()

        # Get recent edge cases
        recent_cases = sorted(
            self.edge_learner.edge_cases.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )[:10]

        return {
            "metrics": metrics,
            "recent_cases": [
                {
                    "id": case.id,
                    "severity": case.severity.value,
                    "pattern": case.pattern,
                    "timestamp": case.timestamp.isoformat()
                }
                for case in recent_cases
            ],
            "patterns_learned": list(self.edge_learner.pattern_index.keys())
        }

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        stats = self.verification_stats.copy()

        if stats["total_verifications"] > 0:
            stats["pass_rate"] = stats["passed"] / stats["total_verifications"]
            stats["prevention_rate"] = stats["prevented_bugs"] / stats["total_verifications"]
            stats["evolution_rate"] = stats["allowed_evolution"] / stats["total_verifications"]
        else:
            stats["pass_rate"] = 0.0
            stats["prevention_rate"] = 0.0
            stats["evolution_rate"] = 0.0

        # Add edge case stats
        stats["edge_case_metrics"] = self.edge_learner.get_quality_metrics()

        return stats

    async def execute_decision(self, decision: Any, observations: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Override execute_decision to add verification layer.
        """
        # For code evolution protector, we override the change analysis
        # The actual execution would call enhanced_change_analysis

        result = super().execute_decision(decision, observations)

        # Add verification stats
        result["verification_stats"] = self.get_verification_stats()

        return result

    def start(self, check_interval: int = 120):
        """
        Start the enhanced protector.

        Adds verification stats to startup info.
        """
        print("=" * 60)
        print("🛡️  ENHANCED Code Evolution Protector Starting 🛡️")
        print("=" * 60)
        print(f"CLI Tool: {self.cli_tool}")
        print(f"Current Phase: {self.current_phase.get('name') if self.current_phase else 'None'}")
        print(f"Check interval: {check_interval}s")
        print()
        print("✨ ADVANCED PROMPTING ENABLED ✨")
        print(f"   • Chain of Verification: {'✅ Active' if self.enable_verification else '❌ Disabled'}")
        print(f"   • Edge Case Learning: ✅ Active ({len(self.edge_learner.edge_cases)} cases)")
        print(f"   • Reasoning Scaffolds: ✅ Available")
        print()
        print("🛡️  Enhanced Protection:")
        print("   • Uncertain changes verified with 5-phase CoV")
        print("   • Edge cases learned and stored")
        print("   • Protection patterns continuously improving")
        print("   • Complex analysis uses reasoning scaffolds")
        print()

        # Show edge case metrics
        metrics = self.edge_learner.get_quality_metrics()
        print(f"📊 Edge Case Metrics:")
        print(f"   • Total edge cases: {metrics['total_edge_cases']}")
        print(f"   • False negative rate: {metrics['false_negative_rate']:.2%}")
        print(f"   • Boundary coverage: {metrics['boundary_detection_coverage']:.2%}")
        print(f"   • Patterns detected: {len(metrics['patterns_detected'])}")
        print()

        # Run parent start method
        super().start(check_interval)


async def main():
    """Main entry point for enhanced protector"""
    # Evolution configuration
    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    enable_verification = "--no-verification" not in sys.argv

    # Create and start enhanced protector
    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=enable_verification
    )

    protector.start(check_interval=120)


if __name__ == "__main__":
    asyncio.run(main())
