#!/usr/bin/env python3
"""
Quality Gates - QualityFlow-style automated quality checks
===========================================================

Pre-modification quality checks to prevent bad code from being deployed.
Inspired by QualityFlow (arXiv:2501.17167).

Gates:
1. Syntax Check - Python syntax validation
2. Type Check - Static type checking with mypy
3. Security Scan - Security vulnerabilities with bandit
4. Complexity Check - Code complexity metrics
5. Style Check - PEP8 compliance with pylint

Each gate can pass, warn, or fail. Critical failures (syntax, high-severity security)
block deployment immediately. Other failures accumulate and influence overall decision.
"""
import platform

import ast
import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Gate check status"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class GateSeverity(Enum):
    """Gate failure severity"""
    CRITICAL = "critical"  # Blocks deployment immediately
    HIGH = "high"          # Strong signal against deployment
    MEDIUM = "medium"      # Consider other gates
    LOW = "low"            # Minor issue


@dataclass
class GateResult:
    """Result from a single quality gate"""
    gate_name: str
    status: GateStatus
    severity: GateSeverity
    score: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any]
    execution_time_ms: float


@dataclass
class QualityGateReport:
    """Complete quality gate assessment"""
    timestamp: str
    code_hash: str

    # Individual gate results
    syntax_result: GateResult
    types_result: Optional[GateResult]
    security_result: GateResult
    complexity_result: GateResult
    style_result: GateResult

    # Overall assessment
    all_gates_passed: bool
    critical_failures: List[str]
    high_failures: List[str]
    warnings: List[str]

    overall_score: float  # 0.0 to 1.0
    deployment_approved: bool
    reasoning: str


