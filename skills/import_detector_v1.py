"""Code analysis: detect imports"""

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
