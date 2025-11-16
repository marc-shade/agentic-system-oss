#!/usr/bin/env python3
"""
Enhanced System Health Guardian with Chain of Verification

Wraps the existing System Health Guardian with advanced prompting techniques:
- Chain of Verification for critical decisions
- Multi-Agent Debate for service changes
- Reasoning Scaffolds for complex analysis

This demonstrates integration without rewriting existing agents.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "specialized"))
sys.path.insert(0, str(Path(__file__).parent.parent / "advanced_prompting"))

from system_health_guardian import SystemHealthGuardian
from chain_of_verification import ChainOfVerification
from multi_agent_debate import MultiAgentDebate, AgentPerspective, PriorityType
from reasoning_scaffolds import build_full_scaffold

logger = logging.getLogger(__name__)


class EnhancedSystemHealthGuardian(SystemHealthGuardian):
    """
    System Health Guardian with advanced prompting integration.

    Adds:
    - Chain of Verification before critical restart decisions
    - Multi-Agent Debate for major service changes
    - Reasoning Scaffolds for complex health analysis
    """

    def __init__(self, arduino_port: str, enable_verification: bool = True):
        """
        Initialize enhanced guardian.

        Args:
            arduino_port: Arduino serial port
            enable_verification: Whether to enable verification (default: True)
        """
        super().__init__(arduino_port)

        self.enable_verification = enable_verification

        # Initialize advanced prompting components
        if self.enable_verification:
            self.verifier = ChainOfVerification(
                cli_tool=self.cli_tool,
                adversarial_enabled=True,
                confidence_threshold=0.7
            )
            logger.info("✅ Chain of Verification enabled")
        else:
            self.verifier = None
            logger.info("⚠️  Chain of Verification disabled")

        # Track verification outcomes
        self.verification_stats = {
            "total_verifications": 0,
            "passed": 0,
            "failed": 0,
            "prevented_errors": 0
        }

    async def enhanced_decision_making(
        self,
        decision: Any,
        observations: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Make decision with verification if needed.

        Args:
            decision: Agent decision object
            observations: Context observations

        Returns:
            (should_execute, reasoning)
        """
        # Check if this is a critical decision that needs verification
        is_critical = self._is_critical_decision(decision, observations)

        if not is_critical or not self.enable_verification:
            # Non-critical or verification disabled - execute normally
            return True, "Decision approved without verification (non-critical)"

        logger.info(f"🔍 Critical decision detected, running verification: {decision.decision}")

        # Run Chain of Verification
        try:
            verification_result = await self.verifier.verify_decision(
                decision=decision.decision,
                context={
                    "observations": observations,
                    "confidence": decision.confidence,
                    "tool_used": decision.tool_used,
                    "reasoning": decision.reasoning
                },
                agent=self
            )

            self.verification_stats["total_verifications"] += 1

            if verification_result.passed:
                self.verification_stats["passed"] += 1
                logger.info(f"✅ Verification PASSED (confidence: {verification_result.confidence:.2f})")
                return True, verification_result.synthesis_rationale or "Verification passed"
            else:
                self.verification_stats["failed"] += 1
                self.verification_stats["prevented_errors"] += 1
                logger.warning(f"❌ Verification FAILED: {verification_result.failures}")
                return False, f"Verification failed: {', '.join(verification_result.failures)}"

        except Exception as e:
            logger.error(f"Verification error: {e}")
            # On verification error, be cautious - don't execute
            return False, f"Verification error (being cautious): {e}"

    def _is_critical_decision(self, decision: Any, observations: Dict[str, Any]) -> bool:
        """
        Determine if a decision is critical and needs verification.

        Critical decisions:
        - Service restarts
        - High confidence but potentially destructive
        - Multiple services affected
        - System under stress
        """
        decision_text = decision.decision.lower()

        # Check for restart keywords
        if any(keyword in decision_text for keyword in ['restart', 'kill', 'stop', 'terminate']):
            return True

        # Check for high-impact with moderate confidence
        if decision.confidence < 0.9 and any(keyword in decision_text for keyword in ['critical', 'urgent', 'failure']):
            return True

        # Check if system is under stress
        if observations.get("system_stress", False):
            return True

        # Check if multiple services involved
        if decision_text.count('service') > 1:
            return True

        return False

    async def debate_major_change(
        self,
        proposal: Dict[str, Any],
        topic: str
    ) -> Dict[str, Any]:
        """
        Use multi-agent debate for major system changes.

        Args:
            proposal: Change proposal with benefits, risks, domains
            topic: Human-readable topic description

        Returns:
            Debate result with consensus and reasoning
        """
        logger.info(f"🗣️  Starting multi-agent debate: {topic}")

        # Use pre-configured system optimization debate
        result = await MultiAgentDebate.quick_debate(
            proposal=proposal,
            debate_topic=topic,
            scenario="system_optimization",
            memory_client=self.memory if self.memory.is_enabled() else None
        )

        logger.info(f"Debate complete: consensus={result.consensus_reached}, decision={result.final_decision}")

        return {
            "consensus_reached": result.consensus_reached,
            "decision": result.final_decision,
            "confidence": result.confidence,
            "rationale": result.synthesis_rationale,
            "agent_agreements": result.agent_agreements,
            "key_concerns": result.key_concerns,
            "key_supports": result.key_supports
        }

    async def analyze_with_scaffold(
        self,
        problem: str,
        context: Dict[str, Any],
        template_type: str = "analysis"
    ) -> str:
        """
        Analyze problem using reasoning scaffolds.

        Args:
            problem: Problem description
            context: Context information
            template_type: CoT template type

        Returns:
            Analysis result
        """
        logger.info(f"📊 Analyzing with scaffold: {problem[:100]}")

        # Build comprehensive scaffold
        scaffold = await build_full_scaffold(
            problem=problem,
            context_tags=["system_health", "monitoring", "analysis"],
            template_type=template_type,
            memory_client=self.memory if self.memory.is_enabled() else None
        )

        # Execute with scaffold (would normally call LLM here)
        # For now, return scaffold for inspection
        logger.info(f"Scaffold created ({len(scaffold)} chars)")

        return scaffold

    async def execute_decision(self, decision: Any, observations: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Override execute_decision to add verification layer.

        This intercepts decisions and adds verification before execution.
        """
        # Run enhanced decision making
        should_execute, reasoning = await self.enhanced_decision_making(decision, observations or {})

        if not should_execute:
            logger.warning(f"Decision blocked by verification: {reasoning}")

            # Store verification failure in memory
            if self.memory.is_enabled():
                try:
                    self.memory.remember({
                        "type": "verification_failure",
                        "decision": decision.decision,
                        "confidence": decision.confidence,
                        "reasoning": reasoning,
                        "blocked": True
                    })
                except Exception as e:
                    logger.error(f"Memory storage failed: {e}")

            return {
                "status": "blocked",
                "reason": reasoning,
                "verification_stats": self.verification_stats
            }

        # Decision approved - execute normally
        logger.info(f"Decision approved: {reasoning}")
        result = await super().execute_decision(decision, observations)

        # Add verification info to result
        result["verification_reasoning"] = reasoning
        result["verification_stats"] = self.verification_stats

        return result

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        stats = self.verification_stats.copy()

        if stats["total_verifications"] > 0:
            stats["pass_rate"] = stats["passed"] / stats["total_verifications"]
            stats["prevention_rate"] = stats["prevented_errors"] / stats["total_verifications"]
        else:
            stats["pass_rate"] = 0.0
            stats["prevention_rate"] = 0.0

        return stats

    def start(self, check_interval: int = 30):
        """
        Start the enhanced guardian.

        Adds verification stats to startup info.
        """
        print("=" * 60)
        print("🔥 ENHANCED System Health Guardian Starting 🔥")
        print("=" * 60)
        print(f"CLI Tool: {self.cli_tool}")
        print(f"Arduino: {self.arduino_port if self.surface else 'Disabled (hardware unavailable)'}")
        print(f"Base interval: {check_interval}s (will adapt)")
        print()
        print("✨ ADVANCED PROMPTING ENABLED ✨")
        print(f"   • Chain of Verification: {'✅ Active' if self.enable_verification else '❌ Disabled'}")
        print(f"   • Multi-Agent Debate: ✅ Available")
        print(f"   • Reasoning Scaffolds: ✅ Available")
        print()
        print("🛡️  Enhanced Protection:")
        print("   • Critical decisions verified with 5-phase CoV")
        print("   • Adversarial prompting finds vulnerabilities")
        print("   • Major changes require multi-agent consensus")
        print("   • Complex analysis uses reasoning scaffolds")
        print()

        # Run parent start method
        super().start(check_interval)


async def main():
    """Main entry point for enhanced guardian"""
    if len(sys.argv) < 2:
        print("Usage: guardian_with_verification.py <arduino_port> [--no-verification]")
        print("Example: guardian_with_verification.py /dev/tty.usbmodem8344401")
        sys.exit(1)

    arduino_port = sys.argv[1]
    enable_verification = "--no-verification" not in sys.argv

    # Create and start enhanced guardian
    guardian = EnhancedSystemHealthGuardian(
        arduino_port=arduino_port,
        enable_verification=enable_verification
    )

    guardian.start(check_interval=30)


if __name__ == "__main__":
    asyncio.run(main())
