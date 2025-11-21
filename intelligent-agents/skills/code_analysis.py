"""
Code Analysis Skills
===================

Production-ready code analysis utilities.
"""

import ast
from typing import List, Dict, Any


def complexity_analyzer(code: str) -> Dict[str, int]:
    """
    Analyze code complexity.

    Args:
        code: Python code string

    Returns:
        Dict with complexity metrics
    """
    try:
        tree = ast.parse(code)

        metrics = {
            "functions": sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)),
            "classes": sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)),
            "lines": len(code.splitlines()),
            "imports": sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
        }

        return metrics
    except SyntaxError:
        return {"error": "Invalid Python code"}


def import_detector(code: str) -> List[str]:
    """
    Detect all imports in code.

    Args:
        code: Python code string

    Returns:
        List of imported module names
    """
    try:
        tree = ast.parse(code)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module if node.module else "")

        return imports
    except SyntaxError:
        return []


def function_counter(code: str) -> int:
    """
    Count number of functions in code.

    Args:
        code: Python code string

    Returns:
        Number of functions
    """
    try:
        tree = ast.parse(code)
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    except SyntaxError:
        return 0
