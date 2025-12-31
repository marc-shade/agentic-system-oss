#!/usr/bin/env python3
"""
Enhanced Memory MCP Server with Git-like Version Control

FACADE MODULE - This file maintains backward compatibility.
All implementations have been moved to the server/ package.

Combines existing compression/tiering with version control features.

ARCHITECTURE: Uses memory-db Unix socket service for core operations
- create_entities, search_nodes, get_memory_status: Delegated to memory-db
- Versioning, branching, conflicts: Local advanced features
- Concurrent access: Enabled via memory-db central coordinator

Refactored Structure (1,807 lines -> modular package):
- server/config.py: Configuration, paths, logging
- server/database.py: Database initialization and schema
- server/compression.py: Data compression utilities
- server/versioning.py: Git-like version control
- server/tools/: MCP tool implementations
- server/modules.py: Dynamic module loading
"""

# FastMCP implementation
from fastmcp import FastMCP

# Memory-DB client for concurrent access
from memory_client import MemoryClient

# =============================================================================
# Re-export everything from server package for backward compatibility
# =============================================================================

from server import (
    # Config
    MEMORY_DIR,
    DB_PATH,
    STORAGE_BASE,
    HOOKS_PATH,
    logger,
    set_tool_usage_callback,
    log_tool_usage,
    # Database
    init_database,
    # Compression
    compress_data,
    decompress_data,
    calculate_checksum,
    classify_tier,
    # Versioning
    create_version,
    get_version_history,
    get_branches,
    # Tools
    register_all_tools,
    register_core_tools,
    register_git_tools,
    register_planning_tools,
    register_execution_tools,
    # Modules
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
    # FastMCP app (for external use)
    'app',
    'memory_client',
]


# Initialize FastMCP app
app = FastMCP("enhanced-memory")

# Initialize memory-db client for concurrent access
memory_client = MemoryClient()


if __name__ == "__main__":
    logger.info("Enhanced Memory MCP Server with Git Features starting...")
    logger.info(f"Database: {DB_PATH}")

    # Initialize database FIRST
    init_database()

    # Set up tool usage logging
    setup_tool_usage_logging(app)

    # Register core server tools
    register_all_tools(app, memory_client)

    # Initialize Neural Memory Fabric for RAG tools
    nmf_instance = initialize_nmf()

    # Register all optional modules based on MEMORY_PROFILE
    register_optional_modules(app, DB_PATH, nmf_instance, memory_client)

    # Disable banner to prevent stdout pollution (MCP protocol requirement)
    # Explicitly specify stdio transport for proper stdin/stdout handling
    app.run(transport="stdio", show_banner=False)
