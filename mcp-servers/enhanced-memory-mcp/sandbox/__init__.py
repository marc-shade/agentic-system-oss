"""
Secure code execution sandbox for enhanced-memory-mcp.

This package provides RestrictedPython-based code execution with:
- 30-second timeout limits
- 500MB memory limits  
- Safe built-ins only
- API access to memory operations
- Complete stdout/stderr capture
"""

from .executor import CodeExecutor

__all__ = ['CodeExecutor']
