"""
Test Cases for Skill Evaluation

Defines test case structures and test suites for evaluating agent skills.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import uuid


class TestStatus(Enum):
    """Status of a test execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class ExpectedBehavior(Enum):
    """Types of expected behavior to verify."""
    RETURNS_VALUE = "returns_value"
    CONTAINS_TEXT = "contains_text"
    MATCHES_PATTERN = "matches_pattern"
    NO_ERRORS = "no_errors"
    WITHIN_TIME = "within_time"
    USES_TOOL = "uses_tool"
    AVOIDS_TOOL = "avoids_tool"
    FOLLOWS_CONSTRAINT = "follows_constraint"
    CUSTOM = "custom"


@dataclass
class SuccessCriterion:
    """A criterion that must be met for test success."""
    name: str
    behavior_type: ExpectedBehavior
    expected_value: Any = None
    tolerance: float = 0.0
    required: bool = True
    weight: float = 1.0
    custom_validator: Optional[Callable[[Any], bool]] = None


@dataclass
class TestInput:
    """Input for a test case."""
    data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """
    A single test case for skill evaluation.

    Attributes:
        name: Test case name
        skill: Skill being tested
        description: What this test verifies
        input: Test input data
        success_criteria: Criteria for success
        tags: Categories/labels
        timeout_seconds: Max execution time
        requires_setup: Setup function needed
        requires_teardown: Teardown function needed
    """
    name: str
    skill: str
    description: str
    input: TestInput
    success_criteria: List[SuccessCriterion]
    tags: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    requires_setup: bool = False
    requires_teardown: bool = False
    setup_fn: Optional[Callable[[], None]] = None
    teardown_fn: Optional[Callable[[], None]] = None
    priority: int = 5  # 1-10, 10 is highest
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.metadata.get("id"):
            self.metadata["id"] = str(uuid.uuid4())[:8]


@dataclass
class TestResult:
    """Result of executing a test case."""
    test_case: TestCase
    status: TestStatus
    passed_criteria: List[str]
    failed_criteria: List[str]
    execution_time_ms: float
    output: Any = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if test passed."""
        return self.status == TestStatus.PASSED

    @property
    def score(self) -> float:
        """Calculate test score (0.0 to 1.0)."""
        total = len(self.passed_criteria) + len(self.failed_criteria)
        if total == 0:
            return 0.0 if self.status != TestStatus.PASSED else 1.0
        return len(self.passed_criteria) / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_case.name,
            "skill": self.test_case.skill,
            "status": self.status.value,
            "passed_criteria": self.passed_criteria,
            "failed_criteria": self.failed_criteria,
            "execution_time_ms": self.execution_time_ms,
            "score": self.score,
            "error": self.error,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }


class TestSuite:
    """
    A collection of related test cases.

    Attributes:
        name: Suite name
        description: What this suite tests
        cases: List of test cases
        tags: Suite categories
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.tags = tags or []
        self.cases: List[TestCase] = []
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}

    def add_case(self, case: TestCase) -> None:
        """Add a test case to the suite."""
        self.cases.append(case)

    def add_cases(self, cases: List[TestCase]) -> None:
        """Add multiple test cases."""
        self.cases.extend(cases)

    def remove_case(self, name: str) -> bool:
        """Remove a test case by name."""
        for i, case in enumerate(self.cases):
            if case.name == name:
                del self.cases[i]
                return True
        return False

    def get_case(self, name: str) -> Optional[TestCase]:
        """Get a test case by name."""
        for case in self.cases:
            if case.name == name:
                return case
        return None

    def filter_by_tag(self, tag: str) -> List[TestCase]:
        """Filter cases by tag."""
        return [c for c in self.cases if tag in c.tags]

    def filter_by_skill(self, skill: str) -> List[TestCase]:
        """Filter cases by skill."""
        return [c for c in self.cases if c.skill == skill]

    def filter_by_priority(self, min_priority: int) -> List[TestCase]:
        """Filter cases by minimum priority."""
        return [c for c in self.cases if c.priority >= min_priority]

    def get_execution_order(self) -> List[TestCase]:
        """
        Get cases in dependency-respecting order.

        Returns cases ordered so dependencies are run first.
        """
        # Build dependency graph
        pending = {c.name: c for c in self.cases}
        ordered = []
        resolved = set()

        while pending:
            # Find cases with resolved dependencies
            ready = []
            for name, case in pending.items():
                deps = set(case.dependencies)
                if deps.issubset(resolved):
                    ready.append(name)

            if not ready:
                # Circular dependency or missing dependency
                # Just add remaining in priority order
                remaining = sorted(
                    pending.values(),
                    key=lambda c: c.priority,
                    reverse=True
                )
                ordered.extend(remaining)
                break

            # Add ready cases in priority order
            ready_cases = sorted(
                [pending[n] for n in ready],
                key=lambda c: c.priority,
                reverse=True
            )
            ordered.extend(ready_cases)

            for name in ready:
                resolved.add(name)
                del pending[name]

        return ordered

    @property
    def total_cases(self) -> int:
        """Total number of cases."""
        return len(self.cases)

    @property
    def skills_covered(self) -> List[str]:
        """List of unique skills tested."""
        return list(set(c.skill for c in self.cases))

    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "total_cases": self.total_cases,
            "skills_covered": self.skills_covered,
            "cases": [
                {
                    "name": c.name,
                    "skill": c.skill,
                    "tags": c.tags,
                    "priority": c.priority,
                }
                for c in self.cases
            ],
            "created_at": self.created_at.isoformat(),
        }


