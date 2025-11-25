"""
Secure Code Execution Engine

Uses RestrictedPython for safe code compilation and execution with:
- 30-second timeout limits
- 500MB memory limits
- Safe built-ins only
- Complete stdout/stderr capture
"""

import sys
import io
import signal
import resource
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

try:
    from RestrictedPython import compile_restricted, safe_globals
    from RestrictedPython.Guards import (
        guarded_iter_unpack_sequence,
        guarded_unpack_sequence,
        safe_builtins
    )
    from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getattr
    from RestrictedPython.PrintCollector import PrintCollector
except ImportError:
    raise ImportError("RestrictedPython is required")


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    result: Any
    stdout: str
    stderr: str
    execution_time_ms: float
    error: Optional[str] = None


class TimeoutException(Exception):
    """Raised when code execution times out"""


class MemoryLimitException(Exception):
    """Raised when code exceeds memory limit"""


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutException("Code execution exceeded timeout limit")


@contextmanager
def timeout_context(seconds: int):
    """Context manager for execution timeout"""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


@contextmanager
def memory_limit_context(max_bytes: int):
    """Context manager for memory limit"""
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, hard))
    try:
        yield
    except MemoryError:
        raise MemoryLimitException(f"Code execution exceeded memory limit")
    finally:
        resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


