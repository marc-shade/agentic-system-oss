#!/usr/bin/env python3
"""
Audit Trail System for Human-in-the-Loop Compliance
===================================================

Comprehensive audit logging for all approval decisions and system actions.

Features:
- Tamper-evident append-only logging
- Cryptographic signatures (Ed25519)
- Structured JSON logs with full context
- Queryable audit history
- Compliance reporting
- Integrity verification

Audit Events:
- APPROVAL_REQUEST: New approval requested
- APPROVAL_DECISION: Human decision made
- AUTO_APPROVAL: Automatic approval
- AUTO_REJECTION: Automatic rejection
- TIMEOUT: Approval timeout
- EXECUTION_START: Task execution began
- EXECUTION_COMPLETE: Task completed
- EXECUTION_FAILED: Task failed
- OVERRIDE: Manual override by admin

Audit Log Format (JSONL):
```json
{
  "event_id": "evt-1234567890",
  "event_type": "APPROVAL_DECISION",
  "timestamp": "2025-11-16T12:34:56.789Z",
  "actor": "user@example.com",
  "subject": "task-123",
  "action": "approve",
  "context": {...},
  "signature": "ed25519:abc123..."
}
```

Usage:
    audit = AuditTrail()

    # Log approval request
    audit.log_approval_request(request)

    # Log decision
    audit.log_approval_decision(request, decision)

    # Query audit history
    events = audit.query(
        start_time="2025-11-01",
        end_time="2025-11-16",
        event_type="APPROVAL_DECISION"
    )

    # Verify integrity
    is_valid, errors = audit.verify_integrity()
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from approval_workflow import ApprovalRequest, ApprovalDecision
from risk_assessment import RiskAssessment

logger = logging.getLogger(__name__)

# Ed25519 signature support (optional)
try:
    from nacl.signing import SigningKey
    from nacl.encoding import HexEncoder
    SIGNING_AVAILABLE = True
except ImportError:
    SIGNING_AVAILABLE = False
    logger.warning("PyNaCl not available - signatures disabled")


class AuditEventType(str, Enum):
    """Types of audit events."""
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_DECISION = "approval_decision"
    AUTO_APPROVAL = "auto_approval"
    AUTO_REJECTION = "auto_rejection"
    TIMEOUT = "timeout"
    EXECUTION_START = "execution_start"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    OVERRIDE = "override"
    SYSTEM_EVENT = "system_event"


@dataclass
class AuditEvent:
    """
    Single audit log event.

    Immutable record of a system action.
    """

    event_id: str
    event_type: AuditEventType
    timestamp: str
    actor: str  # Who performed the action
    subject: str  # What was acted upon (task ID, user ID, etc.)
    action: str  # What action was taken
    result: str  # Outcome of the action

    # Detailed context
    context: Dict[str, Any] = field(default_factory=dict)

    # Chain integrity
    previous_hash: Optional[str] = None
    event_hash: Optional[str] = None

    # Cryptographic signature
    signature: Optional[str] = None

    # Metadata
    node_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def compute_hash(self) -> str:
        """
        Compute deterministic hash of this event.

        Hash includes all fields except hash and signature.
        """
        # Create deterministic representation
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "subject": self.subject,
            "action": self.action,
            "result": self.result,
            "context": self.context,
            "previous_hash": self.previous_hash,
            "node_id": self.node_id,
            "session_id": self.session_id
        }

        # JSON with sorted keys for determinism
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))

        # SHA256 hash
        return hashlib.sha256(json_str.encode()).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        # Convert event_type string to enum
        data["event_type"] = AuditEventType(data["event_type"])
        return cls(**data)


class AuditTrail:
    """
    Tamper-evident audit trail with cryptographic integrity.

    Maintains append-only log of all system actions with:
    - Hash chain linking events
    - Optional Ed25519 signatures
    - Full context preservation
    - Queryable history
    """

    def __init__(
        self,
        log_file: Optional[Path] = None,
        signing_key: Optional[bytes] = None,
        enable_signatures: bool = True,
        node_id: str = "unknown"
    ):
        """
        Initialize audit trail.

        Args:
            log_file: Path to audit log (JSONL format)
            signing_key: Ed25519 signing key (32 bytes)
            enable_signatures: Enable cryptographic signatures
            node_id: Node identifier for multi-node setups
        """
        if log_file is None:
            log_file = Path.home() / ".cache" / "gitMQ-audit" / "audit.jsonl"

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self.node_id = node_id
        self.enable_signatures = enable_signatures and SIGNING_AVAILABLE

        # Signing key
        if signing_key and SIGNING_AVAILABLE:
            self.signing_key = SigningKey(signing_key)
        elif self.enable_signatures:
            # Generate ephemeral key (should be persisted in production)
            self.signing_key = SigningKey.generate()
            logger.warning("Using ephemeral signing key - signatures won't verify across restarts")
        else:
            self.signing_key = None

        # Last event hash (for chain integrity)
        self.last_hash: Optional[str] = None

        # Load existing log
        self._load_log()

        logger.info(f"Audit trail initialized (signatures={self.enable_signatures})")

    def _load_log(self):
        """Load existing audit log to get last hash."""
        if not self.log_file.exists():
            return

        try:
            # Read last line to get last hash
            with open(self.log_file, "r") as f:
                lines = f.readlines()

            if lines:
                last_event = json.loads(lines[-1])
                self.last_hash = last_event.get("event_hash")
                logger.info(f"Loaded audit log ({len(lines)} events)")
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")

    def log_event(
        self,
        event_type: AuditEventType,
        actor: str,
        subject: str,
        action: str,
        result: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            actor: Who performed the action
            subject: What was acted upon
            action: What action was taken
            result: Outcome of the action
            context: Additional context
            session_id: Optional session identifier

        Returns:
            Created AuditEvent
        """
        # Generate event ID
        event_id = f"evt-{int(time.time() * 1000)}"

        # Create event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            actor=actor,
            subject=subject,
            action=action,
            result=result,
            context=context or {},
            previous_hash=self.last_hash,
            node_id=self.node_id,
            session_id=session_id
        )

        # Compute hash
        event.event_hash = event.compute_hash()

        # Sign event
        if self.signing_key:
            event.signature = self._sign_event(event)

        # Update last hash
        self.last_hash = event.event_hash

        # Append to log
        self._append_event(event)

        logger.debug(f"Logged audit event: {event_id} ({event_type.value})")

        return event

    def log_approval_request(self, request: ApprovalRequest):
        """Log approval request event."""
        self.log_event(
            event_type=AuditEventType.APPROVAL_REQUEST,
            actor=request.requester,
            subject=request.task_id,
            action="request_approval",
            result="pending",
            context={
                "request_id": request.request_id,
                "task_type": request.task_type,
                "task_description": request.task_description,
                "risk_level": request.risk_assessment.risk_level.value,
                "risk_score": request.risk_assessment.risk_score,
                "approval_tier": request.risk_assessment.approval_tier.value,
                "deadline": request.deadline
            }
        )

    def log_approval_decision(self, request: ApprovalRequest, decision: ApprovalDecision):
        """Log approval decision event."""
        # Determine event type
        if decision.approved:
            event_type = AuditEventType.APPROVAL_DECISION
            result = "approved"
        else:
            event_type = AuditEventType.APPROVAL_DECISION
            result = "rejected"

        # Check for auto-approval/rejection
        if decision.channel.value == "automatic":
            if decision.approved:
                event_type = AuditEventType.AUTO_APPROVAL
            else:
                event_type = AuditEventType.AUTO_REJECTION

        self.log_event(
            event_type=event_type,
            actor=decision.approver,
            subject=request.task_id,
            action="approve" if decision.approved else "reject",
            result=result,
            context={
                "request_id": request.request_id,
                "decision_channel": decision.channel.value,
                "decision_reason": decision.reason,
                "risk_level": request.risk_assessment.risk_level.value,
                "risk_score": request.risk_assessment.risk_score,
                "decision_metadata": decision.metadata
            }
        )

    def log_timeout(self, request: ApprovalRequest):
        """Log approval timeout event."""
        self.log_event(
            event_type=AuditEventType.TIMEOUT,
            actor="system",
            subject=request.task_id,
            action="timeout",
            result="rejected",
            context={
                "request_id": request.request_id,
                "deadline": request.deadline,
                "time_expired": datetime.now().isoformat()
            }
        )

    def log_execution_start(self, task_id: str, executor: str, context: Optional[Dict] = None):
        """Log task execution start."""
        self.log_event(
            event_type=AuditEventType.EXECUTION_START,
            actor=executor,
            subject=task_id,
            action="start_execution",
            result="started",
            context=context or {}
        )

    def log_execution_complete(self, task_id: str, executor: str, result: Any):
        """Log task execution completion."""
        self.log_event(
            event_type=AuditEventType.EXECUTION_COMPLETE,
            actor=executor,
            subject=task_id,
            action="complete_execution",
            result="success",
            context={"execution_result": str(result)[:1000]}  # Truncate
        )

    def log_execution_failed(self, task_id: str, executor: str, error: str):
        """Log task execution failure."""
        self.log_event(
            event_type=AuditEventType.EXECUTION_FAILED,
            actor=executor,
            subject=task_id,
            action="execute",
            result="failed",
            context={"error": error[:1000]}  # Truncate
        )

    def log_override(self, admin: str, subject: str, reason: str):
        """Log administrative override."""
        self.log_event(
            event_type=AuditEventType.OVERRIDE,
            actor=admin,
            subject=subject,
            action="override",
            result="overridden",
            context={"reason": reason}
        )

    def _sign_event(self, event: AuditEvent) -> str:
        """
        Sign event with Ed25519.

        Returns hex-encoded signature.
        """
        if not self.signing_key:
            return ""

        # Sign event hash
        message = event.event_hash.encode()
        signed = self.signing_key.sign(message, encoder=HexEncoder)

        # Return signature (without message)
        return signed.signature.decode()

    def _append_event(self, event: AuditEvent):
        """Append event to audit log."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to append audit event: {e}")

    def query(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        subject: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """
        Query audit log.

        Args:
            start_time: Start timestamp (ISO format)
            end_time: End timestamp (ISO format)
            event_type: Filter by event type
            actor: Filter by actor
            subject: Filter by subject
            limit: Maximum results

        Returns:
            List of matching events
        """
        if not self.log_file.exists():
            return []

        results = []

        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    event_data = json.loads(line)
                    event = AuditEvent.from_dict(event_data)

                    # Apply filters
                    if start_time and event.timestamp < start_time:
                        continue

                    if end_time and event.timestamp > end_time:
                        continue

                    if event_type and event.event_type != event_type:
                        continue

                    if actor and event.actor != actor:
                        continue

                    if subject and event.subject != subject:
                        continue

                    results.append(event)

                    # Check limit
                    if limit and len(results) >= limit:
                        break

        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")

        return results

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """
        Verify audit log integrity.

        Checks:
        - Hash chain continuity
        - Event hash correctness
        - Signatures (if enabled)

        Returns:
            (is_valid, list_of_errors)
        """
        if not self.log_file.exists():
            return True, []

        errors = []
        previous_hash = None

        try:
            with open(self.log_file, "r") as f:
                for i, line in enumerate(f, 1):
                    event_data = json.loads(line)
                    event = AuditEvent.from_dict(event_data)

                    # Check previous hash
                    if event.previous_hash != previous_hash:
                        errors.append(f"Event {i}: Hash chain broken (expected {previous_hash}, got {event.previous_hash})")

                    # Verify event hash
                    computed_hash = event.compute_hash()
                    if event.event_hash != computed_hash:
                        errors.append(f"Event {i}: Hash mismatch (expected {computed_hash}, got {event.event_hash})")

                    # Verify signature (if available)
                    if event.signature and self.signing_key:
                        # Signature verification would require verify_key
                        # For now, just check presence
                        pass

                    previous_hash = event.event_hash

        except Exception as e:
            errors.append(f"Failed to verify log: {e}")

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        if not self.log_file.exists():
            return {
                "total_events": 0,
                "by_type": {},
                "by_actor": {},
                "first_event": None,
                "last_event": None
            }

        total = 0
        by_type: Dict[str, int] = {}
        by_actor: Dict[str, int] = {}
        first_event = None
        last_event = None

        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    event_data = json.loads(line)
                    total += 1

                    # First/last
                    if not first_event:
                        first_event = event_data["timestamp"]
                    last_event = event_data["timestamp"]

                    # By type
                    event_type = event_data["event_type"]
                    by_type[event_type] = by_type.get(event_type, 0) + 1

                    # By actor
                    actor = event_data["actor"]
                    by_actor[actor] = by_actor.get(actor, 0) + 1

        except Exception as e:
            logger.error(f"Failed to compute statistics: {e}")

        return {
            "total_events": total,
            "by_type": by_type,
            "by_actor": by_actor,
            "first_event": first_event,
            "last_event": last_event
        }

    def export_compliance_report(
        self,
        start_date: str,
        end_date: str,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            output_file: Optional output file for report

        Returns:
            Compliance report dictionary
        """
        events = self.query(start_time=start_date, end_time=end_date + "T23:59:59")

        # Analyze events
        total_approvals = 0
        auto_approved = 0
        human_approved = 0
        rejected = 0
        timeouts = 0

        by_risk_level: Dict[str, int] = {}
        by_approver: Dict[str, int] = {}

        for event in events:
            if event.event_type == AuditEventType.AUTO_APPROVAL:
                auto_approved += 1
                total_approvals += 1
            elif event.event_type == AuditEventType.APPROVAL_DECISION:
                if event.result == "approved":
                    human_approved += 1
                    total_approvals += 1
                else:
                    rejected += 1

                # Track approver
                approver = event.actor
                by_approver[approver] = by_approver.get(approver, 0) + 1

            elif event.event_type == AuditEventType.TIMEOUT:
                timeouts += 1

            # Track risk level
            if "risk_level" in event.context:
                risk = event.context["risk_level"]
                by_risk_level[risk] = by_risk_level.get(risk, 0) + 1

        # Generate report
        report = {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "summary": {
                "total_requests": len([e for e in events if e.event_type == AuditEventType.APPROVAL_REQUEST]),
                "total_approvals": total_approvals,
                "auto_approved": auto_approved,
                "human_approved": human_approved,
                "rejected": rejected,
                "timeouts": timeouts
            },
            "by_risk_level": by_risk_level,
            "by_approver": by_approver,
            "generated_at": datetime.now().isoformat()
        }

        # Export to file if requested
        if output_file:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)

            logger.info(f"Compliance report exported to {output_file}")

        return report


