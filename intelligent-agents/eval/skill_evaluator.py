"""
Skill Evaluator

Core evaluation engine for testing agent skills.
Executes test suites and produces evaluation results.
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import time
import re
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .test_cases import (
    TestCase,
    TestSuite,
    TestResult,
    TestStatus,
    ExpectedBehavior,
    SuccessCriterion,
)


class EvaluationMode(Enum):
    """Evaluation execution modes."""
    STRICT = "strict"       # All required criteria must pass
    LENIENT = "lenient"     # Partial passes accepted
    SCORED = "scored"       # Score-based evaluation


@dataclass
class EvaluationConfig:
    """Configuration for evaluation."""
    mode: EvaluationMode = EvaluationMode.STRICT
    timeout_multiplier: float = 1.0
    parallel_execution: bool = False
    max_workers: int = 4
    continue_on_failure: bool = True
    retry_count: int = 0
    verbose: bool = False
    capture_output: bool = True
    record_timing: bool = True


@dataclass
class SkillScore:
    """Score for a specific skill."""
    skill_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    avg_execution_time_ms: float
    criteria_pass_rate: float
    weighted_score: float

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests


@dataclass
class EvaluationResult:
    """Complete evaluation results."""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    execution_time_ms: float
    test_results: List[TestResult]
    skill_scores: Dict[str, SkillScore]
    config: EvaluationConfig
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overall_pass_rate(self) -> float:
        """Overall pass rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    @property
    def overall_score(self) -> float:
        """Overall weighted score."""
        if not self.skill_scores:
            return 0.0
        return sum(s.weighted_score for s in self.skill_scores.values()) / len(self.skill_scores)

    @property
    def success(self) -> bool:
        """Check if evaluation succeeded (all tests passed)."""
        return self.failed == 0 and self.errors == 0

    def get_failed_tests(self) -> List[TestResult]:
        """Get list of failed test results."""
        return [r for r in self.test_results if r.status == TestStatus.FAILED]

    def get_slow_tests(self, threshold_ms: float = 1000) -> List[TestResult]:
        """Get tests that exceeded time threshold."""
        return [r for r in self.test_results if r.execution_time_ms > threshold_ms]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suite_name": self.suite_name,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "execution_time_ms": self.execution_time_ms,
            "overall_pass_rate": self.overall_pass_rate,
            "overall_score": self.overall_score,
            "success": self.success,
            "skill_scores": {
                name: {
                    "total_tests": s.total_tests,
                    "passed_tests": s.passed_tests,
                    "pass_rate": s.pass_rate,
                    "weighted_score": s.weighted_score,
                }
                for name, s in self.skill_scores.items()
            },
            "test_results": [r.to_dict() for r in self.test_results],
            "timestamp": self.timestamp.isoformat(),
        }


