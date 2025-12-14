#!/usr/bin/env python3
"""
Code Execution MCP Server

Implements the patterns from Anthropic's "Code Execution with MCP" article:
- Progressive tool discovery (load definitions on-demand)
- Sandboxed code execution (process data locally, not in context)
- PII tokenization (privacy-preserving operations)
- Skills persistence (reusable agent capabilities)

This reduces token usage by up to 98% compared to direct tool invocation.
"""
import platform

import json
import os
import re
import hashlib
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from functools import wraps
import resource
import signal

from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("code-execution")

# Configuration
WORKSPACE_DIR = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "mcp-servers/code-execution-mcp/workspace"))
SKILLS_DIR = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "mcp-servers/code-execution-mcp/skills"))
TOOLS_REGISTRY_DIR = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "mcp-servers/code-execution-mcp/tools_registry"))

# Ensure directories exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
TOOLS_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

# PII patterns for tokenization
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'api_key': r'\b(?:api[_-]?key|token|secret)[=:\s]+[A-Za-z0-9_-]{20,}\b',
}

# Token storage for PII
_pii_tokens = {}


def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")


class SafeExecutionContext:
    """Context manager for safe code execution with resource limits."""

    def __init__(self, timeout_seconds: int = 30, memory_mb: int = 500):
        self.timeout = timeout_seconds
        self.memory_limit = memory_mb * 1024 * 1024
        self.old_handler = None

    def __enter__(self):
        # Set timeout
        self.old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)

        # Set memory limit
        try:
            resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
        except (ValueError, resource.error):
            pass  # May not be supported on all systems

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
        if self.old_handler:
            signal.signal(signal.SIGALRM, self.old_handler)
        return False


def create_safe_builtins():
    """Create a restricted set of builtins for sandboxed execution."""
    safe_builtins = {
        # Safe built-in functions
        'abs': abs, 'all': all, 'any': any, 'ascii': ascii,
        'bin': bin, 'bool': bool, 'bytes': bytes, 'callable': callable,
        'chr': chr, 'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
        'filter': filter, 'float': float, 'format': format, 'frozenset': frozenset,
        'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
        'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
        'map': map, 'max': max, 'min': min, 'next': next, 'object': object,
        'oct': oct, 'ord': ord, 'pow': pow, 'print': print, 'range': range,
        'repr': repr, 'reversed': reversed, 'round': round, 'set': set,
        'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
        'tuple': tuple, 'type': type, 'zip': zip,

        # Exceptions
        'Exception': Exception, 'ValueError': ValueError, 'TypeError': TypeError,
        'KeyError': KeyError, 'IndexError': IndexError, 'AttributeError': AttributeError,
        'RuntimeError': RuntimeError, 'StopIteration': StopIteration,

        # Constants
        'True': True, 'False': False, 'None': None,
    }
    return safe_builtins


def create_safe_globals(workspace_path: Path, context_vars: dict = None):
    """Create safe global namespace for code execution."""
    import json as json_module
    import re as re_module
    import math
    import statistics
    import collections
    from datetime import datetime, date, timedelta

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


    safe_globals = {
        '__builtins__': create_safe_builtins(),

        # Safe modules
        'json': json_module,
        're': re_module,
        'math': math,
        'statistics': statistics,
        'collections': collections,
        'datetime': datetime,
        'date': date,
        'timedelta': timedelta,

        # Workspace utilities
        'workspace': str(workspace_path),
        'read_file': lambda f: _safe_read_file(workspace_path, f),
        'write_file': lambda f, c: _safe_write_file(workspace_path, f, c),
        'list_files': lambda p='.': _safe_list_files(workspace_path, p),
        'delete_file': lambda f: _safe_delete_file(workspace_path, f),

        # Skills utilities
        'save_skill': save_skill_internal,
        'load_skill': load_skill_internal,
        'list_skills': list_skills_internal,

        # PII utilities
        'tokenize_pii': tokenize_pii,
        'detokenize_pii': detokenize_pii,

        # Data processing utilities
        'filter_by_field': lambda data, field, value: [d for d in data if d.get(field) == value],
        'summarize_list': lambda data, limit=10: {'count': len(data), 'sample': data[:limit]},
        'aggregate_stats': _aggregate_stats,
        'format_output': lambda data, max_chars=5000: json_module.dumps(data, indent=2)[:max_chars],
    }

    # Add context variables if provided
    if context_vars:
        safe_globals.update(context_vars)

    return safe_globals


