#!/usr/bin/env python3
"""
Code Quality Grader
===================

Evaluates code generation quality across multiple dimensions:
- Correctness: Does the code work?
- Style: PEP8, naming conventions
- Efficiency: Time/space complexity
- Security: No vulnerabilities
- Maintainability: Readability, modularity
"""

import ast
import re
import subprocess
import tempfile
from typing import Dict, Any, Tuple, Optional
from pathlib import Path


def grade_syntax(code: str) -> Tuple[float, str]:
    """Check if code has valid Python syntax."""
    try:
        ast.parse(code)
        return 1.0, "Valid syntax"
    except SyntaxError as e:
        return 0.0, f"Syntax error: {e}"


def grade_execution(code: str, test_cases: list = None) -> Tuple[float, str]:
    """Execute code and check against test cases."""
    if not test_cases:
        # Just check if it runs without error
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                f.flush()
                result = subprocess.run(
                    ['python3', f.name],
                    capture_output=True,
                    timeout=10,
                    text=True
                )
                Path(f.name).unlink()

                if result.returncode == 0:
                    return 1.0, "Code executed successfully"
                else:
                    return 0.5, f"Runtime error: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return 0.3, "Execution timeout"
        except Exception as e:
            return 0.0, f"Execution failed: {e}"

    # Run test cases
    passed = 0
    for i, test in enumerate(test_cases):
        try:
            exec_globals = {}
            exec(code, exec_globals)

            if 'input' in test and 'expected' in test:
                func_name = test.get('function', 'main')
                if func_name in exec_globals:
                    result = exec_globals[func_name](*test['input'])
                    if result == test['expected']:
                        passed += 1
        except Exception:
            pass

    score = passed / len(test_cases) if test_cases else 0.0
    return score, f"Passed {passed}/{len(test_cases)} test cases"


def grade_style(code: str) -> Tuple[float, str]:
    """Check PEP8 compliance using pylint."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            result = subprocess.run(
                ['python3', '-m', 'pylint', '--score=y', '--output-format=text', f.name],
                capture_output=True,
                timeout=30,
                text=True
            )
            Path(f.name).unlink()

            # Extract score from pylint output
            match = re.search(r'Your code has been rated at ([\d.]+)/10', result.stdout)
            if match:
                score = float(match.group(1)) / 10.0
                return score, f"Pylint score: {match.group(1)}/10"
            return 0.7, "Style check completed (no score)"
    except Exception as e:
        return 0.5, f"Style check failed: {e}"


def grade_security(code: str) -> Tuple[float, str]:
    """Check for security vulnerabilities using bandit."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            result = subprocess.run(
                ['python3', '-m', 'bandit', '-f', 'json', f.name],
                capture_output=True,
                timeout=30,
                text=True
            )
            Path(f.name).unlink()

            import json
            try:
                report = json.loads(result.stdout)
                issues = report.get('results', [])

                if not issues:
                    return 1.0, "No security issues found"

                # Score based on severity
                high_sev = sum(1 for i in issues if i.get('issue_severity') == 'HIGH')
                med_sev = sum(1 for i in issues if i.get('issue_severity') == 'MEDIUM')
                low_sev = sum(1 for i in issues if i.get('issue_severity') == 'LOW')

                penalty = high_sev * 0.3 + med_sev * 0.15 + low_sev * 0.05
                score = max(0.0, 1.0 - penalty)
                return score, f"Found {high_sev} high, {med_sev} medium, {low_sev} low issues"
            except json.JSONDecodeError:
                return 0.8, "Security scan completed"
    except Exception as e:
        return 0.5, f"Security check failed: {e}"