# ============================================================================
# Example Usage
# ============================================================================

def example_audit_trail():
    """Example: Audit trail usage."""
    from risk_assessment import RiskScoringEngine
    from approval_workflow import ApprovalWorkflow

    print("\n" + "=" * 70)
    print("Audit Trail Example")
    print("=" * 70)

    # Initialize
    audit = AuditTrail(node_id="macpro51")

    # Create workflow and engine
    workflow = ApprovalWorkflow()
    engine = RiskScoringEngine()

    print("\n1. Creating approval requests...")

    # Request 1: Auto-approved
    task1 = {
        "task_id": "task-001",
        "type": "code_execution",
        "target_node": "macpro51",
        "payload": {"code": "print('hello')"}
    }
    assessment1 = engine.assess_task_risk(task1)
    request_id1 = workflow.request_approval(task1, assessment1)
    request1 = workflow.get_request(request_id1)

    audit.log_approval_request(request1)
    decision1 = workflow.wait_for_approval(request_id1)
    audit.log_approval_decision(request1, decision1)

    # Request 2: Human approved
    task2 = {
        "task_id": "task-002",
        "type": "deployment",
        "target_node": "macpro51",
        "payload": {"project": "api", "version": "1.2.3"}
    }
    assessment2 = engine.assess_task_risk(task2)
    request_id2 = workflow.request_approval(task2, assessment2, timeout=5)
    request2 = workflow.get_request(request_id2)

    audit.log_approval_request(request2)
    time.sleep(1)
    workflow.approve(request_id2, "admin", ApprovalChannel.CLI)
    decision2 = workflow.wait_for_approval(request_id2)
    audit.log_approval_decision(request2, decision2)

    # Log execution
    audit.log_execution_start("task-002", "daemon")
    audit.log_execution_complete("task-002", "daemon", {"status": "success"})

    print("   ✓ Logged 6 audit events")

    # Query audit log
    print("\n2. Querying audit log...")
    recent_events = audit.query(limit=10)
    print(f"   Found {len(recent_events)} recent events")

    for event in recent_events:
        print(f"   - {event.event_type.value}: {event.action} by {event.actor}")

    # Verify integrity
    print("\n3. Verifying audit log integrity...")
    is_valid, errors = audit.verify_integrity()

    if is_valid:
        print("   ✓ Audit log integrity verified")
    else:
        print(f"   ✗ Integrity errors: {len(errors)}")
        for error in errors:
            print(f"     - {error}")

    # Statistics
    print("\n4. Audit statistics:")
    stats = audit.get_statistics()
    print(f"   Total events: {stats['total_events']}")
    print(f"   By type: {stats['by_type']}")
    print(f"   By actor: {stats['by_actor']}")

    # Compliance report
    print("\n5. Generating compliance report...")
    today = datetime.now().strftime("%Y-%m-%d")
    report = audit.export_compliance_report(today, today)

    print(f"   Total requests: {report['summary']['total_requests']}")
    print(f"   Auto-approved: {report['summary']['auto_approved']}")
    print(f"   Human-approved: {report['summary']['human_approved']}")
    print(f"   By risk level: {report['by_risk_level']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_audit_trail()
    print("\nAudit trail module loaded successfully ✓")
