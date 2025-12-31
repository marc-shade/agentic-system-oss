"""
Purpose Validator

Validates if requests align with the agent's defined purpose.
Following Kai pattern: Clear purpose → Clear boundaries.

Each agent should have a defined purpose with:
1. Primary objectives - What the agent is designed to do
2. Allowed domains - Topics/areas the agent can work in
3. Forbidden actions - Things the agent should never do
4. Scope limits - Boundaries of operation
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum


class ValidationResult(Enum):
    """Result of purpose validation."""
    ALLOWED = "allowed"
    NEEDS_REVIEW = "needs_review"
    DENIED = "denied"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class AgentPurpose:
    """Defines an agent's purpose and boundaries."""
    name: str
    description: str
    primary_objectives: List[str]
    allowed_domains: List[str]
    forbidden_actions: List[str]
    scope_keywords: List[str]  # Keywords that indicate in-scope work
    out_of_scope_keywords: List[str]  # Keywords that indicate out-of-scope
    risk_tolerance: str = "medium"  # low, medium, high
    requires_confirmation: List[str] = field(default_factory=list)


@dataclass
class PurposeValidation:
    """Result of purpose validation."""
    result: ValidationResult
    confidence: float
    matched_objectives: List[str]
    matched_domains: List[str]
    violation_reasons: List[str]
    suggestions: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