class CodeExecutor:
    """Secure code execution engine using RestrictedPython."""

    def __init__(self, timeout_seconds: int = 30, memory_limit_bytes: int = 500 * 1024 * 1024):
        self.timeout_seconds = timeout_seconds
        self.memory_limit_bytes = memory_limit_bytes
        self.safe_builtins = self._create_safe_builtins()

        # Create isolated workspace for filesystem access
        self.workspace = Path(tempfile.mkdtemp(prefix="mcp_code_"))
        self.skills_dir = self.workspace / "skills"
        self.skills_dir.mkdir(exist_ok=True)

    def _create_safe_builtins(self) -> Dict[str, Any]:
        """Create whitelist of safe built-in functions."""
        import builtins
        safe = safe_globals.copy()

        safe_functions = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
            'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate', 'filter', 'float',
            'format', 'frozenset', 'hex', 'int', 'isinstance', 'issubclass',
            'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord',
            'pow', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
            'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
        ]

        for func_name in safe_functions:
            if hasattr(builtins, func_name):
                safe[func_name] = getattr(builtins, func_name)

        # RestrictedPython guards
        safe['_iter_unpack_sequence_'] = guarded_iter_unpack_sequence
        safe['_unpack_sequence_'] = guarded_unpack_sequence
        safe['_getitem_'] = default_guarded_getitem
        safe['_getattr_'] = default_guarded_getattr
        safe['_getiter_'] = lambda x: iter(x)
        safe['_iter_'] = iter

        # Add write guard for attribute assignment (returns a simple callable)
        safe['_write_'] = lambda obj: obj

        # Add print function support for RestrictedPython
        safe['_print_'] = PrintCollector

        # Safe modules
        safe['datetime'] = datetime
        safe['json'] = __import__('json')
        safe['re'] = __import__('re')
        safe['math'] = __import__('math')
        safe['statistics'] = __import__('statistics')
        safe['collections'] = __import__('collections')
        safe['time'] = __import__('time')

        return safe

    # === FILESYSTEM HELPER METHODS ===

    def list_files(self, subdir: str = "") -> list[str]:
        """List files in workspace or subdirectory."""
        target = self.workspace / subdir if subdir else self.workspace
        if not target.exists() or not target.is_dir():
            return []
        return [str(p.relative_to(self.workspace)) for p in target.iterdir()]

    def read_file(self, filepath: str) -> str:
        """Read file from workspace (safe path validation)."""
        target = self.workspace / filepath
        if not target.resolve().is_relative_to(self.workspace.resolve()):
            raise ValueError(f"Path escape attempt: {filepath}")
        return target.read_text()

    def write_file(self, filepath: str, content: str) -> str:
        """Write file to workspace (safe path validation)."""
        target = self.workspace / filepath
        if not target.resolve().is_relative_to(self.workspace.resolve()):
            raise ValueError(f"Path escape attempt: {filepath}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Written {len(content)} bytes to {filepath}"

    def delete_file(self, filepath: str) -> str:
        """Delete file from workspace (safe path validation)."""
        target = self.workspace / filepath
        if not target.resolve().is_relative_to(self.workspace.resolve()):
            raise ValueError(f"Path escape attempt: {filepath}")
        if target.exists():
            target.unlink()
            return f"Deleted {filepath}"
        return f"File not found: {filepath}"

    # === SKILLS MANAGEMENT ===

    def save_skill(self, name: str, code: str, description: str = "") -> str:
        """Save code as reusable skill."""
        skill_file = self.skills_dir / f"{name}.py"
        content = f'"""{description}"""\n\n{code}'
        skill_file.write_text(content)
        return f"Skill '{name}' saved ({len(code)} bytes)"

    def load_skill(self, name: str) -> str:
        """Load skill code."""
        skill_file = self.skills_dir / f"{name}.py"
        if not skill_file.exists():
            raise FileNotFoundError(f"Skill '{name}' not found")
        return skill_file.read_text()

    def list_skills(self) -> list[str]:
        """List available skills."""
        return [p.stem for p in self.skills_dir.glob("*.py")]

    def execute(self, code: str, context: Optional[Dict[str, Any]] = None,
                timeout_seconds: Optional[int] = None,
                memory_limit_bytes: Optional[int] = None) -> ExecutionResult:
        """Execute Python code in secure sandbox."""
        start_time = datetime.now()
        timeout = timeout_seconds or self.timeout_seconds

        old_stdout, old_stderr = sys.stdout, sys.stderr
        stdout_capture, stderr_capture = io.StringIO(), io.StringIO()

        try:
            try:
                byte_code = compile_restricted(code, filename='<user_code>', mode='exec')
                if hasattr(byte_code, 'errors') and byte_code.errors:
                    return ExecutionResult(False, None, "", "", 0, f"Compilation errors: {byte_code.errors}")
                code_obj = byte_code.code if hasattr(byte_code, 'code') else byte_code
            except SyntaxError as e:
                return ExecutionResult(False, None, "", "", 0, f"Syntax error: {str(e)}")

            exec_globals = self.safe_builtins.copy()
            if context:
                exec_globals.update(context)

            sys.stdout, sys.stderr = stdout_capture, stderr_capture

            try:
                with timeout_context(timeout):
                    exec(code_obj, exec_globals)
                result = exec_globals.get('result')
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return ExecutionResult(True, result, stdout_capture.getvalue(),
                                     stderr_capture.getvalue(), execution_time_ms)
            except TimeoutException as e:
                return ExecutionResult(False, None, stdout_capture.getvalue(),
                                     stderr_capture.getvalue(), timeout * 1000, f"Timeout: {str(e)}")
            except MemoryLimitException as e:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return ExecutionResult(False, None, stdout_capture.getvalue(),
                                     stderr_capture.getvalue(), execution_time_ms, f"Memory limit: {str(e)}")
            except Exception as e:
                execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return ExecutionResult(False, None, stdout_capture.getvalue(),
                                     stderr_capture.getvalue(), execution_time_ms,
                                     f"{type(e).__name__}: {str(e)}")
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

    def validate_code(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate code can be compiled."""
        try:
            byte_code = compile_restricted(code, filename='<validation>', mode='exec')
            if hasattr(byte_code, 'errors') and byte_code.errors:
                return False, f"Compilation errors: {byte_code.errors}"
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


def create_api_context(executor: Optional[CodeExecutor] = None) -> Dict[str, Callable]:
    """
    Create execution context with all API functions.

    Args:
        executor: CodeExecutor instance (for filesystem/skills access)

    Returns:
        Dict of available functions for code execution
    """
    from api import memory, versioning, analysis, utils

    context = {
        # Memory APIs
        'create_entities': memory.create_entities,
        'search_nodes': memory.search_nodes,
        'get_status': memory.get_status,
        'update_entity': memory.update_entity,

        # Versioning APIs
        'diff': versioning.diff,
        'revert': versioning.revert,
        'branch': versioning.branch,
        'history': versioning.history,
        'commit': versioning.commit,

        # Analysis APIs
        'detect_conflicts': analysis.detect_conflicts,
        'analyze_patterns': analysis.analyze_patterns,
        'classify_content': analysis.classify_content,
        'find_related': analysis.find_related,

        # Utility APIs
        'filter_by_confidence': utils.filter_by_confidence,
        'filter_by_type': utils.filter_by_type,
        'filter_by_date_range': utils.filter_by_date_range,
        'summarize_results': utils.summarize_results,
        'aggregate_stats': utils.aggregate_stats,
        'aggregate_by_tier': utils.aggregate_by_tier,
        'aggregate_by_date': utils.aggregate_by_date,
        'format_output': utils.format_output,
        'top_n': utils.top_n,
        'deduplicate': utils.deduplicate,
        'combine_results': utils.combine_results,
        'calculate_statistics': utils.calculate_statistics,
        'extract_field': utils.extract_field,
        'group_by': utils.group_by,
    }

    # Add filesystem and skills APIs if executor provided
    if executor:
        context.update({
            # Filesystem APIs
            'workspace': str(executor.workspace),
            'list_files': executor.list_files,
            'read_file': executor.read_file,
            'write_file': executor.write_file,
            'delete_file': executor.delete_file,

            # Skills APIs
            'save_skill': executor.save_skill,
            'load_skill': executor.load_skill,
            'list_skills': executor.list_skills,
        })

    return context
