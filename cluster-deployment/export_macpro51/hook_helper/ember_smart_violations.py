#!/usr/bin/env python3
"""
Smart Context-Aware Ember Violation Detection
Version 2.0 - Significantly reduced false positives

Key improvements:
1. Context-aware: Distinguishes documentation examples from placeholder code
2. Implementation verification: Checks for actual incomplete patterns
3. Whitelist support: Known production patterns that are safe
4. Multi-factor scoring: Multiple indicators needed for violation
"""

import re
import ast
from typing import Optional, Dict, List, Tuple

class SmartViolationDetector:
    """Context-aware violation detection with reduced false positives"""

    # Whitelist: Patterns that are always safe
    SAFE_PATTERNS = [
        r'""".*?Example.*?"""',  # Docstring examples
        r"'''.*?Example.*?'''",  # Docstring examples
        r'#.*Example',           # Comment examples
        r'Example usage:',       # Documentation
        r'Example output:',      # Documentation
        r'For example:',         # Documentation
        r'\.example\.',          # .example.com or similar
    ]

    # High-confidence violation indicators
    STRONG_VIOLATIONS = {
        "fake_ui": [
            (r'hardcoded.*notification.*=.*\[', "Hardcoded notification array"),
            (r'const.*dummy.*=.*\{', "Dummy data object"),
            (r'mock_api.*=', "Mock API assignment"),
            (r'PLACEHOLDER_.*=', "Placeholder constant"),
            (r'lorem ipsum', "Lorem ipsum text"),
        ],
        "incomplete_implementation": [
            (r'^\s*pass\s*$', "Empty pass statement"),
            (r'^\s*\.\.\.\s*$', "Ellipsis placeholder"),
            (r'raise NotImplementedError', "Not implemented"),
            (r'def\s+\w+\([^)]*\):\s*pass', "Empty function"),
            (r'TODO:.*missing', "TODO for missing functionality"),
            (r'FIXME:.*implement', "FIXME for implementation"),
        ],
        "mock_data": [
            (r'static.*dashboard.*data\s*=\s*\[', "Static dashboard data"),
            (r'hard.*coded.*values\s*=\s*\[', "Hard coded values array"),
        ]
    }

    # Weak indicators (need multiple to trigger)
    WEAK_INDICATORS = [
        (r'\bPOC\b', "POC reference", 1),
        (r'proof.*of.*concept', "Proof of concept", 1),
        (r'demo.*implementation', "Demo implementation", 1),
        (r'\bexample\b.*\bcode\b', "Example code (weak)", 0.5),
        (r'for testing purposes', "Testing purpose", 0.5),
    ]

    def __init__(self):
        self.compiled_safe = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.SAFE_PATTERNS]

    def is_in_safe_context(self, content: str, match_pos: int) -> bool:
        """Check if a match position is within a safe context (docstring/comment)"""
        # Get surrounding context (500 chars before and after)
        start = max(0, match_pos - 500)
        end = min(len(content), match_pos + 500)
        context = content[start:end]

        # Check if match is in docstring
        for safe_pattern in self.compiled_safe:
            if safe_pattern.search(context):
                return True

        # Check if match is in a comment line
        lines = content[:match_pos].split('\n')
        if lines:
            last_line = lines[-1].strip()
            if last_line.startswith('#'):
                return True

        return False

    def check_python_completeness(self, content: str) -> Tuple[bool, str]:
        """
        Verify Python code is complete using AST analysis
        Returns: (is_complete, reason)
        """
        try:
            tree = ast.parse(content)

            # Check for functions with only pass/ellipsis
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Function with only pass statement
                    if len(node.body) == 1:
                        if isinstance(node.body[0], ast.Pass):
                            return False, f"Empty function: {node.name}"
                        if isinstance(node.body[0], ast.Expr):
                            if isinstance(node.body[0].value, ast.Constant):
                                if node.body[0].value.value == Ellipsis:
                                    return False, f"Ellipsis placeholder in: {node.name}"

                # Check for raise NotImplementedError
                if isinstance(node, ast.Raise):
                    if isinstance(node.exc, ast.Call):
                        if isinstance(node.exc.func, ast.Name):
                            if node.exc.func.id == "NotImplementedError":
                                return False, "NotImplementedError found"

            return True, "Python code appears complete"

        except SyntaxError:
            # Can't parse - might be partial code or not Python
            return True, "Unable to parse (not blocking)"

    def check_error_handling_present(self, content: str) -> bool:
        """Check if code has error handling (try/except blocks)"""
        try:
            tree = ast.parse(content)

            # Look for try/except blocks
            for node in ast.walk(tree):
                if isinstance(node, ast.Try):
                    return True

            # If code is very short (< 10 lines), error handling not required
            if content.count('\n') < 10:
                return True

            return False
        except:
            # Can't parse, give benefit of doubt
            return True

    def calculate_violation_score(self, content: str, tool_name: str) -> Tuple[float, List[str]]:
        """
        Calculate violation score with context awareness
        Returns: (score, reasons)

        Score interpretation:
        - 0.0-2.0: Safe (allow)
        - 2.0-4.0: Suspicious (warn but allow)
        - 4.0+: Violation (block)
        """
        score = 0.0
        reasons = []

        # Check for strong violations first
        for violation_type, patterns in self.STRONG_VIOLATIONS.items():
            for pattern, description in patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                for match in matches:
                    # Skip if in safe context
                    if self.is_in_safe_context(content, match.start()):
                        continue

                    score += 5.0  # Strong violation
                    reasons.append(f"{description} (line near {content[:match.start()].count('\n') + 1})")

        # Check weak indicators (need multiple)
        for pattern, description, weight in self.WEAK_INDICATORS:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                # Skip if in safe context
                if self.is_in_safe_context(content, match.start()):
                    continue

                score += weight
                reasons.append(f"{description} (weak indicator)")

        # For Python code, check completeness
        if tool_name in ["Write", "Edit", "MultiEdit"]:
            is_complete, reason = self.check_python_completeness(content)
            if not is_complete:
                score += 5.0
                reasons.append(f"Python incompleteness: {reason}")

            # Check for error handling (only add small weight if missing)
            if not self.check_error_handling_present(content):
                # Only flag if code is substantial (>50 lines) and no try/except
                if content.count('\n') > 50:
                    score += 1.0
                    reasons.append("Large code block with no error handling (weak)")

        return score, reasons

    def check_content(self, content: str, tool_name: str) -> Optional[Dict]:
        """
        Check content for violations with smart detection

        Returns:
            Dict with violation info if found, None otherwise
        """
        if not content or len(content.strip()) < 10:
            return None

        score, reasons = self.calculate_violation_score(content, tool_name)

        # Threshold: 4.0+ is a violation
        if score >= 4.0:
            return {
                "type": "smart_violation_detected",
                "severity": "severe" if score >= 8.0 else "moderate",
                "message": f"Production policy violation detected (score: {score:.1f})",
                "reasons": reasons,
                "score": score,
                "tool": tool_name
            }

        return None

# Global detector instance
_detector = None

def get_detector() -> SmartViolationDetector:
    """Get or create global detector instance"""
    global _detector
    if _detector is None:
        _detector = SmartViolationDetector()
    return _detector

def check_smart_violations(tool_name: str, tool_args: dict) -> Optional[Dict]:
    """
    Smart violation check with context awareness

    Args:
        tool_name: Name of the tool being called
        tool_args: Arguments passed to the tool

    Returns:
        Dict with violation info if found, None otherwise
    """
    detector = get_detector()

    # Extract content based on tool type
    content = ""
    if tool_name == "Write":
        content = tool_args.get("content", "")
    elif tool_name == "Edit":
        # Check both old and new strings
        old = tool_args.get("old_string", "")
        new = tool_args.get("new_string", "")
        content = f"{old}\n{new}"
    elif tool_name == "MultiEdit":
        edits = tool_args.get("edits", [])
        content = "\n".join([
            f"{e.get('old_string', '')}\n{e.get('new_string', '')}"
            for e in edits
        ])

    if not content:
        return None

    return detector.check_content(content, tool_name)