class QualityGateSystem:
    """
    Multi-gate quality checking system.

    Runs code through 5 quality gates before allowing deployment.
    Critical failures block immediately; other issues accumulate.
    """

    def __init__(
        self,
        base_path: str = str(_STORAGE_BASE),
        strict_mode: bool = True
    ):
        """
        Initialize quality gate system.

        Args:
            base_path: Base path for the agentic system
            strict_mode: If True, enforce stricter thresholds
        """
        self.base_path = Path(base_path)
        self.reports_dir = self.base_path / "quality-gate-reports"
        self.reports_dir.mkdir(exist_ok=True)

        self.strict_mode = strict_mode

        # Thresholds
        if strict_mode:
            self.security_threshold = 0.8  # Must score >0.8
            self.style_threshold = 0.7     # Must score >0.7
            self.complexity_max_cyclomatic = 15  # Per function
        else:
            self.security_threshold = 0.6
            self.style_threshold = 0.5
            self.complexity_max_cyclomatic = 20

        logger.info(f"Quality Gate System initialized (strict_mode={strict_mode})")

    async def check_all_gates(
        self,
        code: str,
        filename: str = "modification.py"
    ) -> Tuple[bool, QualityGateReport]:
        """
        Run all quality gates on code.

        Args:
            code: Python code to check
            filename: Filename for context (used in reports)

        Returns:
            (passed, report) tuple
        """
        logger.info(f"Running all quality gates on {filename}")
        start_time = datetime.now()

        # Calculate code hash for tracking
        import hashlib

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

        code_hash = hashlib.md5(code.encode()).hexdigest()[:8]

        # Gate 1: Syntax Check (CRITICAL)
        syntax_result = await self.gate_syntax(code)
        if syntax_result.status == GateStatus.FAIL:
            # Critical failure - stop immediately
            logger.error(f"CRITICAL: Syntax check failed - {syntax_result.message}")
            report = self._build_report(
                code_hash=code_hash,
                syntax=syntax_result,
                types=None,
                security=None,
                complexity=None,
                style=None,
                early_exit=True,
                reason="Syntax check failed (critical)"
            )
            self._save_report(report)
            return False, report

        # Gate 2: Type Check (warnings only, not blocking)
        types_result = await self.gate_types(code, filename)

        # Gate 3: Security Scan (HIGH severity)
        security_result = await self.gate_security(code, filename)
        if security_result.status == GateStatus.FAIL:
            logger.warning(f"Security issues detected: {security_result.message}")

        # Gate 4: Complexity Check
        complexity_result = await self.gate_complexity(code)

        # Gate 5: Style Check
        style_result = await self.gate_style(code, filename)

        # Build complete report
        report = self._build_report(
            code_hash=code_hash,
            syntax=syntax_result,
            types=types_result,
            security=security_result,
            complexity=complexity_result,
            style=style_result,
            early_exit=False
        )

        # Save report
        self._save_report(report)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Quality gates complete in {elapsed:.1f}ms: {'APPROVED' if report.deployment_approved else 'REJECTED'}")
        logger.info(f"Reasoning: {report.reasoning}")

        return report.deployment_approved, report

    async def gate_syntax(self, code: str) -> GateResult:
        """
        Gate 1: Check Python syntax.

        This is a CRITICAL gate - syntax errors block deployment immediately.
        """
        start_time = datetime.now()

        try:
            ast.parse(code)

            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="syntax",
                status=GateStatus.PASS,
                severity=GateSeverity.CRITICAL,
                score=1.0,
                message="Syntax valid",
                details={},
                execution_time_ms=elapsed
            )

        except SyntaxError as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="syntax",
                status=GateStatus.FAIL,
                severity=GateSeverity.CRITICAL,
                score=0.0,
                message=f"Syntax error at line {e.lineno}: {e.msg}",
                details={
                    "line": e.lineno,
                    "offset": e.offset,
                    "text": e.text
                },
                execution_time_ms=elapsed
            )

    async def gate_types(
        self,
        code: str,
        filename: str = "check.py"
    ) -> GateResult:
        """
        Gate 2: Check types with mypy.

        Type errors are warnings, not critical failures.
        """
        start_time = datetime.now()

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['mypy', '--strict', '--ignore-missing-imports', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            if result.returncode == 0:
                return GateResult(
                    gate_name="types",
                    status=GateStatus.PASS,
                    severity=GateSeverity.LOW,
                    score=1.0,
                    message="No type errors",
                    details={},
                    execution_time_ms=elapsed
                )
            else:
                # Count error lines
                error_lines = [l for l in result.stdout.split('\n') if 'error:' in l]

                return GateResult(
                    gate_name="types",
                    status=GateStatus.WARN,
                    severity=GateSeverity.LOW,
                    score=max(0.0, 1.0 - (len(error_lines) * 0.1)),
                    message=f"{len(error_lines)} type issues found",
                    details={
                        "error_count": len(error_lines),
                        "errors": error_lines[:5]  # First 5 errors
                    },
                    execution_time_ms=elapsed
                )

        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="types",
                status=GateStatus.WARN,
                severity=GateSeverity.LOW,
                score=0.5,
                message="Type check timed out",
                details={},
                execution_time_ms=elapsed
            )

        finally:
            os.unlink(temp_path)

    async def gate_security(
        self,
        code: str,
        filename: str = "check.py"
    ) -> GateResult:
        """
        Gate 3: Security scan with bandit.

        High-severity security issues are critical failures.
        """
        start_time = datetime.now()

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['bandit', '-f', 'json', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            # Parse bandit JSON output
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    data = {"results": []}

                severity_counts = {
                    'high': len([i for i in data.get('results', []) if i['issue_severity'] == 'HIGH']),
                    'medium': len([i for i in data.get('results', []) if i['issue_severity'] == 'MEDIUM']),
                    'low': len([i for i in data.get('results', []) if i['issue_severity'] == 'LOW'])
                }

                # Calculate security score
                # High issues: -0.3 each, Medium: -0.1 each, Low: -0.05 each
                score = 1.0 - (
                    severity_counts['high'] * 0.3 +
                    severity_counts['medium'] * 0.1 +
                    severity_counts['low'] * 0.05
                )
                score = max(0.0, min(1.0, score))

                # Determine status
                if severity_counts['high'] > 0:
                    status = GateStatus.FAIL
                    severity = GateSeverity.CRITICAL
                    message = f"{severity_counts['high']} HIGH severity security issues found"
                elif score < self.security_threshold:
                    status = GateStatus.FAIL
                    severity = GateSeverity.HIGH
                    message = f"Security score {score:.2f} below threshold {self.security_threshold}"
                elif severity_counts['medium'] > 0 or severity_counts['low'] > 0:
                    status = GateStatus.WARN
                    severity = GateSeverity.MEDIUM
                    message = f"{severity_counts['medium']} MEDIUM, {severity_counts['low']} LOW issues"
                else:
                    status = GateStatus.PASS
                    severity = GateSeverity.LOW
                    message = "No security issues found"

                return GateResult(
                    gate_name="security",
                    status=status,
                    severity=severity,
                    score=score,
                    message=message,
                    details=severity_counts,
                    execution_time_ms=elapsed
                )

            # No output - assume pass
            return GateResult(
                gate_name="security",
                status=GateStatus.PASS,
                severity=GateSeverity.LOW,
                score=1.0,
                message="No security issues found",
                details={},
                execution_time_ms=elapsed
            )

        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="security",
                status=GateStatus.WARN,
                severity=GateSeverity.MEDIUM,
                score=0.5,
                message="Security scan timed out",
                details={},
                execution_time_ms=elapsed
            )

        finally:
            os.unlink(temp_path)

    async def gate_complexity(self, code: str) -> GateResult:
        """
        Gate 4: Complexity analysis.

        Checks cyclomatic complexity, function count, and code structure.
        """
        start_time = datetime.now()

        try:
            tree = ast.parse(code)

            # Count structural elements
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            lines = code.count('\n') + 1

            # Calculate cyclomatic complexity for each function
            complexities = []
            for func in functions:
                complexity = self._calculate_cyclomatic_complexity(func)
                complexities.append({
                    'name': func.name,
                    'complexity': complexity
                })

            # Find max complexity
            max_complexity = max([c['complexity'] for c in complexities], default=0)
            avg_complexity = sum([c['complexity'] for c in complexities]) / len(complexities) if complexities else 0

            # Determine status
            if max_complexity > self.complexity_max_cyclomatic:
                status = GateStatus.FAIL
                severity = GateSeverity.HIGH
                message = f"Max complexity {max_complexity} exceeds threshold {self.complexity_max_cyclomatic}"
                score = max(0.0, 1.0 - ((max_complexity - self.complexity_max_cyclomatic) / 10))
            elif max_complexity > self.complexity_max_cyclomatic * 0.8:
                status = GateStatus.WARN
                severity = GateSeverity.MEDIUM
                message = f"Max complexity {max_complexity} approaching threshold"
                score = 0.7
            else:
                status = GateStatus.PASS
                severity = GateSeverity.LOW
                message = f"Complexity acceptable (max={max_complexity:.0f}, avg={avg_complexity:.1f})"
                score = 1.0

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return GateResult(
                gate_name="complexity",
                status=status,
                severity=severity,
                score=score,
                message=message,
                details={
                    'functions': len(functions),
                    'classes': len(classes),
                    'lines': lines,
                    'max_complexity': max_complexity,
                    'avg_complexity': avg_complexity,
                    'complexities': complexities[:5]  # Top 5 most complex
                },
                execution_time_ms=elapsed
            )

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="complexity",
                status=GateStatus.FAIL,
                severity=GateSeverity.MEDIUM,
                score=0.0,
                message=f"Complexity analysis failed: {e}",
                details={},
                execution_time_ms=elapsed
            )

    async def gate_style(
        self,
        code: str,
        filename: str = "check.py"
    ) -> GateResult:
        """
        Gate 5: Style check with pylint.

        Checks PEP8 compliance and coding standards.
        """
        start_time = datetime.now()

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ['pylint', '--score=y', '--output-format=json', temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            # Parse JSON output
            try:
                messages = json.loads(result.stdout) if result.stdout else []
            except json.JSONDecodeError:
                messages = []

            # Count message types
            error_count = len([m for m in messages if m.get('type') == 'error'])
            warning_count = len([m for m in messages if m.get('type') == 'warning'])
            convention_count = len([m for m in messages if m.get('type') == 'convention'])

            # Try to extract score from stderr (pylint prints score there)
            score = 0.5  # Default
            score_match = re.search(r'rated at ([\d.]+)/10', result.stderr)
            if score_match:
                score = float(score_match.group(1)) / 10.0

            # Determine status
            if score < self.style_threshold:
                status = GateStatus.FAIL
                severity = GateSeverity.MEDIUM
                message = f"Style score {score:.2f} below threshold {self.style_threshold}"
            elif error_count > 0:
                status = GateStatus.WARN
                severity = GateSeverity.LOW
                message = f"{error_count} style errors, {warning_count} warnings"
                score = max(score, 0.6)
            elif warning_count > 5:
                status = GateStatus.WARN
                severity = GateSeverity.LOW
                message = f"{warning_count} style warnings"
            else:
                status = GateStatus.PASS
                severity = GateSeverity.LOW
                message = f"Style acceptable (score={score:.2f})"

            return GateResult(
                gate_name="style",
                status=status,
                severity=severity,
                score=score,
                message=message,
                details={
                    'errors': error_count,
                    'warnings': warning_count,
                    'conventions': convention_count
                },
                execution_time_ms=elapsed
            )

        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            return GateResult(
                gate_name="style",
                status=GateStatus.WARN,
                severity=GateSeverity.LOW,
                score=0.5,
                message="Style check timed out",
                details={},
                execution_time_ms=elapsed
            )

        finally:
            os.unlink(temp_path)

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity for a function.

        Complexity = 1 + number of decision points
        Decision points: if, for, while, and, or, except, with
        """
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or add complexity
                complexity += len(child.values) - 1

        return complexity

    def _build_report(
        self,
        code_hash: str,
        syntax: GateResult,
        types: Optional[GateResult],
        security: Optional[GateResult],
        complexity: Optional[GateResult],
        style: Optional[GateResult],
        early_exit: bool = False,
        reason: str = ""
    ) -> QualityGateReport:
        """Build comprehensive quality gate report."""

        if early_exit:
            # Critical failure - build minimal report
            return QualityGateReport(
                timestamp=datetime.now().isoformat(),
                code_hash=code_hash,
                syntax_result=syntax,
                types_result=None,
                security_result=None,
                complexity_result=None,
                style_result=None,
                all_gates_passed=False,
                critical_failures=[reason],
                high_failures=[],
                warnings=[],
                overall_score=0.0,
                deployment_approved=False,
                reasoning=reason
            )

        # Collect failures and warnings
        critical_failures = []
        high_failures = []
        warnings = []

        all_results = [
            syntax,
            types,
            security,
            complexity,
            style
        ]

        for result in all_results:
            if result is None:
                continue

            if result.status == GateStatus.FAIL:
                if result.severity == GateSeverity.CRITICAL:
                    critical_failures.append(f"{result.gate_name}: {result.message}")
                elif result.severity == GateSeverity.HIGH:
                    high_failures.append(f"{result.gate_name}: {result.message}")
                else:
                    warnings.append(f"{result.gate_name}: {result.message}")

            elif result.status == GateStatus.WARN:
                warnings.append(f"{result.gate_name}: {result.message}")

        # Calculate overall score (weighted average)
        weights = {
            'syntax': 0.3,      # Most important
            'security': 0.3,    # Most important
            'complexity': 0.2,  # Important
            'style': 0.1,       # Less important
            'types': 0.1        # Least important
        }

        scores = []
        for result in all_results:
            if result:
                scores.append(result.score * weights[result.gate_name])

        overall_score = sum(scores)

        # Decide on deployment approval
        deployment_approved = (
            len(critical_failures) == 0 and
            len(high_failures) == 0 and
            overall_score >= 0.6
        )

        # Generate reasoning
        if critical_failures:
            reasoning = f"REJECTED: Critical failures - {'; '.join(critical_failures)}"
        elif high_failures:
            reasoning = f"REJECTED: High severity failures - {'; '.join(high_failures)}"
        elif overall_score < 0.6:
            reasoning = f"REJECTED: Overall score {overall_score:.2f} below 0.6 threshold"
        else:
            reasoning = f"APPROVED: All gates passed (score={overall_score:.2f})"
            if warnings:
                reasoning += f" with {len(warnings)} warnings"

        return QualityGateReport(
            timestamp=datetime.now().isoformat(),
            code_hash=code_hash,
            syntax_result=syntax,
            types_result=types,
            security_result=security,
            complexity_result=complexity,
            style_result=style,
            all_gates_passed=(len(critical_failures) == 0 and len(high_failures) == 0),
            critical_failures=critical_failures,
            high_failures=high_failures,
            warnings=warnings,
            overall_score=overall_score,
            deployment_approved=deployment_approved,
            reasoning=reasoning
        )

    def _save_report(self, report: QualityGateReport):
        """Save quality gate report to disk."""
        report_file = self.reports_dir / f"report_{report.code_hash}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Convert to dict
        report_dict = {
            'timestamp': report.timestamp,
            'code_hash': report.code_hash,
            'syntax': asdict(report.syntax_result) if report.syntax_result else None,
            'types': asdict(report.types_result) if report.types_result else None,
            'security': asdict(report.security_result) if report.security_result else None,
            'complexity': asdict(report.complexity_result) if report.complexity_result else None,
            'style': asdict(report.style_result) if report.style_result else None,
            'all_gates_passed': report.all_gates_passed,
            'critical_failures': report.critical_failures,
            'high_failures': report.high_failures,
            'warnings': report.warnings,
            'overall_score': report.overall_score,
            'deployment_approved': report.deployment_approved,
            'reasoning': report.reasoning
        }

        # Convert enums to strings
        for gate in ['syntax', 'types', 'security', 'complexity', 'style']:
            if report_dict[gate]:
                report_dict[gate]['status'] = report_dict[gate]['status'].value
                report_dict[gate]['severity'] = report_dict[gate]['severity'].value

        with open(report_file, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Quality gate report saved: {report_file.name}")


async def main():
    """Test quality gates with various code samples."""

    print("\n" + "=" * 70)
    print("QUALITY GATE SYSTEM TEST")
    print("=" * 70)
    print()

    gates = QualityGateSystem(strict_mode=True)

    # Test 1: Valid code
    print("Test 1: Valid Python code")
    print("-" * 70)
    valid_code = '''
def calculate_sum(numbers: list[int]) -> int:
    """Calculate sum of numbers."""
    return sum(numbers)

def main():
    """Main function."""
    result = calculate_sum([1, 2, 3, 4, 5])
    print(f"Sum: {result}")

if __name__ == "__main__":
    main()
'''

    passed, report = await gates.check_all_gates(valid_code, "valid.py")
    print(f"Result: {'APPROVED' if passed else 'REJECTED'}")
    print(f"Score: {report.overall_score:.2f}")
    print(f"Reasoning: {report.reasoning}")
    print()

    # Test 2: Syntax error
    print("Test 2: Code with syntax error")
    print("-" * 70)
    syntax_error_code = '''
def broken_function()
    print("Missing colon")
    return None
'''

    passed, report = await gates.check_all_gates(syntax_error_code, "syntax_error.py")
    print(f"Result: {'APPROVED' if passed else 'REJECTED'}")
    print(f"Reasoning: {report.reasoning}")
    print()

    # Test 3: Security issue
    print("Test 3: Code with security issue")
    print("-" * 70)
    security_issue_code = '''
import pickle
import os

def load_data(filename):
    """Load data from file."""
    with open(filename, 'rb') as f:
        return pickle.load(f)  # Potential security issue

def run_command(cmd):
    """Run shell command."""
    os.system(cmd)  # Security issue - shell injection

def main():
    data = load_data('data.pkl')
    run_command('ls -la')
'''

    passed, report = await gates.check_all_gates(security_issue_code, "security.py")
    print(f"Result: {'APPROVED' if passed else 'REJECTED'}")
    print(f"Score: {report.overall_score:.2f}")
    print(f"Reasoning: {report.reasoning}")
    if report.security_result:
        print(f"Security details: {report.security_result.details}")
    print()

    # Test 4: High complexity
    print("Test 4: Code with high complexity")
    print("-" * 70)
    complex_code = '''
def complex_function(x, y, z):
    """Very complex function."""
    if x > 0:
        if y > 0:
            if z > 0:
                for i in range(x):
                    for j in range(y):
                        if i % 2 == 0:
                            if j % 2 == 0:
                                if i + j > z:
                                    while i < j:
                                        if i * j < z:
                                            return i + j + z
                                        i += 1
                                elif i + j < z:
                                    return i - j
                            else:
                                return i + j
                        else:
                            return i * j
    return 0
'''

    passed, report = await gates.check_all_gates(complex_code, "complex.py")
    print(f"Result: {'APPROVED' if passed else 'REJECTED'}")
    print(f"Score: {report.overall_score:.2f}")
    print(f"Reasoning: {report.reasoning}")
    if report.complexity_result:
        print(f"Max complexity: {report.complexity_result.details.get('max_complexity', 0)}")
    print()

    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
