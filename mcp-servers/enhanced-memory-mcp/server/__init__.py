"""
Server Package - Modular Enhanced Memory MCP Server

Extracted from server.py (1,807 lines) for better maintainability.

Package structure:
- config.py: Configuration, paths, logging
- database.py: Database initialization and schema
- compression.py: Data compression utilities
- versioning.py: Git-like version control
- tools/: MCP tool implementations
  - core.py: create_entities, search_nodes
  - git_ops.py: memory_diff, memory_revert, memory_branch, detect_memory_conflicts
  - planning.py: save_implementation_plan, get_memory_status
  - execution.py: execute_code
- modules.py: Dynamic module loading for orchestrator mode
"""

from .config import (
    MEMORY_DIR,
    DB_PATH,
    STORAGE_BASE,
    HOOKS_PATH,
    logger,
    set_tool_usage_callback,
    log_tool_usage,
)

from .database import init_database

from .compression import (
    compress_data,
    decompress_data,
    calculate_checksum,
    classify_tier,
)

from .compaction import (
    get_compaction_candidates,
    compact_entity,
    run_compaction_cycle,
    pin_entity,
    get_compaction_stats,
    restore_entity,
    TIER1_THRESHOLD_DAYS,
    TIER2_THRESHOLD_DAYS,
)

from .versioning import (
    create_version,
    get_version_history,
    get_branches,
)

from .tools import (
    register_all_tools,
    register_core_tools,
    register_git_tools,
    register_planning_tools,
    register_execution_tools,
)

from .modules import (
    ORCHESTRATOR_MODULES,
    get_memory_profile,
    is_orchestrator_mode,
    should_load_module,
    skip_msg,
    setup_tool_usage_logging,
    register_optional_modules,
    initialize_nmf,
)


__all__ = [
    # Config
    'MEMORY_DIR',
    'DB_PATH',
    'STORAGE_BASE',
    'HOOKS_PATH',
    'logger',
    'set_tool_usage_callback',
    'log_tool_usage',
    # Database
    'init_database',
    # Compression
    'compress_data',
    'decompress_data',
    'calculate_checksum',
    'classify_tier',
    # Compaction (Beads-inspired)
    'get_compaction_candidates',
    'compact_entity',
    'run_compaction_cycle',
    'pin_entity',
    'get_compaction_stats',
    'restore_entity',
    'TIER1_THRESHOLD_DAYS',
    'TIER2_THRESHOLD_DAYS',
    # Versioning
    'create_version',
    'get_version_history',
    'get_branches',
    # Tools
    'register_all_tools',
    'register_core_tools',
    'register_git_tools',
    'register_planning_tools',
    'register_execution_tools',
    # Modules
    'ORCHESTRATOR_MODULES',
    'get_memory_profile',
    'is_orchestrator_mode',
    'should_load_module',
    'skip_msg',
    'setup_tool_usage_logging',
    'register_optional_modules',
    'initialize_nmf',
]