def _safe_read_file(workspace: Path, filename: str) -> str:
    """Safely read a file from workspace."""
    path = (workspace / filename).resolve()
    if not str(path).startswith(str(workspace)):
        raise PermissionError("Access denied: path outside workspace")
    if path.exists():
        return path.read_text()
    raise FileNotFoundError(f"File not found: {filename}")


def _safe_write_file(workspace: Path, filename: str, content: str) -> str:
    """Safely write a file to workspace."""
    path = (workspace / filename).resolve()
    if not str(path).startswith(str(workspace)):
        raise PermissionError("Access denied: path outside workspace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"Written {len(content)} bytes to {filename}"


def _safe_list_files(workspace: Path, subpath: str = '.') -> list:
    """Safely list files in workspace."""
    path = (workspace / subpath).resolve()
    if not str(path).startswith(str(workspace)):
        raise PermissionError("Access denied: path outside workspace")
    if path.is_dir():
        return [str(f.relative_to(workspace)) for f in path.rglob('*') if f.is_file()]
    return []


def _safe_delete_file(workspace: Path, filename: str) -> str:
    """Safely delete a file from workspace."""
    path = (workspace / filename).resolve()
    if not str(path).startswith(str(workspace)):
        raise PermissionError("Access denied: path outside workspace")
    if path.exists():
        path.unlink()
        return f"Deleted {filename}"
    raise FileNotFoundError(f"File not found: {filename}")


def _aggregate_stats(data: list, numeric_fields: list = None) -> dict:
    """Aggregate statistics for numeric fields in data."""
    if not data:
        return {'count': 0}

    result = {'count': len(data)}

    if numeric_fields is None:
        # Auto-detect numeric fields
        if isinstance(data[0], dict):
            numeric_fields = [k for k, v in data[0].items() if isinstance(v, (int, float))]

    if numeric_fields:
        for field in numeric_fields:
            values = [d.get(field, 0) for d in data if isinstance(d, dict)]
            if values:
                result[f'{field}_sum'] = sum(values)
                result[f'{field}_avg'] = sum(values) / len(values)
                result[f'{field}_min'] = min(values)
                result[f'{field}_max'] = max(values)

    return result


def tokenize_pii(text: str) -> tuple[str, dict]:
    """
    Tokenize PII in text, returning sanitized text and token map.

    Privacy-preserving: PII stays in sandbox, only tokens reach the model.
    """
    tokens = {}
    sanitized = text

    for pii_type, pattern in PII_PATTERNS.items():
        for match in re.finditer(pattern, sanitized, re.IGNORECASE):
            original = match.group()
            token_id = f"[{pii_type.upper()}_{hashlib.md5(original.encode()).hexdigest()[:8]}]"
            tokens[token_id] = original
            sanitized = sanitized.replace(original, token_id)

    # Store tokens for later detokenization
    _pii_tokens.update(tokens)

    return sanitized, tokens


def detokenize_pii(text: str, tokens: dict = None) -> str:
    """Restore PII from tokens."""
    if tokens is None:
        tokens = _pii_tokens

    result = text
    for token, original in tokens.items():
        result = result.replace(token, original)

    return result


def save_skill_internal(name: str, code: str, description: str = "") -> str:
    """Save a reusable skill (code function) for future use."""
    skill_path = SKILLS_DIR / f"{name}.py"
    metadata_path = SKILLS_DIR / f"{name}.json"

    skill_path.write_text(code)
    metadata = {
        'name': name,
        'description': description,
        'created': datetime.now().isoformat(),
        'code_hash': hashlib.md5(code.encode()).hexdigest(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return f"Skill '{name}' saved successfully"


def load_skill_internal(name: str) -> str:
    """Load a saved skill's code."""
    skill_path = SKILLS_DIR / f"{name}.py"
    if skill_path.exists():
        return skill_path.read_text()
    raise FileNotFoundError(f"Skill not found: {name}")


def list_skills_internal() -> list:
    """List all saved skills."""
    skills = []
    for meta_file in SKILLS_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            skills.append(meta)
        except:
            pass
    return skills


# =============================================================================
# Tool Registry for Progressive Discovery
# =============================================================================

CATALOG_FILE = TOOLS_REGISTRY_DIR / "full_catalog.json"
_catalog_cache = None


def get_catalog():
    """Load and cache the tool catalog."""
    global _catalog_cache
    if _catalog_cache is None and CATALOG_FILE.exists():
        _catalog_cache = json.loads(CATALOG_FILE.read_text())
    return _catalog_cache or {"categories": {}}


def search_catalog(query: str, category: str = None) -> list:
    """Search the tool catalog."""
    catalog = get_catalog()
    results = []
    query_lower = query.lower()

    for cat_name, cat_data in catalog.get("categories", {}).items():
        if category and cat_name != category:
            continue

        for tool_name, tool_data in cat_data.get("tools", {}).items():
            # Build searchable text
            searchable = f"{tool_name} {tool_data.get('description', '')} {' '.join(tool_data.get('functions', []))} {' '.join(tool_data.get('use_cases', []))}".lower()

            if query_lower in searchable:
                results.append({
                    "name": tool_name,
                    "category": cat_name,
                    "mcp_server": tool_data.get("mcp_server"),
                    "description": tool_data.get("description"),
                    "functions": tool_data.get("functions", []),
                    "use_cases": tool_data.get("use_cases", [])
                })

    return results


def get_tool_from_catalog(tool_name: str) -> dict:
    """Get full tool definition from catalog."""
    catalog = get_catalog()

    for cat_name, cat_data in catalog.get("categories", {}).items():
        if tool_name in cat_data.get("tools", {}):
            tool = cat_data["tools"][tool_name].copy()
            tool["category"] = cat_name
            return tool

    return None


def list_categories() -> dict:
    """List all tool categories with descriptions."""
    catalog = get_catalog()
    return {
        cat: {
            "description": data.get("description", ""),
            "tool_count": len(data.get("tools", {}))
        }
        for cat, data in catalog.get("categories", {}).items()
    }


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
def execute_code(
    code: str,
    context_vars: dict = None,
    timeout_seconds: int = 30,
    memory_mb: int = 500
) -> str:
    """
    Execute Python code in a secure sandbox.

    The sandbox provides:
    - Resource limits (timeout, memory)
    - Restricted builtins (no file system access outside workspace)
    - Safe modules (json, re, math, datetime, etc.)
    - Workspace file utilities (read_file, write_file, list_files)
    - PII tokenization (tokenize_pii, detokenize_pii)
    - Skills persistence (save_skill, load_skill, list_skills)

    Token Efficiency Pattern:
    - Process large datasets in the sandbox
    - Return only summarized/filtered results
    - Use write_file to persist intermediate state

    Example:
        # Instead of returning 10,000 rows to context:
        data = json.loads(read_file("large_data.json"))
        filtered = [d for d in data if d['status'] == 'active']
        result = summarize_list(filtered, limit=5)

    Args:
        code: Python code to execute
        context_vars: Additional variables to make available
        timeout_seconds: Maximum execution time (default: 30)
        memory_mb: Memory limit in MB (default: 500)

    Returns:
        JSON with execution result, output, and any errors
    """
    start_time = time.time()
    output = []

    # Create custom print that captures output
    def capture_print(*args, **kwargs):
        output.append(' '.join(str(a) for a in args))

    try:
        # Prepare execution environment
        safe_globals = create_safe_globals(WORKSPACE_DIR, context_vars)
        safe_globals['print'] = capture_print

        # Execute with resource limits
        with SafeExecutionContext(timeout_seconds, memory_mb):
            exec(compile(code, '<sandbox>', 'exec'), safe_globals)

        # Get result if defined
        result = safe_globals.get('result', None)

        return json.dumps({
            'success': True,
            'result': result,
            'output': output,
            'execution_time_ms': int((time.time() - start_time) * 1000),
        }, indent=2, default=str)

    except TimeoutError:
        return json.dumps({
            'success': False,
            'error': f'Execution timed out after {timeout_seconds} seconds',
            'output': output,
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'output': output,
        })


@mcp.tool()
def search_tools(
    query: str,
    category: str = None,
    detail_level: str = "summary"
) -> str:
    """
    Progressive tool discovery - find tools without loading all definitions.

    This implements the "progressive disclosure" pattern from the Anthropic article.
    Instead of loading 150K+ tokens of tool definitions upfront, agents can:
    1. Search for relevant tools by query
    2. Get summaries first (minimal tokens)
    3. Load full definitions only when needed

    Token savings: ~98.7% compared to loading all tools upfront

    Args:
        query: Search term (matches name, description, functions, use_cases)
        category: Filter by category (security, memory, agents, communication, research, media)
        detail_level: "summary" (name+description) or "full" (include all details)

    Returns:
        JSON with matching tools at requested detail level
    """
    results = search_catalog(query, category)

    if detail_level == "summary":
        results = [
            {"name": r["name"], "category": r["category"], "description": r["description"], "mcp_server": r["mcp_server"]}
            for r in results
        ]

    return json.dumps({
        'query': query,
        'category': category,
        'detail_level': detail_level,
        'count': len(results),
        'tools': results,
    }, indent=2)


@mcp.tool()
def get_tool_definition(tool_name: str, category: str = None) -> str:
    """
    Get full definition for a specific tool.

    Use this after search_tools to load complete details for a tool you want to use.

    Args:
        tool_name: Name of the tool
        category: Category to search in (optional, searches all if not provided)

    Returns:
        JSON with full tool definition including functions and use cases
    """
    tool = get_tool_from_catalog(tool_name)
    if tool:
        return json.dumps(tool, indent=2)


@mcp.tool()
def list_tool_categories() -> str:
    """
    List all available tool categories.

    Use this to understand what types of tools are available before searching.

    Returns:
        JSON with categories, descriptions, and tool counts
    """
    categories = list_categories()
    catalog = get_catalog()

    return json.dumps({
        'categories': categories,
        'total_tools': catalog.get('total_tools', 0),
        'core_mcps': catalog.get('core_mcps', []),
    }, indent=2)


@mcp.tool()
def save_skill(name: str, code: str, description: str = "") -> str:
    """
    Save a reusable skill (code snippet) for future use.

    Skills are high-level capabilities that agents build over time.
    They persist across sessions and can be loaded by execute_code.

    Example:
        save_skill(
            name="filter_active_users",
            code="def filter_active(data): return [u for u in data if u['status'] == 'active']",
            description="Filter list to only active users"
        )

    Args:
        name: Skill name (alphanumeric and underscores)
        code: Python code defining the skill
        description: Human-readable description

    Returns:
        JSON confirmation
    """
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        return json.dumps({'error': 'Invalid skill name. Use alphanumeric and underscores only.'})

    result = save_skill_internal(name, code, description)
    return json.dumps({'success': True, 'message': result})


@mcp.tool()
def load_skill(name: str) -> str:
    """
    Load a saved skill's code.

    Args:
        name: Skill name to load

    Returns:
        JSON with skill code and metadata
    """
    try:
        code = load_skill_internal(name)
        metadata_path = SKILLS_DIR / f"{name}.json"
        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())

        return json.dumps({
            'name': name,
            'code': code,
            'metadata': metadata,
        }, indent=2)
    except FileNotFoundError as e:
        return json.dumps({'error': str(e)})


@mcp.tool()
def list_skills() -> str:
    """
    List all saved skills.

    Returns:
        JSON with skill names and descriptions
    """
    skills = list_skills_internal()
    return json.dumps({
        'count': len(skills),
        'skills': skills,
    }, indent=2)


@mcp.tool()
def sanitize_pii(text: str) -> str:
    """
    Tokenize PII in text for privacy-preserving operations.

    This implements the privacy pattern from the Anthropic article:
    - PII is detected and replaced with tokens
    - Tokens can be restored later with detokenize
    - Prevents sensitive data from entering model context

    Detected PII types:
    - Email addresses
    - Phone numbers
    - SSNs
    - Credit card numbers
    - IP addresses
    - API keys

    Args:
        text: Text potentially containing PII

    Returns:
        JSON with sanitized text and token count
    """
    sanitized, tokens = tokenize_pii(text)

    return json.dumps({
        'sanitized_text': sanitized,
        'pii_found': len(tokens),
        'pii_types': list(set(t.split('_')[0].strip('[') for t in tokens.keys())),
    }, indent=2)


@mcp.tool()
def restore_pii(text: str) -> str:
    """
    Restore tokenized PII back to original values.

    Args:
        text: Text with PII tokens

    Returns:
        JSON with restored text
    """
    restored = detokenize_pii(text)
    return json.dumps({
        'restored_text': restored,
    }, indent=2)


@mcp.tool()
def write_workspace_file(filename: str, content: str) -> str:
    """
    Write a file to the sandbox workspace.

    Use this to persist intermediate results between code executions.

    Args:
        filename: File path relative to workspace
        content: File content

    Returns:
        JSON confirmation
    """
    try:
        result = _safe_write_file(WORKSPACE_DIR, filename, content)
        return json.dumps({'success': True, 'message': result})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@mcp.tool()
def read_workspace_file(filename: str) -> str:
    """
    Read a file from the sandbox workspace.

    Args:
        filename: File path relative to workspace

    Returns:
        JSON with file content
    """
    try:
        content = _safe_read_file(WORKSPACE_DIR, filename)
        return json.dumps({
            'success': True,
            'filename': filename,
            'content': content,
            'size': len(content),
        }, indent=2)
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@mcp.tool()
def list_workspace_files(subpath: str = ".") -> str:
    """
    List files in the sandbox workspace.

    Args:
        subpath: Subdirectory to list (default: root)

    Returns:
        JSON with file listing
    """
    try:
        files = _safe_list_files(WORKSPACE_DIR, subpath)
        return json.dumps({
            'success': True,
            'path': subpath,
            'files': files,
            'count': len(files),
        }, indent=2)
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@mcp.tool()
def get_execution_stats() -> str:
    """
    Get statistics about the code execution environment.

    Returns:
        JSON with workspace size, skill count, and capabilities
    """
    workspace_files = list(_safe_list_files(WORKSPACE_DIR, '.'))
    skills = list_skills_internal()

    # Count tool definitions
    tool_count = 0
    categories = []
    for category_dir in TOOLS_REGISTRY_DIR.iterdir():
        if category_dir.is_dir():
            categories.append(category_dir.name)
            tool_count += len(list(category_dir.glob("*.json")))

    return json.dumps({
        'workspace': {
            'path': str(WORKSPACE_DIR),
            'file_count': len(workspace_files),
        },
        'skills': {
            'count': len(skills),
            'path': str(SKILLS_DIR),
        },
        'tool_registry': {
            'categories': categories,
            'total_tools': tool_count,
        },
        'capabilities': [
            'sandboxed_execution',
            'progressive_tool_discovery',
            'pii_tokenization',
            'skills_persistence',
            'workspace_files',
        ],
        'limits': {
            'default_timeout_seconds': 30,
            'default_memory_mb': 500,
        },
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
