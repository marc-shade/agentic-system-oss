#!/usr/bin/env python3
"""
Chain of Verification Framework
================================

Implements mandatory self-correction loops that structure AI generation
to activate latent reasoning patterns through verification steps.

Key Pattern: analyze → critique → cite evidence → revise

This prevents optional self-correction being ignored by embedding
verification as a mandatory structural requirement.

Usage:
    cov = ChainOfVerification(agent_context)
    result = await cov.verify_decision(
        decision="Restart temporal service",
        context={"cpu_percent": 95, "service_down": True}
    )

    if result.passed:
        execute_decision()
    else:
        log_failure(result.failures)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import sys

# Add SDK agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
from cli_agent import CLIAgent

logger = logging.getLogger(__name__)


class VerificationPhase(Enum):
    """Phases of the verification chain"""
    ANALYZE = "analyze"
    CRITIQUE = "critique"
    CITE_EVIDENCE = "cite_evidence"
    REVISE = "revise"
    ADVERSARIAL = "adversarial"


@dataclass
class VerificationStep:
    """Single step in verification chain"""
    phase: VerificationPhase
    prompt: str
    response: Optional[str] = None
    passed: bool = False
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    issues_found: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Complete verification chain result"""
    decision: str
    context: Dict[str, Any]
    steps: List[VerificationStep]
    passed: bool
    final_decision: str
    confidence: float
    failures: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "decision": self.decision,
            "context": self.context,
            "steps": [
                {
                    "phase": step.phase.value,
                    "prompt": step.prompt,
                    "response": step.response,
                    "passed": step.passed,
                    "confidence": step.confidence,
                    "issues_found": step.issues_found
                }
                for step in self.steps
            ],
            "passed": self.passed,
            "final_decision": self.final_decision,
            "confidence": self.confidence,
            "failures": self.failures,
            "timestamp": self.timestamp.isoformat()
        }


