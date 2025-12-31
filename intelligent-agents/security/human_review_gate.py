"""
Human Review Gate

Flags sensitive operations for human review.
Following Kai pattern: Human-in-the-loop for critical decisions.

Review triggers:
1. High-risk operations (delete, system modify, deploy)
2. Sensitive data access (credentials, PII, financial)
3. Unusual patterns (high frequency, unexpected scope)
4. Confidence thresholds (agent uncertainty)
5. Policy violations (potential but uncertain)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json


class ReviewPriority(Enum):
    """Priority levels for review requests."""
    LOW = "low"           # Can wait, informational
    MEDIUM = "medium"     # Should review soon
    HIGH = "high"         # Needs prompt attention
    CRITICAL = "critical" # Immediate review required
    BLOCKING = "blocking" # Cannot proceed without approval


class ReviewCategory(Enum):
    """Categories of operations requiring review."""
    DATA_DELETION = "data_deletion"
    SYSTEM_MODIFICATION = "system_modification"
    CREDENTIAL_ACCESS = "credential_access"
    EXTERNAL_COMMUNICATION = "external_communication"
    FINANCIAL_OPERATION = "financial_operation"
    PII_ACCESS = "pii_access"
    SECURITY_CHANGE = "security_change"
    DEPLOYMENT = "deployment"
    PERMISSION_GRANT = "permission_grant"
    UNUSUAL_PATTERN = "unusual_pattern"
    LOW_CONFIDENCE = "low_confidence"
    POLICY_EDGE_CASE = "policy_edge_case"


class ReviewStatus(Enum):
    """Status of a review request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    ESCALATED = "escalated"


@dataclass
class ReviewTrigger:
    """Definition of what triggers a review."""
    category: ReviewCategory
    patterns: List[str]  # Patterns that trigger this review
    priority: ReviewPriority
    description: str
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)
    expiry_hours: int = 24
    escalation_hours: int = 4


@dataclass
class ReviewRequest:
    """A request for human review."""
    id: str
    category: ReviewCategory
    priority: ReviewPriority
    operation: str
    description: str
    context: Dict[str, Any]
    requester_id: str
    created_at: datetime
    expires_at: datetime
    status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: str = ""
    escalated: bool = False


@dataclass
class ReviewDecision:
    """Result of review gate check."""
    requires_review: bool
    request_id: Optional[str] = None
    priority: ReviewPriority = ReviewPriority.LOW
    category: Optional[ReviewCategory] = None
    reason: str = ""
    can_proceed: bool = True  # False if blocking review required
    existing_approval: Optional[ReviewRequest] = None