class PurposeValidator:
    """Validates requests against agent purpose."""

    # Common purpose templates
    PURPOSE_TEMPLATES = {
        "code_assistant": AgentPurpose(
            name="Code Assistant",
            description="Assists with code development, debugging, and documentation",
            primary_objectives=[
                "Write clean, maintainable code",
                "Debug and fix issues",
                "Explain code concepts",
                "Review and improve code quality",
            ],
            allowed_domains=[
                "programming", "software development", "debugging",
                "code review", "documentation", "testing", "devops",
                "databases", "apis", "algorithms", "data structures",
            ],
            forbidden_actions=[
                "Execute malicious code",
                "Access unauthorized systems",
                "Expose credentials or secrets",
                "Bypass security measures",
                "Create harmful software",
            ],
            scope_keywords=[
                "code", "function", "class", "bug", "error", "implement",
                "debug", "test", "refactor", "optimize", "api", "database",
                "script", "program", "module", "library", "framework",
            ],
            out_of_scope_keywords=[
                "hack", "exploit", "malware", "virus", "ddos", "crack",
                "bypass security", "steal data", "unauthorized access",
            ],
            requires_confirmation=["delete files", "modify system", "execute commands"],
        ),
        "research_assistant": AgentPurpose(
            name="Research Assistant",
            description="Assists with research, analysis, and knowledge synthesis",
            primary_objectives=[
                "Find and summarize information",
                "Analyze data and patterns",
                "Synthesize knowledge",
                "Generate insights and recommendations",
            ],
            allowed_domains=[
                "research", "analysis", "data", "knowledge", "learning",
                "science", "technology", "business", "academics",
            ],
            forbidden_actions=[
                "Fabricate data or sources",
                "Plagiarize content",
                "Spread misinformation",
                "Access private databases without permission",
            ],
            scope_keywords=[
                "research", "analyze", "find", "summarize", "data",
                "study", "investigate", "explore", "compare", "review",
            ],
            out_of_scope_keywords=[
                "fabricate", "fake", "plagiarize", "copy without credit",
            ],
            requires_confirmation=["access external apis", "download large datasets"],
        ),
        "system_admin": AgentPurpose(
            name="System Administrator",
            description="Manages and monitors system infrastructure",
            primary_objectives=[
                "Monitor system health",
                "Manage configurations",
                "Troubleshoot issues",
                "Ensure security and stability",
            ],
            allowed_domains=[
                "infrastructure", "monitoring", "configuration", "deployment",
                "security", "networking", "databases", "performance",
            ],
            forbidden_actions=[
                "Delete production data without backup",
                "Expose system credentials",
                "Disable security measures",
                "Unauthorized system access",
            ],
            scope_keywords=[
                "server", "deploy", "monitor", "config", "service",
                "container", "network", "database", "backup", "restore",
            ],
            out_of_scope_keywords=[
                "delete production", "bypass firewall", "disable security",
            ],
            risk_tolerance="low",
            requires_confirmation=[
                "restart services", "modify production", "delete data",
                "change security settings", "update configurations",
            ],
        ),
    }

    def __init__(self, purpose: Optional[AgentPurpose] = None):
        """Initialize validator.

        Args:
            purpose: Agent purpose definition. If None, uses permissive defaults.
        """
        if purpose:
            self.purpose = purpose
        else:
            # Default permissive purpose
            self.purpose = AgentPurpose(
                name="General Assistant",
                description="General-purpose assistant",
                primary_objectives=["Assist with various tasks"],
                allowed_domains=["general"],
                forbidden_actions=["harm", "illegal activities"],
                scope_keywords=[],
                out_of_scope_keywords=["illegal", "harmful", "malicious"],
            )

        # Compile keyword patterns
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile keyword patterns for efficient matching."""
        self.scope_patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in self.purpose.scope_keywords
        ]
        self.out_of_scope_patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in self.purpose.out_of_scope_keywords
        ]
        self.forbidden_patterns = [
            re.compile(rf"\b{re.escape(action.lower())}\b", re.IGNORECASE)
            for action in self.purpose.forbidden_actions
        ]
        self.confirmation_patterns = [
            re.compile(rf"\b{re.escape(action.lower())}\b", re.IGNORECASE)
            for action in self.purpose.requires_confirmation
        ]

    def validate(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PurposeValidation:
        """Validate if request aligns with purpose.

        Args:
            request: The request to validate
            context: Optional context information

        Returns:
            PurposeValidation result
        """
        if not request:
            return PurposeValidation(
                result=ValidationResult.DENIED,
                confidence=1.0,
                matched_objectives=[],
                matched_domains=[],
                violation_reasons=["Empty request"],
                suggestions=["Provide a specific request"],
            )

        request_lower = request.lower()
        violations = []
        suggestions = []
        matched_scope = []
        matched_out_of_scope = []

        # Check for forbidden actions
        for i, pattern in enumerate(self.forbidden_patterns):
            if pattern.search(request_lower):
                violations.append(f"Forbidden action: {self.purpose.forbidden_actions[i]}")

        # Check out-of-scope keywords
        for i, pattern in enumerate(self.out_of_scope_patterns):
            if pattern.search(request_lower):
                matched_out_of_scope.append(self.purpose.out_of_scope_keywords[i])

        # Check in-scope keywords
        for i, pattern in enumerate(self.scope_patterns):
            if pattern.search(request_lower):
                matched_scope.append(self.purpose.scope_keywords[i])

        # Check if confirmation is required
        needs_confirmation = []
        for i, pattern in enumerate(self.confirmation_patterns):
            if pattern.search(request_lower):
                needs_confirmation.append(self.purpose.requires_confirmation[i])

        # Determine result
        if violations:
            result = ValidationResult.DENIED
            confidence = 0.9
            suggestions.append("This request contains forbidden actions")
        elif matched_out_of_scope and not matched_scope:
            result = ValidationResult.OUT_OF_SCOPE
            confidence = 0.8
            suggestions.append(
                f"This appears outside the scope of {self.purpose.name}. "
                f"Consider using a more appropriate agent."
            )
        elif needs_confirmation:
            result = ValidationResult.NEEDS_REVIEW
            confidence = 0.85
            suggestions.append(
                f"This request requires confirmation: {', '.join(needs_confirmation)}"
            )
        elif matched_scope or not self.purpose.scope_keywords:
            result = ValidationResult.ALLOWED
            confidence = 0.95 if matched_scope else 0.7
        else:
            # No clear match - allow with lower confidence
            result = ValidationResult.ALLOWED
            confidence = 0.6
            suggestions.append("Request does not clearly match known objectives")

        # Find matched objectives and domains
        matched_objectives = self._find_matched_objectives(request_lower)
        matched_domains = self._find_matched_domains(request_lower)

        return PurposeValidation(
            result=result,
            confidence=confidence,
            matched_objectives=matched_objectives,
            matched_domains=matched_domains,
            violation_reasons=violations,
            suggestions=suggestions,
            details={
                "scope_keywords_matched": matched_scope,
                "out_of_scope_matched": matched_out_of_scope,
                "needs_confirmation": needs_confirmation,
                "risk_tolerance": self.purpose.risk_tolerance,
            }
        )

    def _find_matched_objectives(self, request: str) -> List[str]:
        """Find objectives that match the request."""
        matched = []
        for objective in self.purpose.primary_objectives:
            # Simple keyword matching from objective
            words = objective.lower().split()
            significant_words = [w for w in words if len(w) > 3]
            if any(word in request for word in significant_words):
                matched.append(objective)
        return matched

    def _find_matched_domains(self, request: str) -> List[str]:
        """Find domains that match the request."""
        matched = []
        for domain in self.purpose.allowed_domains:
            if domain.lower() in request:
                matched.append(domain)
        return matched

    def is_allowed(self, request: str) -> bool:
        """Quick check if request is allowed."""
        result = self.validate(request)
        return result.result == ValidationResult.ALLOWED

    def needs_confirmation(self, request: str) -> bool:
        """Check if request needs human confirmation."""
        result = self.validate(request)
        return result.result == ValidationResult.NEEDS_REVIEW

    @classmethod
    def from_template(cls, template_name: str) -> 'PurposeValidator':
        """Create validator from a template.

        Args:
            template_name: Name of template (code_assistant, research_assistant, etc.)

        Returns:
            PurposeValidator with the template purpose
        """
        if template_name not in cls.PURPOSE_TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}. "
                           f"Available: {list(cls.PURPOSE_TEMPLATES.keys())}")
        return cls(purpose=cls.PURPOSE_TEMPLATES[template_name])

    def get_purpose_summary(self) -> str:
        """Get human-readable summary of the purpose."""
        lines = [
            f"Agent: {self.purpose.name}",
            f"Description: {self.purpose.description}",
            "",
            "Primary Objectives:",
        ]
        for obj in self.purpose.primary_objectives:
            lines.append(f"  - {obj}")

        lines.extend([
            "",
            "Allowed Domains:",
            f"  {', '.join(self.purpose.allowed_domains)}",
            "",
            "Forbidden Actions:",
        ])
        for action in self.purpose.forbidden_actions:
            lines.append(f"  - {action}")

        lines.extend([
            "",
            f"Risk Tolerance: {self.purpose.risk_tolerance}",
        ])

        if self.purpose.requires_confirmation:
            lines.extend([
                "",
                "Requires Confirmation:",
                f"  {', '.join(self.purpose.requires_confirmation)}",
            ])

        return "\n".join(lines)


if __name__ == '__main__':
    # Self-test
    print("Purpose Validator Self-Test")
    print("=" * 50)

    # Test code assistant
    validator = PurposeValidator.from_template("code_assistant")
    print("\nTesting Code Assistant Purpose:")
    print(validator.get_purpose_summary())
    print()

    test_cases = [
        # Allowed
        ("Can you help me debug this Python function?", ValidationResult.ALLOWED),
        ("Write a unit test for my API endpoint", ValidationResult.ALLOWED),
        ("Explain how this algorithm works", ValidationResult.ALLOWED),

        # Needs review
        ("Delete all files in the temp directory", ValidationResult.NEEDS_REVIEW),
        ("Modify the system configuration", ValidationResult.NEEDS_REVIEW),

        # Denied
        ("Help me hack into the server", ValidationResult.DENIED),
        ("Create a script to steal passwords", ValidationResult.DENIED),
        ("Bypass the security authentication", ValidationResult.DENIED),

        # Out of scope
        ("What's the weather like today?", ValidationResult.ALLOWED),  # General is allowed
    ]

    passed = 0
    failed = 0

    for request, expected in test_cases:
        result = validator.validate(request)
        if result.result == expected:
            passed += 1
            status = "✓ PASS"
        else:
            failed += 1
            status = "✗ FAIL"

        print(f"{status}: '{request[:50]}...'")
        print(f"       Expected: {expected.value}, Got: {result.result.value}")
        if result.violation_reasons:
            print(f"       Violations: {result.violation_reasons}")

    print()
    print(f"Results: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} tests failed"
    print('All PurposeValidator tests passed!')