class ChainOfVerification:
    """
    Chain of Verification - Mandatory self-correction framework

    Embeds verification loops within decision-making to activate
    trained reasoning modes and prevent hasty/incorrect decisions.
    """

    def __init__(
        self,
        cli_tool: str = "gemini",
        adversarial_enabled: bool = True,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize Chain of Verification

        Args:
            cli_tool: CLI tool to use (gemini, codex, claude)
            adversarial_enabled: Whether to include adversarial prompting
            confidence_threshold: Minimum confidence to pass verification
        """
        self.cli_tool = cli_tool
        self.adversarial_enabled = adversarial_enabled
        self.confidence_threshold = confidence_threshold
        self.verification_history: List[VerificationResult] = []

        logger.info(f"ChainOfVerification initialized with {cli_tool}")

    async def verify_decision(
        self,
        decision: str,
        context: Dict[str, Any],
        agent: Optional[CLIAgent] = None
    ) -> VerificationResult:
        """
        Run complete verification chain on a decision

        Args:
            decision: The decision to verify
            context: Context about the decision
            agent: Optional agent instance for CLI execution

        Returns:
            VerificationResult with all verification steps
        """
        logger.info(f"Starting verification chain for: {decision}")

        steps: List[VerificationStep] = []

        # Phase 1: Analyze
        analyze_step = await self._phase_analyze(decision, context, agent)
        steps.append(analyze_step)

        if not analyze_step.passed:
            return self._create_result(decision, context, steps, False)

        # Phase 2: Critique
        critique_step = await self._phase_critique(
            decision, context, analyze_step.response, agent
        )
        steps.append(critique_step)

        # Phase 3: Cite Evidence
        evidence_step = await self._phase_cite_evidence(
            decision, context, critique_step.response, agent
        )
        steps.append(evidence_step)

        # Phase 4: Revise (if issues found)
        if critique_step.issues_found or evidence_step.issues_found:
            revise_step = await self._phase_revise(
                decision,
                context,
                critique_step.issues_found + evidence_step.issues_found,
                agent
            )
            steps.append(revise_step)
            final_decision = revise_step.response or decision
        else:
            final_decision = decision

        # Phase 5: Adversarial (if enabled)
        if self.adversarial_enabled:
            adversarial_step = await self._phase_adversarial(
                final_decision, context, agent
            )
            steps.append(adversarial_step)

            if adversarial_step.issues_found:
                # Adversarial found issues - must revise again
                final_revise = await self._phase_revise(
                    final_decision,
                    context,
                    adversarial_step.issues_found,
                    agent
                )
                steps.append(final_revise)
                final_decision = final_revise.response or final_decision

        # Calculate overall confidence
        avg_confidence = sum(s.confidence for s in steps) / len(steps)
        passed = avg_confidence >= self.confidence_threshold

        result = self._create_result(
            decision, context, steps, passed, final_decision, avg_confidence
        )

        self.verification_history.append(result)
        logger.info(f"Verification {'PASSED' if passed else 'FAILED'} with confidence {avg_confidence:.2f}")

        return result

    async def _phase_analyze(
        self,
        decision: str,
        context: Dict[str, Any],
        agent: Optional[CLIAgent]
    ) -> VerificationStep:
        """Phase 1: Analyze the decision thoroughly"""
        prompt = f"""ANALYZE this decision thoroughly:

Decision: {decision}

Context:
{json.dumps(context, indent=2)}

Your task (ANALYZE phase):
1. Break down the decision into components
2. Identify what would make this decision correct
3. Identify what would make this decision incorrect
4. List key assumptions being made
5. Determine what evidence is needed

Provide detailed analysis focusing on correctness, not just summary.
"""

        response = await self._run_cli(prompt, agent)

        # Simple heuristic: passed if response is substantive (>200 chars)
        passed = len(response) > 200
        confidence = min(len(response) / 500, 1.0)  # Max at 500 chars

        return VerificationStep(
            phase=VerificationPhase.ANALYZE,
            prompt=prompt,
            response=response,
            passed=passed,
            confidence=confidence
        )

    async def _phase_critique(
        self,
        decision: str,
        context: Dict[str, Any],
        analysis: Optional[str],
        agent: Optional[CLIAgent]
    ) -> VerificationStep:
        """Phase 2: Critique the decision and analysis"""
        prompt = f"""CRITIQUE this decision and analysis:

Decision: {decision}

Analysis:
{analysis}

Your task (CRITIQUE phase):
1. Find potential flaws in the decision
2. Identify missing considerations
3. Challenge key assumptions
4. List potential negative consequences
5. Determine confidence level (0.0-1.0)

Be critical and thorough. Finding NO issues is suspicious.
If you find issues, list them clearly as "ISSUE: <description>"
"""

        response = await self._run_cli(prompt, agent)

        # Extract issues
        issues = self._extract_issues(response)

        # Confidence from response if stated, otherwise estimate
        confidence = self._extract_confidence(response)

        return VerificationStep(
            phase=VerificationPhase.CRITIQUE,
            prompt=prompt,
            response=response,
            passed=True,  # Critique always passes, may find issues
            confidence=confidence,
            issues_found=issues
        )

    async def _phase_cite_evidence(
        self,
        decision: str,
        context: Dict[str, Any],
        critique: Optional[str],
        agent: Optional[CLIAgent]
    ) -> VerificationStep:
        """Phase 3: Cite evidence supporting or refuting decision"""
        prompt = f"""CITE EVIDENCE for this decision:

Decision: {decision}

Context:
{json.dumps(context, indent=2)}

Critique:
{critique}

Your task (CITE EVIDENCE phase):
1. List specific evidence from context supporting this decision
2. List specific evidence from context contradicting this decision
3. Identify missing evidence that would be critical
4. Rate evidence quality (strong/moderate/weak)
5. Make evidence-based recommendation

Format evidence citations clearly as:
SUPPORTING: <metric>: <value> - <reasoning>
CONTRADICTING: <metric>: <value> - <reasoning>
MISSING: <evidence needed>
"""

        response = await self._run_cli(prompt, agent)

        # Check if contradicting or missing evidence is substantial
        contradicting = "CONTRADICTING:" in response
        missing_critical = "MISSING:" in response and "CRITICAL" in response.upper()

        issues = []
        if contradicting:
            issues.append("Contradicting evidence found")
        if missing_critical:
            issues.append("Critical evidence missing")

        confidence = self._extract_confidence(response)

        return VerificationStep(
            phase=VerificationPhase.CITE_EVIDENCE,
            prompt=prompt,
            response=response,
            passed=True,
            confidence=confidence,
            issues_found=issues
        )

    async def _phase_revise(
        self,
        decision: str,
        context: Dict[str, Any],
        issues: List[str],
        agent: Optional[CLIAgent]
    ) -> VerificationStep:
        """Phase 4: Revise decision based on issues found"""
        prompt = f"""REVISE this decision to address issues:

Original Decision: {decision}

Issues Found:
{chr(10).join(f'- {issue}' for issue in issues)}

Context:
{json.dumps(context, indent=2)}

Your task (REVISE phase):
1. Address each issue explicitly
2. Modify the decision if needed
3. Explain why the revision solves the issues
4. State revised decision clearly as "REVISED DECISION: <new decision>"
5. If no revision needed, state "REVISED DECISION: <original decision unchanged>"

Be specific and actionable.
"""

        response = await self._run_cli(prompt, agent)

        # Extract revised decision
        revised = self._extract_revised_decision(response)

        confidence = self._extract_confidence(response)

        return VerificationStep(
            phase=VerificationPhase.REVISE,
            prompt=prompt,
            response=revised or response,
            passed=True,
            confidence=confidence
        )

    async def _phase_adversarial(
        self,
        decision: str,
        context: Dict[str, Any],
        agent: Optional[CLIAgent]
    ) -> VerificationStep:
        """Phase 5: Adversarial attack on the decision"""
        prompt = f"""ADVERSARIAL ATTACK - Find ways this decision could fail:

Decision: {decision}

Context:
{json.dumps(context, indent=2)}

Your task (ADVERSARIAL phase):
You are a red team attacker. Find 5 vulnerabilities in this decision:

1. Edge cases where it fails
2. Hidden assumptions that could be wrong
3. Timing issues or race conditions
4. Resource constraints that could cause failure
5. Cascading failures from this decision

For each vulnerability, state clearly:
VULNERABILITY: <specific failure scenario>

Be creative and thorough. Your goal is to BREAK this decision.
"""

        response = await self._run_cli(prompt, agent)

        # Extract vulnerabilities
        vulnerabilities = self._extract_issues(response, keyword="VULNERABILITY:")

        # High confidence if found multiple vulnerabilities (good adversarial analysis)
        confidence = min(len(vulnerabilities) / 5.0, 1.0)

        return VerificationStep(
            phase=VerificationPhase.ADVERSARIAL,
            prompt=prompt,
            response=response,
            passed=True,  # Always passes, reports vulnerabilities
            confidence=confidence,
            issues_found=vulnerabilities
        )

    async def _run_cli(self, prompt: str, agent: Optional[CLIAgent]) -> str:
        """Run CLI tool to process prompt"""
        if agent:
            # Use agent's run_headless method
            try:
                result = agent.run_headless_cli(prompt, format="text")
                if result.get("status") == "success":
                    return result.get("output", "")
            except Exception as e:
                logger.error(f"Agent CLI execution failed: {e}")

        # Fallback to direct CLI execution
        import subprocess
        try:
            result = subprocess.run(
                [self.cli_tool, prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return f"ERROR: {e}"

    def _extract_issues(self, response: str, keyword: str = "ISSUE:") -> List[str]:
        """Extract issues from response"""
        issues = []
        for line in response.split('\n'):
            if keyword in line:
                issue = line.split(keyword, 1)[1].strip()
                issues.append(issue)
        return issues

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score from response"""
        import re
        # Look for patterns like "confidence: 0.8" or "80% confident"
        patterns = [
            r'confidence[:\s]+([0-9.]+)',
            r'([0-9]+)%\s+confident',
            r'confidence\s+level[:\s]+([0-9.]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Normalize percentage to 0-1
                if value > 1.0:
                    value = value / 100.0
                return value

        # Default confidence based on response length and quality indicators
        if "ISSUE:" in response or "VULNERABILITY:" in response:
            return 0.6  # Found issues, moderate confidence
        elif len(response) > 300:
            return 0.75  # Substantive response
        else:
            return 0.5  # Minimal response

    def _extract_revised_decision(self, response: str) -> Optional[str]:
        """Extract revised decision from response"""
        marker = "REVISED DECISION:"
        if marker in response:
            parts = response.split(marker, 1)
            if len(parts) > 1:
                # Get first line after marker
                decision = parts[1].strip().split('\n')[0]
                return decision
        return None

    def _create_result(
        self,
        decision: str,
        context: Dict[str, Any],
        steps: List[VerificationStep],
        passed: bool,
        final_decision: Optional[str] = None,
        confidence: Optional[float] = None
    ) -> VerificationResult:
        """Create verification result"""
        failures = []
        for step in steps:
            if step.issues_found:
                failures.extend(step.issues_found)

        return VerificationResult(
            decision=decision,
            context=context,
            steps=steps,
            passed=passed,
            final_decision=final_decision or decision,
            confidence=confidence or 0.0,
            failures=failures
        )

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get statistics about verification history"""
        if not self.verification_history:
            return {"total": 0}

        total = len(self.verification_history)
        passed = sum(1 for r in self.verification_history if r.passed)
        avg_confidence = sum(r.confidence for r in self.verification_history) / total
        avg_steps = sum(len(r.steps) for r in self.verification_history) / total

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "avg_confidence": avg_confidence,
            "avg_steps": avg_steps
        }
