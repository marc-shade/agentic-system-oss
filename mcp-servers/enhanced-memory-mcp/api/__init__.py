"""
Enhanced Memory MCP - Code Execution API
Exposes memory operations as Python functions for agent code execution
"""

from .memory import (
    create_entities,
    search_nodes,
    get_status,
    update_entity
)

from .versioning import (
    diff,
    revert,
    branch,
    history,
    commit
)

from .analysis import (
    detect_conflicts,
    analyze_patterns,
    classify_content,
    find_related
)

from .utils import (
    filter_by_confidence,
    summarize_results,
    aggregate_stats,
    format_output
)

__all__ = [
    # Memory operations
    'create_entities',
    'search_nodes',
    'get_status',
    'update_entity',
    # Version control
    'diff',
    'revert',
    'branch',
    'history',
    'commit',
    # Analysis
    'detect_conflicts',
    'analyze_patterns',
    'classify_content',
    'find_related',
    # Utilities
    'filter_by_confidence',
    'summarize_results',
    'aggregate_stats',
    'format_output',
]