class CriterionValidator:
    """Validates success criteria against actual outputs."""

    @staticmethod
    def validate(
        criterion: SuccessCriterion,
        actual_output: Any,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Validate a criterion against actual output.

        Args:
            criterion: Criterion to validate
            actual_output: Actual output from execution
            context: Additional context

        Returns:
            True if criterion is satisfied
        """
        context = context or {}
        behavior = criterion.behavior_type

        if behavior == ExpectedBehavior.RETURNS_VALUE:
            if criterion.expected_value is not None:
                return actual_output == criterion.expected_value
            return actual_output is not None

        elif behavior == ExpectedBehavior.CONTAINS_TEXT:
            if isinstance(actual_output, str) and isinstance(criterion.expected_value, str):
                return criterion.expected_value in actual_output
            return False

        elif behavior == ExpectedBehavior.MATCHES_PATTERN:
            if isinstance(actual_output, str) and isinstance(criterion.expected_value, str):
                return bool(re.search(criterion.expected_value, actual_output))
            return False

        elif behavior == ExpectedBehavior.NO_ERRORS:
            return not context.get("error") and not context.get("exception")

        elif behavior == ExpectedBehavior.WITHIN_TIME:
            execution_time = context.get("execution_time_ms", float('inf'))
            expected_time = criterion.expected_value or float('inf')
            return execution_time <= expected_time * (1 + criterion.tolerance)

        elif behavior == ExpectedBehavior.USES_TOOL:
            tools_used = context.get("tools_used", [])
            return criterion.expected_value in tools_used

        elif behavior == ExpectedBehavior.AVOIDS_TOOL:
            tools_used = context.get("tools_used", [])
            return criterion.expected_value not in tools_used

        elif behavior == ExpectedBehavior.FOLLOWS_CONSTRAINT:
            constraint_triggered = context.get("constraint_triggered", False)
            return constraint_triggered == criterion.expected_value

        elif behavior == ExpectedBehavior.CUSTOM:
            if criterion.custom_validator:
                return criterion.custom_validator(actual_output)
            return True  # No validator = pass

        return False


class SkillEvaluator:
    """
    Core engine for evaluating agent skills.

    Executes test suites against agents and produces detailed results.
    """

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """Initialize evaluator with configuration."""
        self.config = config or EvaluationConfig()
        self.validator = CriterionValidator()
        self._execution_hooks: List[Callable] = []

    def add_execution_hook(self, hook: Callable[[TestCase, Any], None]) -> None:
        """Add a hook called after each test execution."""
        self._execution_hooks.append(hook)

    def run_suite(
        self,
        agent: Any,
        suite: TestSuite,
        config_override: Optional[EvaluationConfig] = None
    ) -> EvaluationResult:
        """
        Run a test suite against an agent.

        Args:
            agent: Agent to evaluate (must have execute method)
            suite: Test suite to run
            config_override: Override default config

        Returns:
            EvaluationResult with all test outcomes
        """
        config = config_override or self.config
        start_time = time.time()

        # Get tests in execution order
        tests = suite.get_execution_order()

        # Run tests
        if config.parallel_execution:
            results = self._run_parallel(agent, tests, config)
        else:
            results = self._run_sequential(agent, tests, config)

        execution_time_ms = (time.time() - start_time) * 1000

        # Calculate skill scores
        skill_scores = self._calculate_skill_scores(results)

        # Aggregate results
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status in [TestStatus.ERROR, TestStatus.TIMEOUT])

        return EvaluationResult(
            suite_name=suite.name,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            execution_time_ms=execution_time_ms,
            test_results=results,
            skill_scores=skill_scores,
            config=config,
        )

    def run_single(
        self,
        agent: Any,
        test_case: TestCase,
        config_override: Optional[EvaluationConfig] = None
    ) -> TestResult:
        """
        Run a single test case.

        Args:
            agent: Agent to evaluate
            test_case: Test case to run
            config_override: Override default config

        Returns:
            TestResult for the test
        """
        config = config_override or self.config
        return self._execute_test(agent, test_case, config)

    def _run_sequential(
        self,
        agent: Any,
        tests: List[TestCase],
        config: EvaluationConfig
    ) -> List[TestResult]:
        """Run tests sequentially."""
        results = []
        failed_dependencies = set()

        for test in tests:
            # Check dependencies
            if any(dep in failed_dependencies for dep in test.dependencies):
                results.append(TestResult(
                    test_case=test,
                    status=TestStatus.SKIPPED,
                    passed_criteria=[],
                    failed_criteria=[],
                    execution_time_ms=0,
                    warnings=["Skipped due to failed dependencies"],
                ))
                continue

            # Execute test
            result = self._execute_test(agent, test, config)
            results.append(result)

            # Track failures for dependency checking
            if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                failed_dependencies.add(test.name)

            # Stop on failure if configured
            if not config.continue_on_failure and not result.passed:
                # Mark remaining as skipped
                remaining = tests[tests.index(test) + 1:]
                for remaining_test in remaining:
                    results.append(TestResult(
                        test_case=remaining_test,
                        status=TestStatus.SKIPPED,
                        passed_criteria=[],
                        failed_criteria=[],
                        execution_time_ms=0,
                        warnings=["Skipped due to earlier failure"],
                    ))
                break

        return results

    def _run_parallel(
        self,
        agent: Any,
        tests: List[TestCase],
        config: EvaluationConfig
    ) -> List[TestResult]:
        """Run tests in parallel."""
        # Filter out tests with dependencies (run those sequentially)
        independent = [t for t in tests if not t.dependencies]
        dependent = [t for t in tests if t.dependencies]

        results = []

        # Run independent tests in parallel
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = {
                executor.submit(self._execute_test, agent, test, config): test
                for test in independent
            }

            for future in futures:
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    test = futures[future]
                    results.append(TestResult(
                        test_case=test,
                        status=TestStatus.ERROR,
                        passed_criteria=[],
                        failed_criteria=[],
                        execution_time_ms=0,
                        error=str(e),
                    ))

        # Run dependent tests sequentially
        failed_names = {r.test_case.name for r in results if r.status != TestStatus.PASSED}
        for test in dependent:
            if any(dep in failed_names for dep in test.dependencies):
                results.append(TestResult(
                    test_case=test,
                    status=TestStatus.SKIPPED,
                    passed_criteria=[],
                    failed_criteria=[],
                    execution_time_ms=0,
                    warnings=["Skipped due to failed dependencies"],
                ))
            else:
                result = self._execute_test(agent, test, config)
                results.append(result)
                if result.status != TestStatus.PASSED:
                    failed_names.add(test.name)

        return results

    def _execute_test(
        self,
        agent: Any,
        test: TestCase,
        config: EvaluationConfig
    ) -> TestResult:
        """Execute a single test case."""
        start_time = time.time()
        output = None
        error = None
        context = {"tools_used": [], "constraint_triggered": False}

        try:
            # Run setup if needed
            if test.requires_setup and test.setup_fn:
                test.setup_fn()

            # Calculate timeout
            timeout = test.timeout_seconds * config.timeout_multiplier

            # Execute with retry
            for attempt in range(config.retry_count + 1):
                try:
                    # Execute the test
                    output = self._invoke_agent(agent, test, timeout, context)
                    break
                except FuturesTimeoutError:
                    if attempt == config.retry_count:
                        raise
                except Exception as e:
                    if attempt == config.retry_count:
                        raise
                    time.sleep(0.1)  # Brief pause before retry

        except FuturesTimeoutError:
            execution_time_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_case=test,
                status=TestStatus.TIMEOUT,
                passed_criteria=[],
                failed_criteria=[c.name for c in test.success_criteria],
                execution_time_ms=execution_time_ms,
                error="Test timed out",
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error = str(e)
            context["error"] = error
            context["exception"] = True

        finally:
            # Run teardown if needed
            if test.requires_teardown and test.teardown_fn:
                try:
                    test.teardown_fn()
                except Exception:
                    pass

        execution_time_ms = (time.time() - start_time) * 1000
        context["execution_time_ms"] = execution_time_ms

        # Validate criteria
        passed_criteria = []
        failed_criteria = []

        for criterion in test.success_criteria:
            if self.validator.validate(criterion, output, context):
                passed_criteria.append(criterion.name)
            else:
                failed_criteria.append(criterion.name)

        # Determine status based on mode
        status = self._determine_status(
            passed_criteria,
            failed_criteria,
            test.success_criteria,
            error,
            config.mode
        )

        result = TestResult(
            test_case=test,
            status=status,
            passed_criteria=passed_criteria,
            failed_criteria=failed_criteria,
            execution_time_ms=execution_time_ms,
            output=output if config.capture_output else None,
            error=error,
            metrics={"execution_time_ms": execution_time_ms},
        )

        # Call execution hooks
        for hook in self._execution_hooks:
            try:
                hook(test, result)
            except Exception:
                pass

        return result

    def _invoke_agent(
        self,
        agent: Any,
        test: TestCase,
        timeout: float,
        context: Dict[str, Any]
    ) -> Any:
        """Invoke the agent with the test input."""
        # Check if agent has an execute method
        if hasattr(agent, 'execute'):
            return agent.execute(test.input.data, test.input.context)

        # Check if agent has a test-specific method
        method_name = f"test_{test.skill}"
        if hasattr(agent, method_name):
            method = getattr(agent, method_name)
            return method(test.input.data)

        # Check if agent is a persona and has capability
        if hasattr(agent, 'has_capability'):
            if agent.has_capability(test.skill):
                # Simulate capability execution
                context["tools_used"] = agent.get_allowed_tools()
                return {"success": True, "skill": test.skill}

            # Check for constraint violations
            if hasattr(agent, 'check_constraint'):
                action = test.input.data.get("action", "")
                constraint = agent.check_constraint(action)
                if constraint:
                    context["constraint_triggered"] = True
                    return {"blocked": True, "constraint": constraint.name}

        # Generic callable check
        if callable(agent):
            return agent(test.input.data)

        raise ValueError(f"Agent doesn't support execution for skill: {test.skill}")

    def _determine_status(
        self,
        passed: List[str],
        failed: List[str],
        criteria: List[SuccessCriterion],
        error: Optional[str],
        mode: EvaluationMode
    ) -> TestStatus:
        """Determine test status based on criteria results."""
        if error:
            return TestStatus.ERROR

        required_criteria = [c for c in criteria if c.required]
        required_names = {c.name for c in required_criteria}

        if mode == EvaluationMode.STRICT:
            # All required criteria must pass
            if any(name in failed for name in required_names):
                return TestStatus.FAILED
            if not passed:
                return TestStatus.FAILED
            return TestStatus.PASSED

        elif mode == EvaluationMode.LENIENT:
            # At least some criteria must pass
            if not passed:
                return TestStatus.FAILED
            return TestStatus.PASSED

        else:  # SCORED
            # Score-based (any score > 0.5 passes)
            total = len(passed) + len(failed)
            if total == 0:
                return TestStatus.PASSED
            score = len(passed) / total
            return TestStatus.PASSED if score >= 0.5 else TestStatus.FAILED

    def _calculate_skill_scores(
        self,
        results: List[TestResult]
    ) -> Dict[str, SkillScore]:
        """Calculate scores per skill."""
        skill_results: Dict[str, List[TestResult]] = {}

        for result in results:
            skill = result.test_case.skill
            if skill not in skill_results:
                skill_results[skill] = []
            skill_results[skill].append(result)

        skill_scores = {}
        for skill, skill_tests in skill_results.items():
            total = len(skill_tests)
            passed = sum(1 for r in skill_tests if r.status == TestStatus.PASSED)
            failed = sum(1 for r in skill_tests if r.status == TestStatus.FAILED)
            skipped = sum(1 for r in skill_tests if r.status == TestStatus.SKIPPED)
            errors = sum(1 for r in skill_tests if r.status in [TestStatus.ERROR, TestStatus.TIMEOUT])

            execution_times = [r.execution_time_ms for r in skill_tests if r.execution_time_ms > 0]
            avg_time = sum(execution_times) / len(execution_times) if execution_times else 0

            # Calculate criteria pass rate
            all_passed = sum(len(r.passed_criteria) for r in skill_tests)
            all_failed = sum(len(r.failed_criteria) for r in skill_tests)
            criteria_rate = all_passed / (all_passed + all_failed) if (all_passed + all_failed) > 0 else 0

            # Calculate weighted score
            test_scores = [r.score for r in skill_tests]
            weighted = sum(test_scores) / len(test_scores) if test_scores else 0

            skill_scores[skill] = SkillScore(
                skill_name=skill,
                total_tests=total,
                passed_tests=passed,
                failed_tests=failed,
                skipped_tests=skipped,
                error_tests=errors,
                avg_execution_time_ms=avg_time,
                criteria_pass_rate=criteria_rate,
                weighted_score=weighted,
            )

        return skill_scores


if __name__ == '__main__':
    from .test_cases import create_test_case, create_constraint_test

    print("SkillEvaluator Self-Test")
    print("=" * 50)

    # Create a mock agent
    class MockAgent:
        def __init__(self):
            self.capabilities = ["file_reading", "code_writing"]
            self.tools = ["Read", "Write", "Grep"]

        def has_capability(self, name: str) -> bool:
            return name in self.capabilities

        def get_allowed_tools(self) -> List[str]:
            return self.tools

        def check_constraint(self, action: str) -> Optional[Any]:
            if "production" in action.lower():
                class MockConstraint:
                    name = "no_production"
                return MockConstraint()
            return None

        def execute(self, data: Dict, context: Dict = None) -> Any:
            if data.get("error"):
                raise ValueError("Simulated error")
            return {"result": "success", "data": data}

    agent = MockAgent()

    # Create test suite
    suite = TestSuite(name="Mock Agent Tests")

    # Add basic test
    suite.add_case(create_test_case(
        name="Basic Execution",
        skill="file_reading",
        input_data={"path": "test.py"},
        expected_behavior="returns_value",
    ))

    # Add constraint test
    suite.add_case(create_constraint_test(
        name="Block Production",
        constraint_name="no_production",
        input_action="deploy to production",
        should_block=True,
    ))

    # Add capability test
    from .test_cases import create_capability_test
    suite.add_case(create_capability_test(
        name="File Reading Capability",
        capability_name="file_reading",
        input_data={},
        expected_tools=["Read", "Grep"],
    ))

    print(f"Test Suite: {suite.name}")
    print(f"Total cases: {suite.total_cases}")

    # Run evaluation
    evaluator = SkillEvaluator(EvaluationConfig(
        mode=EvaluationMode.LENIENT,
        verbose=True,
    ))

    results = evaluator.run_suite(agent, suite)

    print(f"\nResults:")
    print(f"  Passed: {results.passed}/{results.total_tests}")
    print(f"  Failed: {results.failed}")
    print(f"  Errors: {results.errors}")
    print(f"  Overall pass rate: {results.overall_pass_rate:.1%}")
    print(f"  Overall score: {results.overall_score:.2f}")

    # Check skill scores
    print(f"\nSkill Scores:")
    for skill, score in results.skill_scores.items():
        print(f"  {skill}: {score.pass_rate:.1%} ({score.passed_tests}/{score.total_tests})")

    # Test single execution
    single_result = evaluator.run_single(agent, suite.cases[0])
    print(f"\nSingle test result: {single_result.status.value}")

    # Verify results make sense
    assert results.total_tests == suite.total_cases
    assert results.passed + results.failed + results.skipped + results.errors == results.total_tests

    print("\nAll SkillEvaluator tests passed!")
