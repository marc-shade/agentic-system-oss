#!/usr/bin/env python3
"""
Risk Assessment Engine for Human-in-the-Loop
=============================================

Automatically assesses risk level of operations and determines
whether human approval is needed.

Risk Factors:
- Scope: How many systems affected?
- Criticality: Can this break things?
- Reversibility: Can we undo this?
- Test Coverage: Are there tests?
- Novelty: Have we done this before?

Risk Levels:
- Low (0-0.2): Automatic execution
- Medium (0.2-0.5): Notify human
- High (0.5-0.8): Require approval
- Critical (0.8-1.0): Collaborative decision

Usage:
    engine = RiskScoringEngine()

    assessment = engine.assess_task_risk(task_data)

    if assessment.risk_level == "critical":
        # Request human approval
        ...
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level categories."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalTier(str, Enum):
    """Approval requirement tiers."""
    AUTOMATIC = "automatic"       # Execute without approval (risk < 0.2)
    NOTIFICATION = "notification" # Execute but notify (0.2 <= risk < 0.5)
    APPROVAL = "approval"         # Require approval (0.5 <= risk < 0.8)
    COLLABORATIVE = "collaborative" # Collaborative decision (risk >= 0.8)


@dataclass
class RiskFactors:
    """Individual risk factor scores (0.0-1.0)."""
    scope: float           # How many systems affected?
    criticality: float     # Can this break things?
    reversibility: float   # Can we undo this?
    test_coverage: float   # Are there tests?
    novelty: float         # Have we done this before?

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class RiskAssessment:
    """Complete risk assessment for an operation."""
    task_id: str
    risk_score: float
    risk_level: RiskLevel
    approval_tier: ApprovalTier
    risk_factors: RiskFactors
    reasoning: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "approval_tier": self.approval_tier.value,
            "risk_factors": self.risk_factors.to_dict(),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }


class RiskScoringEngine:
    """
    Assesses operation risk and determines approval requirements.

    Uses weighted scoring across multiple risk dimensions.
    """

    # Risk factor weights (must sum to 1.0)
    WEIGHTS = {
        "scope": 0.20,           # 20% weight
        "criticality": 0.30,     # 30% weight (most important)
        "reversibility": 0.20,   # 20% weight
        "test_coverage": 0.15,   # 15% weight
        "novelty": 0.15          # 15% weight
    }

    # Critical operations patterns
    CRITICAL_PATTERNS = [
        r"rm\s+-rf",              # Recursive delete
        r"DROP\s+TABLE",          # Database drops
        r"DELETE\s+FROM",         # Database deletes
        r"truncate",              # File truncation
        r">/dev/null",            # Output redirection
        r"mkfs",                  # Format filesystem
        r"dd\s+if=",              # Disk operations
        r"iptables\s+-F",         # Firewall flush
        r"shutdown",              # System shutdown
        r"reboot",                # System reboot
    ]

    # System paths (modification = high risk)
    CRITICAL_PATHS = [
        "/etc/",
        "/sys/",
        "/proc/",
        "/boot/",
        "/root/",
        "~/.ssh/",
        "~/.config/",
    ]

    def __init__(self, history_file: Optional[Path] = None):
        """
        Initialize risk scoring engine.

        Args:
            history_file: Path to operation history (for novelty scoring)
        """
        if history_file is None:
            history_file = Path.home() / ".cache" / "gitMQ-risk-history.json"

        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        # Load operation history
        self.operation_history = self._load_history()

        logger.info(f"Risk scoring engine initialized")
        logger.info(f"Known operations: {len(self.operation_history)}")

    def _load_history(self) -> Dict[str, int]:
        """Load operation history for novelty scoring."""
        if not self.history_file.exists():
            return {}

        try:
            with open(self.history_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load history: {e}")
            return {}

    def _save_history(self):
        """Save operation history."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.operation_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    def assess_task_risk(self, task: Dict[str, Any]) -> RiskAssessment:
        """
        Assess risk level of a task.

        Args:
            task: Task data (TaskPayload)

        Returns:
            RiskAssessment with score and approval tier
        """
        task_id = task.get("task_id", "unknown")
        task_type = task.get("type", "unknown")
        payload = task.get("payload", {})

        # Calculate individual risk factors
        risk_factors = RiskFactors(
            scope=self._calculate_scope(task),
            criticality=self._calculate_criticality(task),
            reversibility=self._calculate_reversibility(task),
            test_coverage=self._calculate_test_coverage(task),
            novelty=self._calculate_novelty(task)
        )

        # Calculate weighted risk score
        risk_score = sum(
            getattr(risk_factors, factor) * self.WEIGHTS[factor]
            for factor in self.WEIGHTS.keys()
        )

        # Determine risk level
        risk_level = self._get_risk_level(risk_score)
        approval_tier = self._get_approval_tier(risk_score)

        # Generate reasoning
        reasoning = self._generate_reasoning(task, risk_factors, risk_score)

        # Create assessment
        assessment = RiskAssessment(
            task_id=task_id,
            risk_score=risk_score,
            risk_level=risk_level,
            approval_tier=approval_tier,
            risk_factors=risk_factors,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat()
        )

        # Record in history (for future novelty scoring)
        self._record_operation(task)

        logger.info(f"Risk assessment: {task_id}")
        logger.info(f"  Score: {risk_score:.3f}")
        logger.info(f"  Level: {risk_level.value}")
        logger.info(f"  Approval: {approval_tier.value}")

        return assessment

    def _calculate_scope(self, task: Dict[str, Any]) -> float:
        """
        Calculate scope risk (0.0-1.0).

        Factors:
        - Number of nodes affected
        - Target specificity
        - Broadcast vs targeted
        """
        target_node = task.get("target_node", "")

        if target_node == "*" or target_node == "all":
            # Broadcast to all nodes
            return 1.0
        elif target_node.startswith("group:"):
            # Group of nodes
            return 0.6
        else:
            # Single node
            return 0.2

    def _calculate_criticality(self, task: Dict[str, Any]) -> float:
        """
        Calculate criticality risk (0.0-1.0).

        Factors:
        - Dangerous operations
        - System path modifications
        - Destructive commands
        """
        payload = task.get("payload", {})
        code = payload.get("code", "")

        # Check for critical patterns
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning(f"Critical pattern detected: {pattern}")
                return 1.0

        # Check for critical path access
        for critical_path in self.CRITICAL_PATHS:
            if critical_path in code:
                logger.warning(f"Critical path access: {critical_path}")
                return 0.8

        # Check task type
        task_type = task.get("type", "")
        if task_type == "build":
            return 0.5  # Builds can fail but usually safe
        elif task_type == "deployment":
            return 0.7  # Deployments are risky
        elif task_type == "code_execution":
            # Depends on what the code does
            if "import os" in code and "system(" in code:
                return 0.7
            return 0.4

        return 0.3  # Default moderate risk

    def _calculate_reversibility(self, task: Dict[str, Any]) -> float:
        """
        Calculate reversibility risk (0.0-1.0).

        Low score = easily reversible (low risk)
        High score = hard to reverse (high risk)
        """
        payload = task.get("payload", {})
        code = payload.get("code", "")

        # Irreversible operations
        irreversible_patterns = [
            r"rm\s+-rf",
            r"DROP\s+TABLE",
            r"DELETE\s+FROM",
            r"truncate",
            r"mkfs",
        ]

        for pattern in irreversible_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return 1.0  # Cannot undo

        # Check for backup/checkpoint
        if "backup" in code.lower() or "checkpoint" in code.lower():
            return 0.3  # Has backup

        # Code execution generally reversible
        task_type = task.get("type", "")
        if task_type == "code_execution":
            return 0.4
        elif task_type == "build":
            return 0.2  # Can rebuild
        elif task_type == "deployment":
            return 0.6  # Hard to rollback

        return 0.5  # Default moderate

    def _calculate_test_coverage(self, task: Dict[str, Any]) -> float:
        """
        Calculate test coverage risk (0.0-1.0).

        Low score = well tested (low risk)
        High score = untested (high risk)
        """
        payload = task.get("payload", {})

        # Check if tests are mentioned
        has_tests = (
            "test" in str(payload).lower() or
            "pytest" in str(payload).lower() or
            "unittest" in str(payload).lower()
        )

        if has_tests:
            return 0.2  # Has tests

        # Check for validation
        has_validation = (
            "validate" in str(payload).lower() or
            "verify" in str(payload).lower() or
            "check" in str(payload).lower()
        )

        if has_validation:
            return 0.4  # Has validation

        return 0.7  # No tests/validation

    def _calculate_novelty(self, task: Dict[str, Any]) -> float:
        """
        Calculate novelty risk (0.0-1.0).

        Low score = done before (low risk)
        High score = never done (high risk)
        """
        # Create operation signature
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        # Simple signature based on task type + key patterns
        signature = f"{task_type}:{len(str(payload))}"

        # Check history
        if signature in self.operation_history:
            count = self.operation_history[signature]

            if count >= 10:
                return 0.1  # Very familiar
            elif count >= 5:
                return 0.3  # Familiar
            elif count >= 2:
                return 0.5  # Somewhat familiar
            else:
                return 0.7  # Somewhat novel

        return 0.9  # Completely novel

    def _record_operation(self, task: Dict[str, Any]):
        """Record operation in history for future novelty scoring."""
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        signature = f"{task_type}:{len(str(payload))}"

        self.operation_history[signature] = self.operation_history.get(signature, 0) + 1

        # Save periodically
        if len(self.operation_history) % 10 == 0:
            self._save_history()

    def _get_risk_level(self, score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if score < 0.2:
            return RiskLevel.LOW
        elif score < 0.5:
            return RiskLevel.MEDIUM
        elif score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _get_approval_tier(self, score: float) -> ApprovalTier:
        """Convert risk score to approval tier."""
        if score < 0.2:
            return ApprovalTier.AUTOMATIC
        elif score < 0.5:
            return ApprovalTier.NOTIFICATION
        elif score < 0.8:
            return ApprovalTier.APPROVAL
        else:
            return ApprovalTier.COLLABORATIVE

    def _generate_reasoning(
        self,
        task: Dict[str, Any],
        risk_factors: RiskFactors,
        risk_score: float
    ) -> List[str]:
        """Generate human-readable reasoning for risk score."""
        reasoning = []

        # Highlight high-risk factors
        if risk_factors.scope > 0.7:
            reasoning.append(f"Wide scope (affects multiple nodes)")

        if risk_factors.criticality > 0.7:
            reasoning.append(f"Critical operation (can break things)")

        if risk_factors.reversibility > 0.7:
            reasoning.append(f"Hard to reverse (destructive operation)")

        if risk_factors.test_coverage > 0.7:
            reasoning.append(f"Low test coverage (untested code)")

        if risk_factors.novelty > 0.7:
            reasoning.append(f"Novel operation (never done before)")

        # Overall assessment
        if risk_score >= 0.8:
            reasoning.append(f"CRITICAL: Requires collaborative decision")
        elif risk_score >= 0.5:
            reasoning.append(f"HIGH: Requires human approval")
        elif risk_score >= 0.2:
            reasoning.append(f"MEDIUM: Will notify human")
        else:
            reasoning.append(f"LOW: Safe for automatic execution")

        return reasoning


# ============================================================================
# Example Usage
# ============================================================================

def example_risk_assessment():
    """Example: Assess risk of various operations."""
    print("\n" + "=" * 70)
    print("Risk Assessment Examples")
    print("=" * 70)

    engine = RiskScoringEngine()

    # Example 1: Low risk (simple script)
    print("\n1. Low Risk: Simple health check")
    task1 = {
        "task_id": "task-001",
        "type": "code_execution",
        "target_node": "macpro51",
        "payload": {
            "code": "import psutil\nprint(f'CPU: {psutil.cpu_percent()}%')",
            "code_language": "python"
        }
    }

    assessment1 = engine.assess_task_risk(task1)
    print(f"   Score: {assessment1.risk_score:.3f}")
    print(f"   Level: {assessment1.risk_level.value}")
    print(f"   Approval: {assessment1.approval_tier.value}")
    for reason in assessment1.reasoning:
        print(f"   - {reason}")

    # Example 2: Medium risk (deployment)
    print("\n2. Medium Risk: Deployment")
    task2 = {
        "task_id": "task-002",
        "type": "deployment",
        "target_node": "macpro51",
        "payload": {
            "project": "api-server",
            "version": "1.2.3"
        }
    }

    assessment2 = engine.assess_task_risk(task2)
    print(f"   Score: {assessment2.risk_score:.3f}")
    print(f"   Level: {assessment2.risk_level.value}")
    print(f"   Approval: {assessment2.approval_tier.value}")

    # Example 3: Critical risk (destructive operation)
    print("\n3. CRITICAL Risk: Destructive operation")
    task3 = {
        "task_id": "task-003",
        "type": "code_execution",
        "target_node": "*",  # All nodes!
        "payload": {
            "code": "import shutil\nshutil.rmtree('/tmp/data', ignore_errors=False)",
            "code_language": "python"
        }
    }

    assessment3 = engine.assess_task_risk(task3)
    print(f"   Score: {assessment3.risk_score:.3f}")
    print(f"   Level: {assessment3.risk_level.value}")
    print(f"   Approval: {assessment3.approval_tier.value}")
    for reason in assessment3.reasoning:
        print(f"   - {reason}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_risk_assessment()
    print("\nRisk assessment module loaded successfully ✓")
