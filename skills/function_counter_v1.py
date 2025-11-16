"""Code analysis: count functions"""

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