def grade_complexity(code: str) -> Tuple[float, str]:
    """Evaluate code complexity."""
    try:
        tree = ast.parse(code)

        # Count complexity indicators
        num_functions = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        num_classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        num_loops = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While)))
        num_conditionals = sum(1 for node in ast.walk(tree) if isinstance(node, ast.If))
        num_try = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Try))

        lines = len([l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')])

        # Cyclomatic complexity approximation
        cyclomatic = 1 + num_conditionals + num_loops

        # Score based on reasonable thresholds
        if cyclomatic > 20:
            complexity_score = 0.4
        elif cyclomatic > 10:
            complexity_score = 0.7
        else:
            complexity_score = 1.0

        # Penalize very long functions
        if lines > 100 and num_functions <= 1:
            complexity_score *= 0.8

        return complexity_score, f"Cyclomatic: {cyclomatic}, Lines: {lines}, Functions: {num_functions}"
    except Exception as e:
        return 0.5, f"Complexity analysis failed: {e}"


def grade_maintainability(code: str) -> Tuple[float, str]:
    """Evaluate code maintainability."""
    try:
        tree = ast.parse(code)

        score = 1.0
        issues = []

        # Check for docstrings
        functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        funcs_with_docstring = sum(1 for f in functions if ast.get_docstring(f))

        if functions:
            docstring_ratio = funcs_with_docstring / len(functions)
            if docstring_ratio < 0.5:
                score -= 0.2
                issues.append(f"Only {int(docstring_ratio*100)}% functions have docstrings")

        # Check for type hints
        funcs_with_hints = sum(1 for f in functions if f.returns or f.args.args and any(a.annotation for a in f.args.args))
        if functions:
            hint_ratio = funcs_with_hints / len(functions)
            if hint_ratio < 0.5:
                score -= 0.1
                issues.append(f"Only {int(hint_ratio*100)}% functions have type hints")

        # Check variable naming (snake_case)
        names = [node.id for node in ast.walk(tree) if isinstance(node, ast.Name)]
        bad_names = [n for n in names if not re.match(r'^[a-z_][a-z0-9_]*$', n) and not n.isupper()]
        if bad_names:
            score -= 0.1
            issues.append(f"Non-standard names: {bad_names[:3]}")

        msg = "; ".join(issues) if issues else "Good maintainability"
        return max(0.0, score), msg
    except Exception as e:
        return 0.5, f"Maintainability check failed: {e}"


def grade_code(code: str, test_cases: list = None, weights: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Comprehensive code grading.

    Args:
        code: Python code to evaluate
        test_cases: Optional list of test cases [{input: [], expected: any, function: str}]
        weights: Optional custom weights for each dimension

    Returns:
        Dict with overall score and dimension breakdowns
    """
    default_weights = {
        'syntax': 0.20,
        'execution': 0.30,
        'style': 0.15,
        'security': 0.15,
        'complexity': 0.10,
        'maintainability': 0.10
    }
    weights = weights or default_weights

    results = {}

    # Run all graders
    syntax_score, syntax_msg = grade_syntax(code)
    results['syntax'] = {'score': syntax_score, 'message': syntax_msg}

    # Only continue if syntax is valid
    if syntax_score > 0:
        exec_score, exec_msg = grade_execution(code, test_cases)
        style_score, style_msg = grade_style(code)
        sec_score, sec_msg = grade_security(code)
        complex_score, complex_msg = grade_complexity(code)
        maint_score, maint_msg = grade_maintainability(code)
    else:
        exec_score = style_score = sec_score = complex_score = maint_score = 0.0
        exec_msg = style_msg = sec_msg = complex_msg = maint_msg = "Skipped due to syntax error"

    results['execution'] = {'score': exec_score, 'message': exec_msg}
    results['style'] = {'score': style_score, 'message': style_msg}
    results['security'] = {'score': sec_score, 'message': sec_msg}
    results['complexity'] = {'score': complex_score, 'message': complex_msg}
    results['maintainability'] = {'score': maint_score, 'message': maint_msg}

    # Calculate weighted overall score
    overall = sum(results[dim]['score'] * weights.get(dim, 0) for dim in results)

    return {
        'overall_score': round(overall, 3),
        'passed': overall >= 0.7,
        'dimensions': results,
        'weights': weights
    }


if __name__ == "__main__":
    # Test the grader
    test_code = '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    for i in range(10):
        print(f"fib({i}) = {fibonacci(i)}")

if __name__ == "__main__":
    main()
'''

    result = grade_code(test_code)
    print(f"Overall Score: {result['overall_score']}")
    print(f"Passed: {result['passed']}")
    for dim, data in result['dimensions'].items():
        print(f"  {dim}: {data['score']:.2f} - {data['message']}")
