"""
Verifier Agent - Validates execution results.

Key responsibilities:
- Check if action achieved expected outcome
- Detect errors and failures
- Trigger replanning when needed
- Quality gate for step completion
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """Result of verification."""
    success: bool
    error: str = ""
    traceback: str = ""
    should_replan: bool = False
    notes: str = ""
    confidence: float = 1.0


# Error patterns to detect
ERROR_PATTERNS = [
    r"error[:\s]",
    r"exception[:\s]",
    r"failed[:\s]",
    r"not found",
    r"permission denied",
    r"timeout",
    r"connection refused",
    r"syntax error",
    r"traceback",
    r"errno",
    r"fatal[:\s]",
    r"cannot\s+\w+",
    r"unable to",
]

# Success patterns
SUCCESS_PATTERNS = [
    r"success",
    r"completed",
    r"created",
    r"written",
    r"saved",
    r"done",
    r"ok\b",
    r"passed",
]


VERIFIER_PROMPT = """You are the Verifier Agent for Project Prometheus.

Your role: Determine if the action achieved its expected outcome.

ACTION:
{action}

EXPECTED OUTCOME:
{expected}

OBSERVATION:
{observation}

Analyze the observation and determine:
1. Did the action succeed?
2. Were there any errors?
3. Is replanning needed?

OUTPUT FORMAT (JSON):
{{
  "success": true/false,
  "error": "error message if failed",
  "should_replan": true/false,
  "notes": "any relevant notes",
  "confidence": 0.0-1.0
}}
"""


class VerifierAgent:
    """
    Validates execution results and triggers replanning.

    Uses both pattern matching and LLM analysis to determine
    if actions succeeded or failed.
    """

    def __init__(self, llm_client=None):
        """
        Initialize verifier.

        Args:
            llm_client: LLM client for complex verification
        """
        self.llm_client = llm_client
        self.error_patterns = [re.compile(p, re.IGNORECASE) for p in ERROR_PATTERNS]
        self.success_patterns = [re.compile(p, re.IGNORECASE) for p in SUCCESS_PATTERNS]

    async def verify(
        self,
        action: dict,
        observation: str,
        expected_outcome: str = None
    ) -> VerifyResult:
        """
        Verify if action succeeded.

        Args:
            action: The action that was executed
            observation: The result/output of the action
            expected_outcome: What we expected to see

        Returns:
            VerifyResult with success status
        """
        logger.info(f"Verifying action: {action.get('tool', 'unknown')}")

        # Quick pattern-based check first
        quick_result = self._quick_verify(observation)

        if quick_result.confidence > 0.9:
            # High confidence from patterns, use it
            return quick_result

        # If LLM available and we have expected outcome, use it
        if self.llm_client and expected_outcome:
            return await self._llm_verify(action, observation, expected_outcome)

        # Fall back to pattern result
        return quick_result

    def _quick_verify(self, observation: str) -> VerifyResult:
        """Quick pattern-based verification."""
        obs_lower = observation.lower()

        # Count error and success signals
        error_count = sum(1 for p in self.error_patterns if p.search(obs_lower))
        success_count = sum(1 for p in self.success_patterns if p.search(obs_lower))

        # Determine result
        if error_count > 0 and success_count == 0:
            # Clear error
            return VerifyResult(
                success=False,
                error=self._extract_error(observation),
                should_replan=True,
                confidence=0.8 + min(error_count * 0.05, 0.15)
            )

        elif success_count > 0 and error_count == 0:
            # Clear success
            return VerifyResult(
                success=True,
                confidence=0.8 + min(success_count * 0.05, 0.15)
            )

        elif error_count > success_count:
            # More errors than successes
            return VerifyResult(
                success=False,
                error=self._extract_error(observation),
                should_replan=True,
                confidence=0.6
            )

        elif success_count > error_count:
            # More successes
            return VerifyResult(
                success=True,
                confidence=0.6
            )

        else:
            # Unclear - assume success but low confidence
            return VerifyResult(
                success=True,
                confidence=0.4,
                notes="Unclear result, assuming success"
            )

    def _extract_error(self, observation: str) -> str:
        """Extract the most relevant error message."""
        lines = observation.split("\n")

        # Look for lines with error keywords
        for line in lines:
            line_lower = line.lower()
            if any(p.search(line_lower) for p in self.error_patterns):
                return line.strip()[:200]

        # Return first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()[:200]

        return "Unknown error"

    async def _llm_verify(
        self,
        action: dict,
        observation: str,
        expected: str
    ) -> VerifyResult:
        """Use LLM for complex verification."""
        prompt = VERIFIER_PROMPT.format(
            action=json.dumps(action, indent=2),
            expected=expected,
            observation=observation[:2000]  # Truncate for context
        )

        try:
            response = await self.llm_client.generate(
                system="You are a verification agent. Analyze results accurately.",
                user=prompt
            )

            return self._parse_result(response)

        except Exception as e:
            logger.exception(f"LLM verification failed: {e}")
            # Fall back to pattern matching
            return self._quick_verify(observation)

    def _parse_result(self, response: str) -> VerifyResult:
        """Parse LLM response into VerifyResult."""
        try:
            # Extract JSON
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                response = response[start:end]

            data = json.loads(response.strip())

            return VerifyResult(
                success=data.get("success", False),
                error=data.get("error", ""),
                should_replan=data.get("should_replan", False),
                notes=data.get("notes", ""),
                confidence=data.get("confidence", 0.8)
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse verify result: {e}")
            return VerifyResult(
                success=False,
                error="Failed to parse verification result",
                confidence=0.3
            )

    def is_recoverable(self, error: str) -> bool:
        """Determine if an error is likely recoverable."""
        error_lower = error.lower()

        # Non-recoverable patterns
        fatal_patterns = [
            "permission denied",
            "access denied",
            "authentication failed",
            "not authorized",
            "quota exceeded",
            "disk full",
            "out of memory",
        ]

        for pattern in fatal_patterns:
            if pattern in error_lower:
                return False

        # Likely recoverable
        return True