def create_test_case(
    name: str,
    skill: str,
    input_data: Dict[str, Any],
    expected_behavior: Union[str, ExpectedBehavior],
    success_criteria: Optional[List[Dict[str, Any]]] = None,
    description: str = "",
    tags: Optional[List[str]] = None,
    timeout: float = 30.0,
    priority: int = 5,
) -> TestCase:
    """
    Factory function to create a test case.

    Args:
        name: Test case name
        skill: Skill being tested
        input_data: Input data dictionary
        expected_behavior: Primary expected behavior
        success_criteria: Additional success criteria
        description: Test description
        tags: Test categories
        timeout: Timeout in seconds
        priority: Priority (1-10)

    Returns:
        Configured TestCase
    """
    # Parse expected behavior
    if isinstance(expected_behavior, str):
        try:
            behavior = ExpectedBehavior(expected_behavior)
        except ValueError:
            behavior = ExpectedBehavior.CUSTOM
    else:
        behavior = expected_behavior

    # Build criteria list
    criteria = [
        SuccessCriterion(
            name="primary_behavior",
            behavior_type=behavior,
            required=True,
        )
    ]

    # Add additional criteria
    if success_criteria:
        for crit in success_criteria:
            behavior_type = crit.get("type", ExpectedBehavior.CUSTOM)
            if isinstance(behavior_type, str):
                try:
                    behavior_type = ExpectedBehavior(behavior_type)
                except ValueError:
                    behavior_type = ExpectedBehavior.CUSTOM

            criteria.append(SuccessCriterion(
                name=crit.get("name", "criterion"),
                behavior_type=behavior_type,
                expected_value=crit.get("expected_value"),
                tolerance=crit.get("tolerance", 0.0),
                required=crit.get("required", True),
                weight=crit.get("weight", 1.0),
            ))

    return TestCase(
        name=name,
        skill=skill,
        description=description or f"Test {skill} capability",
        input=TestInput(data=input_data),
        success_criteria=criteria,
        tags=tags or [],
        timeout_seconds=timeout,
        priority=priority,
    )


def create_constraint_test(
    name: str,
    constraint_name: str,
    input_action: str,
    should_block: bool = True,
    tags: Optional[List[str]] = None,
) -> TestCase:
    """
    Create a test case for constraint checking.

    Args:
        name: Test name
        constraint_name: Constraint being tested
        input_action: Action to test against constraint
        should_block: Whether constraint should block action
        tags: Test categories

    Returns:
        TestCase for constraint testing
    """
    return TestCase(
        name=name,
        skill="constraint_enforcement",
        description=f"Test that {constraint_name} {'blocks' if should_block else 'allows'} action",
        input=TestInput(
            data={"action": input_action},
            context={"constraint": constraint_name},
        ),
        success_criteria=[
            SuccessCriterion(
                name="constraint_checked",
                behavior_type=ExpectedBehavior.FOLLOWS_CONSTRAINT,
                expected_value=should_block,
                required=True,
            ),
            SuccessCriterion(
                name="no_bypass",
                behavior_type=ExpectedBehavior.NO_ERRORS,
                required=True,
            ),
        ],
        tags=(tags or []) + ["constraint", "security"],
        priority=8,  # Constraint tests are high priority
    )


