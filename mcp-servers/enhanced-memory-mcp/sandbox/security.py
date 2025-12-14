"""
Security Layer for Code Execution

Provides:
- PII tokenization (SSN, email, credit cards, phone, IP addresses)
- Code safety validation
- Dangerous pattern detection
"""

import re
from typing import Any, Dict, List, Tuple, Optional


PII_PATTERNS = {
    'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),
    'email': (r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', '[EMAIL]'),
    'credit_card': (r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD]'),
    'phone': (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
    'ip_address': (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]'),
    'api_key': (r'\b[A-Za-z0-9]{32,}\b', '[APIKEY]'),
}


DANGEROUS_IMPORTS = [
    'os', 'subprocess', 'sys', 'socket', 'urllib', 'requests', 'http',
    'shutil', 'tempfile', 'pathlib', 'pickle', 'marshal', 'ctypes',
    '__import__', 'importlib', 'imp'
]


DANGEROUS_FUNCTIONS = [
    'eval', 'exec', 'compile', 'open', 'file', 'input', 'raw_input',
    '__import__', 'getattr', 'setattr', 'delattr', 'hasattr',
    'globals', 'locals', 'vars', 'dir'
]


DANGEROUS_KEYWORDS = [
    '__builtins__', '__dict__', '__class__', '__bases__', '__subclasses__',
    '__mro__', '__code__', '__globals__', '__closure__'
]


def tokenize_pii(data: Any) -> Any:
    """Recursively tokenize PII in data structures."""
    if isinstance(data, str):
        return tokenize_pii_string(data)
    elif isinstance(data, dict):
        return {k: tokenize_pii(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [tokenize_pii(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(tokenize_pii(item) for item in data)
    else:
        return data


def tokenize_pii_string(text: str) -> str:
    """Replace PII patterns in string with tokens."""
    for pattern_name, (pattern, replacement) in PII_PATTERNS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def validate_code_safety(code: str) -> Tuple[bool, str]:
    """Validate code is safe to execute."""

    dangerous_imports_found = []
    for imp in DANGEROUS_IMPORTS:
        if re.search(rf'\b(import|from)\s+{re.escape(imp)}\b', code):
            dangerous_imports_found.append(imp)

    if dangerous_imports_found:
        return False, f"Dangerous imports detected: {', '.join(dangerous_imports_found)}"

    dangerous_functions_found = []
    for func in DANGEROUS_FUNCTIONS:
        if re.search(rf'\b{re.escape(func)}\s*\(', code):
            dangerous_functions_found.append(func)

    if dangerous_functions_found:
        return False, f"Dangerous functions detected: {', '.join(dangerous_functions_found)}"

    dangerous_keywords_found = []
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in code:
            dangerous_keywords_found.append(keyword)

    if dangerous_keywords_found:
        return False, f"Dangerous keywords detected: {', '.join(dangerous_keywords_found)}"

    if re.search(r'\bfile\s*\(', code) or re.search(r'\bopen\s*\(', code):
        return False, "File operations not allowed"

    return True, "Code appears safe"


def sanitize_output(data: Any) -> Any:
    """Sanitize output by tokenizing PII and limiting size."""
    tokenized = tokenize_pii(data)

    if isinstance(tokenized, str) and len(tokenized) > 100000:
        return tokenized[:100000] + "... [TRUNCATED]"
    elif isinstance(tokenized, (list, tuple)) and len(tokenized) > 1000:
        return type(tokenized)(list(tokenized)[:1000])
    elif isinstance(tokenized, dict) and len(tokenized) > 1000:
        limited = dict(list(tokenized.items())[:1000])
        limited['__truncated__'] = True
        return limited

    return tokenized


def check_resource_safety(code: str) -> Tuple[bool, str]:
    """Check for resource-intensive operations."""

    if re.search(r'\bwhile\s+True\b', code):
        return False, "Infinite loops detected"

    if re.search(r'\bfor\s+\w+\s+in\s+range\s*\(\s*\d{7,}', code):
        return False, "Very large range detected"

    recursion_patterns = [
        r'def\s+(\w+)\s*\([^)]*\):[^}]+\1\s*\('
    ]
    for pattern in recursion_patterns:
        if re.search(pattern, code):
            return False, "Potential unbounded recursion detected"

    return True, "Resource usage appears safe"


def comprehensive_safety_check(code: str) -> Tuple[bool, List[str]]:
    """Run all safety checks and return combined results."""
    issues = []

    is_safe, msg = validate_code_safety(code)
    if not is_safe:
        issues.append(msg)

    is_safe, msg = check_resource_safety(code)
    if not is_safe:
        issues.append(msg)

    if issues:
        return False, issues

    return True, []