class HumanReviewGate:
    """Gates operations that require human review."""

    # Default review triggers
    DEFAULT_TRIGGERS: Dict[ReviewCategory, ReviewTrigger] = {
        ReviewCategory.DATA_DELETION: ReviewTrigger(
            category=ReviewCategory.DATA_DELETION,
            patterns=[
                r"delete.*database",
                r"drop\s+table",
                r"rm\s+-rf",
                r"remove.*all",
                r"purge",
                r"truncate",
            ],
            priority=ReviewPriority.HIGH,
            description="Data deletion operations require approval",
        ),
        ReviewCategory.SYSTEM_MODIFICATION: ReviewTrigger(
            category=ReviewCategory.SYSTEM_MODIFICATION,
            patterns=[
                r"modify.*system",
                r"change.*config",
                r"update.*settings",
                r"alter.*service",
                r"restart",
                r"shutdown",
            ],
            priority=ReviewPriority.HIGH,
            description="System modifications require approval",
        ),
        ReviewCategory.CREDENTIAL_ACCESS: ReviewTrigger(
            category=ReviewCategory.CREDENTIAL_ACCESS,
            patterns=[
                r"api[_\s-]?key",
                r"secret",
                r"password",
                r"token",
                r"credential",
                r"\.env",
                r"\.pem",
            ],
            priority=ReviewPriority.CRITICAL,
            description="Credential access requires approval",
        ),
        ReviewCategory.EXTERNAL_COMMUNICATION: ReviewTrigger(
            category=ReviewCategory.EXTERNAL_COMMUNICATION,
            patterns=[
                r"send.*email",
                r"post.*slack",
                r"notify.*external",
                r"webhook",
                r"api.*call.*external",
            ],
            priority=ReviewPriority.MEDIUM,
            description="External communications require approval",
            auto_approve_conditions={"trusted_recipients": True},
        ),
        ReviewCategory.DEPLOYMENT: ReviewTrigger(
            category=ReviewCategory.DEPLOYMENT,
            patterns=[
                r"deploy",
                r"release",
                r"publish",
                r"push.*production",
                r"promote",
            ],
            priority=ReviewPriority.BLOCKING,
            description="Deployments require explicit approval",
            expiry_hours=1,
        ),
        ReviewCategory.PERMISSION_GRANT: ReviewTrigger(
            category=ReviewCategory.PERMISSION_GRANT,
            patterns=[
                r"grant.*permission",
                r"add.*role",
                r"elevate.*access",
                r"sudo",
                r"admin.*access",
            ],
            priority=ReviewPriority.CRITICAL,
            description="Permission changes require approval",
        ),
        ReviewCategory.FINANCIAL_OPERATION: ReviewTrigger(
            category=ReviewCategory.FINANCIAL_OPERATION,
            patterns=[
                r"payment",
                r"billing",
                r"invoice",
                r"charge",
                r"refund",
                r"transaction",
            ],
            priority=ReviewPriority.BLOCKING,
            description="Financial operations require approval",
        ),
        ReviewCategory.PII_ACCESS: ReviewTrigger(
            category=ReviewCategory.PII_ACCESS,
            patterns=[
                r"personal.*data",
                r"user.*info",
                r"ssn",
                r"social.*security",
                r"address",
                r"phone.*number",
                r"email.*list",
            ],
            priority=ReviewPriority.HIGH,
            description="PII access requires approval",
        ),
    }

    def __init__(
        self,
        triggers: Optional[Dict[ReviewCategory, ReviewTrigger]] = None,
        approval_callback: Optional[Callable[[ReviewRequest], bool]] = None,
        auto_approve_low_priority: bool = False,
        review_storage: Optional[Dict[str, ReviewRequest]] = None
    ):
        """Initialize review gate.

        Args:
            triggers: Custom review triggers (merged with defaults)
            approval_callback: Optional callback for real-time approval
            auto_approve_low_priority: Auto-approve LOW priority items
            review_storage: Storage for review requests
        """
        self.triggers = dict(self.DEFAULT_TRIGGERS)
        if triggers:
            self.triggers.update(triggers)

        self.approval_callback = approval_callback
        self.auto_approve_low_priority = auto_approve_low_priority
        self.pending_reviews: Dict[str, ReviewRequest] = review_storage or {}
        self.approved_patterns: Set[str] = set()  # Cached approvals

        # Compile patterns
        import re
        self.compiled_triggers: Dict[ReviewCategory, List[Any]] = {}
        for category, trigger in self.triggers.items():
            self.compiled_triggers[category] = [
                re.compile(p, re.IGNORECASE) for p in trigger.patterns
            ]

    def check(
        self,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        requester_id: str = "unknown",
        confidence: float = 1.0
    ) -> ReviewDecision:
        """Check if operation requires human review.

        Args:
            operation: Operation being attempted
            context: Additional context
            requester_id: Who is requesting
            confidence: Agent's confidence (0-1)

        Returns:
            ReviewDecision indicating if review is needed
        """
        context = context or {}

        # Check for low confidence
        if confidence < 0.6:
            return self._create_review(
                operation=operation,
                category=ReviewCategory.LOW_CONFIDENCE,
                priority=ReviewPriority.HIGH,
                context={**context, "confidence": confidence},
                requester_id=requester_id,
                reason=f"Low agent confidence: {confidence:.0%}",
            )

        # Check each trigger category
        for category, patterns in self.compiled_triggers.items():
            for pattern in patterns:
                if pattern.search(operation):
                    trigger = self.triggers[category]

                    # Check for existing approval
                    approval_key = self._get_approval_key(category, operation)
                    if approval_key in self.approved_patterns:
                        return ReviewDecision(
                            requires_review=False,
                            reason="Previously approved pattern",
                            can_proceed=True,
                        )

                    # Check auto-approve conditions
                    if self._check_auto_approve(trigger, context):
                        return ReviewDecision(
                            requires_review=False,
                            reason="Auto-approved based on conditions",
                            can_proceed=True,
                        )

                    # Check pending reviews for same operation
                    existing = self._find_existing_review(category, operation)
                    if existing:
                        if existing.status == ReviewStatus.APPROVED:
                            return ReviewDecision(
                                requires_review=False,
                                existing_approval=existing,
                                can_proceed=True,
                            )
                        elif existing.status == ReviewStatus.PENDING:
                            return ReviewDecision(
                                requires_review=True,
                                request_id=existing.id,
                                priority=trigger.priority,
                                category=category,
                                reason="Review already pending",
                                can_proceed=trigger.priority != ReviewPriority.BLOCKING,
                            )

                    # Create new review request
                    return self._create_review(
                        operation=operation,
                        category=category,
                        priority=trigger.priority,
                        context=context,
                        requester_id=requester_id,
                        reason=trigger.description,
                    )

        # No triggers matched
        return ReviewDecision(
            requires_review=False,
            reason="No review triggers matched",
            can_proceed=True,
        )

    def _create_review(
        self,
        operation: str,
        category: ReviewCategory,
        priority: ReviewPriority,
        context: Dict[str, Any],
        requester_id: str,
        reason: str
    ) -> ReviewDecision:
        """Create a review request."""
        trigger = self.triggers.get(category)
        expiry_hours = trigger.expiry_hours if trigger else 24

        # Generate unique ID
        review_id = hashlib.sha256(
            f"{operation}:{category.value}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        now = datetime.now()
        request = ReviewRequest(
            id=review_id,
            category=category,
            priority=priority,
            operation=operation,
            description=reason,
            context=context,
            requester_id=requester_id,
            created_at=now,
            expires_at=now + timedelta(hours=expiry_hours),
        )

        # Store request
        self.pending_reviews[review_id] = request

        # Check for auto-approve
        if self.auto_approve_low_priority and priority == ReviewPriority.LOW:
            self._approve_request(review_id, "system", "Auto-approved low priority")
            return ReviewDecision(
                requires_review=False,
                request_id=review_id,
                reason="Auto-approved (low priority)",
                can_proceed=True,
            )

        # Try approval callback
        if self.approval_callback:
            try:
                if self.approval_callback(request):
                    self._approve_request(review_id, "callback", "Approved by callback")
                    return ReviewDecision(
                        requires_review=False,
                        request_id=review_id,
                        reason="Approved by callback",
                        can_proceed=True,
                    )
            except Exception:
                pass  # Callback failed, require manual review

        return ReviewDecision(
            requires_review=True,
            request_id=review_id,
            priority=priority,
            category=category,
            reason=reason,
            can_proceed=priority != ReviewPriority.BLOCKING,
        )

    def _check_auto_approve(
        self,
        trigger: ReviewTrigger,
        context: Dict[str, Any]
    ) -> bool:
        """Check if auto-approve conditions are met."""
        if not trigger.auto_approve_conditions:
            return False

        for condition, expected in trigger.auto_approve_conditions.items():
            if context.get(condition) != expected:
                return False

        return True

    def _find_existing_review(
        self,
        category: ReviewCategory,
        operation: str
    ) -> Optional[ReviewRequest]:
        """Find existing review for same operation."""
        now = datetime.now()

        for request in self.pending_reviews.values():
            if request.category == category and request.operation == operation:
                # Check expiry
                if request.expires_at < now:
                    request.status = ReviewStatus.EXPIRED
                    continue

                return request

        return None

    def _get_approval_key(self, category: ReviewCategory, operation: str) -> str:
        """Generate key for caching approvals."""
        # Normalize operation for caching
        normalized = operation.lower().strip()
        return f"{category.value}:{hashlib.sha256(normalized.encode()).hexdigest()[:8]}"

    def approve(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str = ""
    ) -> bool:
        """Approve a review request.

        Args:
            request_id: The request to approve
            reviewer_id: Who is approving
            notes: Optional review notes

        Returns:
            True if approved successfully
        """
        return self._approve_request(request_id, reviewer_id, notes)

    def _approve_request(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str
    ) -> bool:
        """Internal approval method."""
        if request_id not in self.pending_reviews:
            return False

        request = self.pending_reviews[request_id]

        if request.status != ReviewStatus.PENDING:
            return False

        request.status = ReviewStatus.APPROVED
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.now()
        request.review_notes = notes

        # Cache approval
        approval_key = self._get_approval_key(request.category, request.operation)
        self.approved_patterns.add(approval_key)

        return True

    def deny(
        self,
        request_id: str,
        reviewer_id: str,
        notes: str = ""
    ) -> bool:
        """Deny a review request."""
        if request_id not in self.pending_reviews:
            return False

        request = self.pending_reviews[request_id]

        if request.status != ReviewStatus.PENDING:
            return False

        request.status = ReviewStatus.DENIED
        request.reviewed_by = reviewer_id
        request.reviewed_at = datetime.now()
        request.review_notes = notes

        return True

    def escalate(self, request_id: str) -> bool:
        """Escalate a review request."""
        if request_id not in self.pending_reviews:
            return False

        request = self.pending_reviews[request_id]
        request.escalated = True
        request.status = ReviewStatus.ESCALATED

        # Increase priority
        priority_order = [
            ReviewPriority.LOW,
            ReviewPriority.MEDIUM,
            ReviewPriority.HIGH,
            ReviewPriority.CRITICAL,
            ReviewPriority.BLOCKING,
        ]
        current_idx = priority_order.index(request.priority)
        if current_idx < len(priority_order) - 1:
            request.priority = priority_order[current_idx + 1]

        return True

    def get_pending_reviews(
        self,
        priority: Optional[ReviewPriority] = None,
        category: Optional[ReviewCategory] = None
    ) -> List[ReviewRequest]:
        """Get pending review requests."""
        now = datetime.now()
        results = []

        for request in self.pending_reviews.values():
            # Update expired status
            if request.expires_at < now and request.status == ReviewStatus.PENDING:
                request.status = ReviewStatus.EXPIRED

            # Filter by status
            if request.status not in (ReviewStatus.PENDING, ReviewStatus.ESCALATED):
                continue

            # Filter by priority
            if priority and request.priority != priority:
                continue

            # Filter by category
            if category and request.category != category:
                continue

            results.append(request)

        # Sort by priority (highest first) then by creation time
        priority_order = {
            ReviewPriority.BLOCKING: 0,
            ReviewPriority.CRITICAL: 1,
            ReviewPriority.HIGH: 2,
            ReviewPriority.MEDIUM: 3,
            ReviewPriority.LOW: 4,
        }
        results.sort(key=lambda r: (priority_order[r.priority], r.created_at))

        return results

    def get_review_summary(self) -> str:
        """Get summary of pending reviews."""
        pending = self.get_pending_reviews()

        if not pending:
            return "No pending reviews"

        lines = [f"Pending Reviews: {len(pending)}"]

        # Group by priority
        by_priority: Dict[ReviewPriority, List[ReviewRequest]] = {}
        for r in pending:
            if r.priority not in by_priority:
                by_priority[r.priority] = []
            by_priority[r.priority].append(r)

        priority_order = [
            ReviewPriority.BLOCKING,
            ReviewPriority.CRITICAL,
            ReviewPriority.HIGH,
            ReviewPriority.MEDIUM,
            ReviewPriority.LOW,
        ]

        for priority in priority_order:
            if priority in by_priority:
                lines.append(f"\n{priority.value.upper()}:")
                for r in by_priority[priority]:
                    escalated = " [ESCALATED]" if r.escalated else ""
                    lines.append(f"  [{r.id}] {r.category.value}: {r.operation[:50]}...{escalated}")

        return "\n".join(lines)


if __name__ == '__main__':
    # Self-test
    print("Human Review Gate Self-Test")
    print("=" * 50)

    gate = HumanReviewGate(auto_approve_low_priority=True)

    test_cases = [
        # Should trigger review
        ("delete all user database records", True, ReviewCategory.DATA_DELETION),
        ("rm -rf /tmp/cache", True, ReviewCategory.DATA_DELETION),
        ("modify system configuration", True, ReviewCategory.SYSTEM_MODIFICATION),
        ("get api_key from vault", True, ReviewCategory.CREDENTIAL_ACCESS),
        ("deploy to production", True, ReviewCategory.DEPLOYMENT),
        ("send email to customers", True, ReviewCategory.EXTERNAL_COMMUNICATION),

        # Should not trigger review
        ("read file.txt", False, None),
        ("search for pattern", False, None),
        ("list directory contents", False, None),
    ]

    passed = 0
    failed = 0

    for operation, should_require, expected_category in test_cases:
        result = gate.check(operation, requester_id="test_agent")

        category_match = expected_category is None or result.category == expected_category
        requires_match = result.requires_review == should_require

        if requires_match and category_match:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"

        print(f"{status}: '{operation[:40]}...'")
        print(f"       Expected: requires_review={should_require}, category={expected_category}")
        print(f"       Got: requires_review={result.requires_review}, category={result.category}")

    # Test approval flow
    print("\nTesting approval flow:")
    result = gate.check("deploy to staging", requester_id="agent1")
    assert result.requires_review, "Deploy should require review"
    print(f"Created review: {result.request_id}")

    # Approve it
    approved = gate.approve(result.request_id, "admin1", "Approved for staging")
    assert approved, "Should be able to approve"
    print(f"Approved: {approved}")

    # Check again - should find approval
    result2 = gate.check("deploy to staging", requester_id="agent1")
    print(f"After approval, requires_review={result2.requires_review}")

    # Test low confidence
    result3 = gate.check("simple read operation", requester_id="agent1", confidence=0.3)
    print(f"Low confidence check: requires_review={result3.requires_review}, category={result3.category}")

    print()
    print("Review Summary:")
    print(gate.get_review_summary())

    print()
    print(f"Results: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} tests failed"
    print('All HumanReviewGate tests passed!')