def create_capability_test(
    name: str,
    capability_name: str,
    input_data: Dict[str, Any],
    expected_tools: List[str],
    description: str = "",
) -> TestCase:
    """
    Create a test case for capability verification.

    Args:
        name: Test name
        capability_name: Capability being tested
        input_data: Input data
        expected_tools: Tools that should be used
        description: Test description

    Returns:
        TestCase for capability testing
    """
    criteria = [
        SuccessCriterion(
            name="capability_available",
            behavior_type=ExpectedBehavior.RETURNS_VALUE,
            expected_value=True,
            required=True,
        ),
    ]

    for tool in expected_tools:
        criteria.append(SuccessCriterion(
            name=f"uses_{tool}",
            behavior_type=ExpectedBehavior.USES_TOOL,
            expected_value=tool,
            required=False,
            weight=0.5,
        ))

    return TestCase(
        name=name,
        skill=capability_name,
        description=description or f"Test {capability_name} capability",
        input=TestInput(data=input_data),
        success_criteria=criteria,
        tags=["capability"],
        priority=7,
    )


if __name__ == '__main__':
    print("Test Cases Module Self-Test")
    print("=" * 50)

    # Test TestCase creation
    case = create_test_case(
        name="Read Python File",
        skill="file_reading",
        input_data={"path": "test.py"},
        expected_behavior="returns_value",
        success_criteria=[
            {"name": "content_valid", "type": "returns_value"},
            {"name": "fast_execution", "type": "within_time", "expected_value": 1000},
        ],
        tags=["file_ops", "core"],
    )
    assert case.name == "Read Python File"
    assert case.skill == "file_reading"
    assert len(case.success_criteria) == 3
    print(f"Created test case: {case.name}")

    # Test constraint test creation
    constraint_test = create_constraint_test(
        name="Block Production Deploy",
        constraint_name="no_production_deploy",
        input_action="deploy to production",
        should_block=True,
    )
    assert "constraint" in constraint_test.tags
    assert constraint_test.priority == 8
    print(f"Created constraint test: {constraint_test.name}")

    # Test capability test creation
    cap_test = create_capability_test(
        name="Test Code Reading",
        capability_name="code_reading",
        input_data={"file": "app.py"},
        expected_tools=["Read", "Grep"],
    )
    assert len(cap_test.success_criteria) >= 2
    print(f"Created capability test: {cap_test.name}")

    # Test TestSuite
    suite = TestSuite(
        name="Code Agent Tests",
        description="Test code agent capabilities",
        tags=["code", "agent"],
    )
    suite.add_case(case)
    suite.add_case(constraint_test)
    suite.add_case(cap_test)

    assert suite.total_cases == 3
    assert "file_reading" in suite.skills_covered
    print(f"\nSuite: {suite.name}")
    print(f"  Total cases: {suite.total_cases}")
    print(f"  Skills covered: {suite.skills_covered}")

    # Test filtering
    constraint_cases = suite.filter_by_tag("constraint")
    assert len(constraint_cases) == 1
    print(f"  Constraint tests: {len(constraint_cases)}")

    # Test execution order
    # Add dependent test
    dependent_case = TestCase(
        name="Dependent Test",
        skill="advanced_reading",
        description="Depends on file reading",
        input=TestInput(data={}),
        success_criteria=[],
        dependencies=["Read Python File"],
    )
    suite.add_case(dependent_case)

    order = suite.get_execution_order()
    file_idx = next(i for i, c in enumerate(order) if c.name == "Read Python File")
    dep_idx = next(i for i, c in enumerate(order) if c.name == "Dependent Test")
    assert file_idx < dep_idx, "Dependencies should run first"
    print(f"  Execution order verified")

    # Test TestResult
    result = TestResult(
        test_case=case,
        status=TestStatus.PASSED,
        passed_criteria=["primary_behavior", "content_valid"],
        failed_criteria=["fast_execution"],
        execution_time_ms=1500,
        output={"content": "file data"},
    )
    assert result.passed
    assert result.score == 2/3
    print(f"\nTest result score: {result.score:.2f}")

    # Test serialization
    suite_dict = suite.to_dict()
    assert suite_dict["total_cases"] == 4
    result_dict = result.to_dict()
    assert result_dict["status"] == "passed"
    print(f"Serialization works")

    print("\nAll test cases module tests passed!")
