"""Code analysis: measure complexity metrics"""

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
