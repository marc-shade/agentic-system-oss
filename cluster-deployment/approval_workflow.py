#!/usr/bin/env python3
"""
Approval Workflow System for Human-in-the-Loop
==============================================

Manages the complete lifecycle of approval requests for risky operations.

Workflow States:
- Pending: Awaiting human decision
- Approved: Human approved execution
- Rejected: Human rejected execution
- Timeout: No response within deadline
- Auto-approved: Low risk, automatically approved

Approval Channels:
- CLI: Command-line interface approval
- Web: Browser-based approval dashboard
- Arduino: Physical approval controller (macOS only)
- API: External API integration

Features:
- Risk-based automatic approval/rejection
- Timeout handling with configurable deadlines
- Multi-channel approval support
- Approval history and audit trail
- Real-time status updates
- Approval delegation and escalation

Usage:
    workflow = ApprovalWorkflow()

    # Request approval for a task
    request_id = workflow.request_approval(
        task=task_data,
        risk_assessment=assessment,
        requester="github_daemon"
    )

    # Wait for approval (blocks)
    decision = workflow.wait_for_approval(request_id, timeout=300)

    if decision.approved:
        # Execute task
        ...
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from risk_assessment import RiskAssessment, ApprovalTier

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    AUTO_APPROVED = "auto_approved"
    AUTO_REJECTED = "auto_rejected"


class ApprovalChannel(str, Enum):
    """Channel through which approval was requested/granted."""
    CLI = "cli"
    WEB = "web"
    ARDUINO = "arduino"
    API = "api"
    AUTOMATIC = "automatic"


@dataclass
class ApprovalDecision:
    """Human decision on an approval request."""
    request_id: str
    approved: bool
    channel: ApprovalChannel
    approver: str
    reason: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalDecision":
        return cls(**data)


@dataclass
class ApprovalRequest:
    """
    Request for human approval of an operation.

    Tracks complete lifecycle from request to decision.
    """

    request_id: str
    task_id: str
    task_type: str
    task_description: str
    risk_assessment: RiskAssessment
    requester: str

    # Lifecycle
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    deadline: Optional[str] = None

    # Decision
    decision: Optional[ApprovalDecision] = None
    decided_at: Optional[str] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["risk_assessment"] = self.risk_assessment.to_dict()
        if self.decision:
            data["decision"] = self.decision.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        # Parse nested objects
        risk_assessment = RiskAssessment(**data["risk_assessment"])
        decision = ApprovalDecision.from_dict(data["decision"]) if data.get("decision") else None

        return cls(
            request_id=data["request_id"],
            task_id=data["task_id"],
            task_type=data["task_type"],
            task_description=data["task_description"],
            risk_assessment=risk_assessment,
            requester=data["requester"],
            status=ApprovalStatus(data["status"]),
            created_at=data["created_at"],
            deadline=data.get("deadline"),
            decision=decision,
            decided_at=data.get("decided_at"),
            context=data.get("context", {})
        )

    def is_expired(self) -> bool:
        """Check if request has passed its deadline."""
        if not self.deadline:
            return False

        deadline_dt = datetime.fromisoformat(self.deadline)
        return datetime.now() > deadline_dt

    def time_remaining(self) -> Optional[float]:
        """Get seconds remaining until deadline."""
        if not self.deadline:
            return None

        deadline_dt = datetime.fromisoformat(self.deadline)
        remaining = (deadline_dt - datetime.now()).total_seconds()
        return max(0, remaining)


class ApprovalWorkflow:
    """
    Manages approval workflow lifecycle.

    Handles:
    - Automatic approval/rejection based on risk
    - Timeout management
    - Multi-channel approval
    - Approval history
    - Real-time notifications
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        default_timeout: int = 300,  # 5 minutes
        auto_approve_low_risk: bool = True
    ):
        """
        Initialize approval workflow manager.

        Args:
            storage_dir: Directory for approval history
            default_timeout: Default timeout in seconds
            auto_approve_low_risk: Automatically approve low-risk operations
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".cache" / "gitMQ-approvals"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.default_timeout = default_timeout
        self.auto_approve_low_risk = auto_approve_low_risk

        # Active requests
        self.requests: Dict[str, ApprovalRequest] = {}
        self.request_lock = threading.Lock()

        # Callbacks for approval channels
        self.approval_callbacks: Dict[ApprovalChannel, Callable] = {}

        # Event for blocking wait
        self.decision_events: Dict[str, threading.Event] = {}

        # Load history
        self.history_file = self.storage_dir / "approval_history.jsonl"

        logger.info("Approval workflow initialized")

    def request_approval(
        self,
        task: Dict[str, Any],
        risk_assessment: RiskAssessment,
        requester: str = "unknown",
        timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Request approval for a task.

        Args:
            task: Task data
            risk_assessment: Risk assessment for the task
            requester: Who is requesting approval
            timeout: Timeout in seconds (None for default)
            context: Additional context

        Returns:
            request_id for tracking
        """
        request_id = f"approval-{int(time.time() * 1000)}"

        if timeout is None:
            timeout = self.default_timeout

        # Calculate deadline
        deadline = (datetime.now() + timedelta(seconds=timeout)).isoformat()

        # Create approval request
        request = ApprovalRequest(
            request_id=request_id,
            task_id=task.get("task_id", "unknown"),
            task_type=task.get("type", "unknown"),
            task_description=self._describe_task(task),
            risk_assessment=risk_assessment,
            requester=requester,
            deadline=deadline,
            context=context or {}
        )

        # Handle automatic approval/rejection
        if self._should_auto_approve(risk_assessment):
            request.status = ApprovalStatus.AUTO_APPROVED
            request.decision = ApprovalDecision(
                request_id=request_id,
                approved=True,
                channel=ApprovalChannel.AUTOMATIC,
                approver="system",
                reason="Low risk - automatic approval"
            )
            request.decided_at = datetime.now().isoformat()

            logger.info(f"Auto-approved {request_id} (low risk)")
            self._record_decision(request)

            return request_id

        if self._should_auto_reject(risk_assessment):
            request.status = ApprovalStatus.AUTO_REJECTED
            request.decision = ApprovalDecision(
                request_id=request_id,
                approved=False,
                channel=ApprovalChannel.AUTOMATIC,
                approver="system",
                reason="Automatically rejected by policy"
            )
            request.decided_at = datetime.now().isoformat()

            logger.warning(f"Auto-rejected {request_id}")
            self._record_decision(request)

            return request_id

        # Store request
        with self.request_lock:
            self.requests[request_id] = request
            self.decision_events[request_id] = threading.Event()

        # Notify approval channels
        self._notify_channels(request)

        logger.info(f"Approval requested: {request_id}")
        logger.info(f"  Task: {request.task_type}")
        logger.info(f"  Risk: {risk_assessment.risk_level.value}")
        logger.info(f"  Tier: {risk_assessment.approval_tier.value}")
        logger.info(f"  Timeout: {timeout}s")

        return request_id

    def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[float] = None
    ) -> ApprovalDecision:
        """
        Wait for approval decision (blocking).

        Args:
            request_id: Request to wait for
            timeout: Maximum time to wait (seconds)

        Returns:
            ApprovalDecision with approved=True/False
        """
        request = self._get_request(request_id)

        if not request:
            raise ValueError(f"Unknown request: {request_id}")

        # Already decided?
        if request.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED,
                              ApprovalStatus.AUTO_APPROVED, ApprovalStatus.AUTO_REJECTED]:
            return request.decision

        # Wait for decision or timeout
        event = self.decision_events.get(request_id)

        if timeout is None and request.deadline:
            timeout = request.time_remaining()

        if event:
            decision_made = event.wait(timeout=timeout)

            if decision_made:
                # Decision was made
                request = self._get_request(request_id)
                return request.decision

        # Timeout - no decision made
        request.status = ApprovalStatus.TIMEOUT
        request.decision = ApprovalDecision(
            request_id=request_id,
            approved=False,
            channel=ApprovalChannel.AUTOMATIC,
            approver="system",
            reason="Timeout - no response within deadline"
        )
        request.decided_at = datetime.now().isoformat()

        self._record_decision(request)

        logger.warning(f"Approval timeout: {request_id}")

        return request.decision

    def approve(
        self,
        request_id: str,
        approver: str,
        channel: ApprovalChannel,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Approve a request.

        Args:
            request_id: Request to approve
            approver: Who is approving
            channel: Approval channel used
            reason: Optional reason for approval
            metadata: Additional metadata
        """
        self._make_decision(
            request_id=request_id,
            approved=True,
            approver=approver,
            channel=channel,
            reason=reason,
            metadata=metadata
        )

    def reject(
        self,
        request_id: str,
        approver: str,
        channel: ApprovalChannel,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Reject a request.

        Args:
            request_id: Request to reject
            approver: Who is rejecting
            channel: Approval channel used
            reason: Optional reason for rejection
            metadata: Additional metadata
        """
        self._make_decision(
            request_id=request_id,
            approved=False,
            approver=approver,
            channel=channel,
            reason=reason,
            metadata=metadata
        )

    def _make_decision(
        self,
        request_id: str,
        approved: bool,
        approver: str,
        channel: ApprovalChannel,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Internal method to record a decision."""
        request = self._get_request(request_id)

        if not request:
            raise ValueError(f"Unknown request: {request_id}")

        if request.status != ApprovalStatus.PENDING:
            logger.warning(f"Request {request_id} already decided: {request.status}")
            return

        # Create decision
        decision = ApprovalDecision(
            request_id=request_id,
            approved=approved,
            channel=channel,
            approver=approver,
            reason=reason,
            metadata=metadata or {}
        )

        # Update request
        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.decision = decision
        request.decided_at = datetime.now().isoformat()

        # Record decision
        self._record_decision(request)

        # Notify waiters
        event = self.decision_events.get(request_id)
        if event:
            event.set()

        action = "approved" if approved else "rejected"
        logger.info(f"Request {request_id} {action} by {approver} via {channel.value}")

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        with self.request_lock:
            return [
                req for req in self.requests.values()
                if req.status == ApprovalStatus.PENDING and not req.is_expired()
            ]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        return self._get_request(request_id)

    def _get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Internal method to get request (thread-safe)."""
        with self.request_lock:
            return self.requests.get(request_id)

    def register_channel_callback(
        self,
        channel: ApprovalChannel,
        callback: Callable[[ApprovalRequest], None]
    ):
        """
        Register callback for approval channel notifications.

        Callback will be called when approval is requested.

        Args:
            channel: Approval channel
            callback: Callback function (receives ApprovalRequest)
        """
        self.approval_callbacks[channel] = callback
        logger.info(f"Registered callback for {channel.value} channel")

    def _notify_channels(self, request: ApprovalRequest):
        """Notify all registered channels about new approval request."""
        for channel, callback in self.approval_callbacks.items():
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Channel {channel.value} callback failed: {e}")

    def _should_auto_approve(self, risk_assessment: RiskAssessment) -> bool:
        """Check if request should be auto-approved."""
        if not self.auto_approve_low_risk:
            return False

        return risk_assessment.approval_tier == ApprovalTier.AUTOMATIC

    def _should_auto_reject(self, risk_assessment: RiskAssessment) -> bool:
        """Check if request should be auto-rejected."""
        # Currently no auto-rejection policy
        # Could add policies like "reject if criticality > 0.95"
        return False

    def _describe_task(self, task: Dict[str, Any]) -> str:
        """Generate human-readable task description."""
        task_type = task.get("type", "unknown")
        payload = task.get("payload", {})

        if task_type == "code_execution":
            code = payload.get("code", "")
            language = payload.get("code_language", "unknown")

            # Truncate code for description
            code_preview = code[:100] + "..." if len(code) > 100 else code

            return f"Execute {language} code: {code_preview}"

        elif task_type == "build":
            project = payload.get("project", "unknown")
            return f"Build project: {project}"

        elif task_type == "deployment":
            project = payload.get("project", "unknown")
            version = payload.get("version", "unknown")
            return f"Deploy {project} v{version}"

        else:
            return f"{task_type}: {json.dumps(payload)[:100]}"

    def _record_decision(self, request: ApprovalRequest):
        """Record decision to history."""
        try:
            # Append to history file (JSONL format)
            with open(self.history_file, "a") as f:
                f.write(json.dumps(request.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to record decision: {e}")

    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval statistics."""
        with self.request_lock:
            total = len(self.requests)

            stats = {
                "total_requests": total,
                "by_status": {},
                "by_channel": {},
                "by_risk_level": {},
                "average_decision_time": 0
            }

            if total == 0:
                return stats

            # Count by status
            for status in ApprovalStatus:
                count = sum(1 for req in self.requests.values() if req.status == status)
                stats["by_status"][status.value] = count

            # Count by channel
            for channel in ApprovalChannel:
                count = sum(
                    1 for req in self.requests.values()
                    if req.decision and req.decision.channel == channel
                )
                stats["by_channel"][channel.value] = count

            # Count by risk level
            risk_levels = {}
            for req in self.requests.values():
                level = req.risk_assessment.risk_level.value
                risk_levels[level] = risk_levels.get(level, 0) + 1
            stats["by_risk_level"] = risk_levels

            # Average decision time
            decision_times = []
            for req in self.requests.values():
                if req.decided_at:
                    created = datetime.fromisoformat(req.created_at)
                    decided = datetime.fromisoformat(req.decided_at)
                    decision_times.append((decided - created).total_seconds())

            if decision_times:
                stats["average_decision_time"] = sum(decision_times) / len(decision_times)

            return stats


# ============================================================================
# CLI Approval Interface
# ============================================================================

class CLIApprovalInterface:
    """
    Simple CLI interface for approval requests.

    Displays pending requests and accepts approve/reject commands.
    """

    def __init__(self, workflow: ApprovalWorkflow):
        self.workflow = workflow

        # Register CLI callback
        workflow.register_channel_callback(
            ApprovalChannel.CLI,
            self.on_approval_request
        )

    def on_approval_request(self, request: ApprovalRequest):
        """Called when new approval is requested."""
        print("\n" + "=" * 70)
        print("⚠️  APPROVAL REQUIRED")
        print("=" * 70)
        print(f"Request ID: {request.request_id}")
        print(f"Task: {request.task_description}")
        print(f"Risk Level: {request.risk_assessment.risk_level.value.upper()}")
        print(f"Risk Score: {request.risk_assessment.risk_score:.3f}")
        print(f"Approval Tier: {request.risk_assessment.approval_tier.value}")
        print(f"\nRisk Factors:")
        for factor, value in request.risk_assessment.risk_factors.to_dict().items():
            print(f"  - {factor}: {value:.2f}")
        print(f"\nReasoning:")
        for reason in request.risk_assessment.reasoning:
            print(f"  - {reason}")
        print(f"\nTime remaining: {request.time_remaining():.0f}s")
        print("=" * 70)
        print(f"\nTo approve: approve {request.request_id}")
        print(f"To reject:  reject {request.request_id}")
        print()

    def approve_request(self, request_id: str, approver: str = "cli_user"):
        """Approve a request via CLI."""
        self.workflow.approve(
            request_id=request_id,
            approver=approver,
            channel=ApprovalChannel.CLI,
            reason="Approved via CLI"
        )
        print(f"✓ Approved {request_id}")

    def reject_request(self, request_id: str, approver: str = "cli_user"):
        """Reject a request via CLI."""
        self.workflow.reject(
            request_id=request_id,
            approver=approver,
            channel=ApprovalChannel.CLI,
            reason="Rejected via CLI"
        )
        print(f"✗ Rejected {request_id}")

    def show_pending(self):
        """Show all pending approval requests."""
        pending = self.workflow.get_pending_requests()

        if not pending:
            print("No pending approval requests.")
            return

        print(f"\n{len(pending)} pending approval request(s):\n")

        for req in pending:
            print(f"  {req.request_id}")
            print(f"    Task: {req.task_description}")
            print(f"    Risk: {req.risk_assessment.risk_level.value} ({req.risk_assessment.risk_score:.3f})")
            print(f"    Time: {req.time_remaining():.0f}s remaining")
            print()


# ============================================================================
# Example Usage
# ============================================================================

def example_approval_workflow():
    """Example: Request and handle approval."""
    from risk_assessment import RiskScoringEngine

    print("\n" + "=" * 70)
    print("Approval Workflow Example")
    print("=" * 70)

    # Initialize
    workflow = ApprovalWorkflow(
        default_timeout=60,
        auto_approve_low_risk=True
    )

    cli_interface = CLIApprovalInterface(workflow)

    # Create risk engine
    engine = RiskScoringEngine()

    # Example 1: Low risk task (auto-approved)
    print("\n1. Low Risk Task (auto-approved):")
    task1 = {
        "task_id": "task-001",
        "type": "code_execution",
        "target_node": "macpro51",
        "payload": {
            "code": "print('Hello, World!')",
            "code_language": "python"
        }
    }

    assessment1 = engine.assess_task_risk(task1)
    request_id1 = workflow.request_approval(task1, assessment1, requester="example")
    decision1 = workflow.wait_for_approval(request_id1)

    print(f"   Decision: {'✓ APPROVED' if decision1.approved else '✗ REJECTED'}")
    print(f"   Channel: {decision1.channel.value}")
    print(f"   Reason: {decision1.reason}")

    # Example 2: High risk task (requires approval)
    print("\n2. High Risk Task (requires approval):")
    task2 = {
        "task_id": "task-002",
        "type": "code_execution",
        "target_node": "*",  # All nodes!
        "payload": {
            "code": "import os; os.system('rm -rf /tmp/test')",
            "code_language": "python"
        }
    }

    assessment2 = engine.assess_task_risk(task2)
    request_id2 = workflow.request_approval(task2, assessment2, requester="example")

    # In real scenario, human would approve/reject
    # For demo, auto-approve after brief wait
    print("   Waiting for approval...")
    time.sleep(2)

    # Simulate CLI approval
    cli_interface.approve_request(request_id2, approver="demo_user")

    decision2 = workflow.wait_for_approval(request_id2)
    print(f"   Decision: {'✓ APPROVED' if decision2.approved else '✗ REJECTED'}")
    print(f"   Channel: {decision2.channel.value}")
    print(f"   Approver: {decision2.approver}")

    # Show statistics
    print("\n3. Approval Statistics:")
    stats = workflow.get_approval_statistics()
    print(f"   Total requests: {stats['total_requests']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   By channel: {stats['by_channel']}")
    print(f"   Average decision time: {stats['average_decision_time']:.1f}s")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_approval_workflow()
    print("\nApproval workflow module loaded successfully ✓")
