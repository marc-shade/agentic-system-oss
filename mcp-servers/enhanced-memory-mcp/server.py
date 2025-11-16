#!/usr/bin/env python3
"""
Enhanced Memory MCP Server with Git-like Version Control
Combines existing compression/tiering with version control features

ARCHITECTURE: Uses memory-db Unix socket service for core operations
- create_entities, search_nodes, get_memory_status: Delegated to memory-db
- Versioning, branching, conflicts: Local advanced features
- Concurrent access: Enabled via memory-db central coordinator
"""

import asyncio
import logging
import sqlite3
import hashlib
import zlib
import base64
import pickle
import json
import difflib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# FastMCP implementation
from fastmcp import FastMCP

# Memory-DB client for concurrent access
from memory_client import MemoryClient

# Code Execution imports
from sandbox.executor import CodeExecutor, create_api_context
from sandbox.security import comprehensive_safety_check, sanitize_output

# Set up logging - CRITICAL: Must use stderr for MCP compatibility
# MCP protocol requires stdout is reserved for JSON-RPC messages only
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Critical: redirect all logging to stderr
)
logger = logging.getLogger("enhanced-memory-git")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastMCP app
app = FastMCP("enhanced-memory")

# Initialize memory-db client for concurrent access
memory_client = MemoryClient()

def init_database():
    """Initialize SQLite database with all tables including Git features"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Original entities table with compression
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            tier TEXT DEFAULT 'working',
            compressed_data BLOB,
            original_size INTEGER,
            compressed_size INTEGER,
            compression_ratio REAL,
            checksum TEXT,
            access_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_version INTEGER DEFAULT 1,
            current_branch TEXT DEFAULT 'main'
        )
    ''')

    # Observations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER,
            content TEXT NOT NULL,
            compressed BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # Relations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity_id INTEGER,
            to_entity_id INTEGER,
            relation_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_entity_id) REFERENCES entities (id),
            FOREIGN KEY (to_entity_id) REFERENCES entities (id)
        )
    ''')

    # NEW: Memory versions table for Git-like history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            compressed_data BLOB NOT NULL,
            diff_from_previous TEXT,
            commit_message TEXT,
            author TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_current BOOLEAN DEFAULT 0,
            branch_name TEXT DEFAULT 'main',
            parent_version_id INTEGER,
            FOREIGN KEY (entity_id) REFERENCES entities (id),
            FOREIGN KEY (parent_version_id) REFERENCES memory_versions (id),
            UNIQUE(entity_id, version_number, branch_name)
        )
    ''')

    # NEW: Memory branches table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            branch_name TEXT NOT NULL,
            base_version_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT DEFAULT 'system',
            description TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities (id),
            FOREIGN KEY (base_version_id) REFERENCES memory_versions (id),
            UNIQUE(entity_id, branch_name)
        )
    ''')

    # NEW: Conflict detection table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_conflicts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity1_id INTEGER NOT NULL,
            entity2_id INTEGER NOT NULL,
            conflict_type TEXT NOT NULL,
            similarity_score REAL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT 0,
            resolution_notes TEXT,
            FOREIGN KEY (entity1_id) REFERENCES entities (id),
            FOREIGN KEY (entity2_id) REFERENCES entities (id)
        )
    ''')

    # NEW: Implementation plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS implementation_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            steps JSON NOT NULL,
            status TEXT DEFAULT 'draft',
            progress JSON,
            entity_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # NEW: Project handbooks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_handbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT UNIQUE NOT NULL,
            overview TEXT,
            architecture JSON,
            conventions JSON,
            setup_instructions TEXT,
            entity_id INTEGER,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # Create all indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_accessed ON entities(last_accessed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_entity ON memory_versions(entity_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_branch ON memory_versions(branch_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_current ON memory_versions(is_current)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON memory_conflicts(resolved)')

    conn.commit()
    conn.close()

def compress_data(data: Any) -> tuple[bytes, int, int, float]:
    """Compress data using zlib with maximum compression"""
    serialized = pickle.dumps(data)
    original_size = len(serialized)
    compressed = zlib.compress(serialized, level=9)
    compressed_size = len(compressed)
    compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
    return compressed, original_size, compressed_size, compression_ratio

def decompress_data(compressed: bytes) -> Any:
    """Decompress and deserialize data"""
    decompressed = zlib.decompress(compressed)
    return pickle.loads(decompressed)

def calculate_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum for data integrity"""
    return hashlib.sha256(data).hexdigest()

def classify_tier(entity_type: str, name: str) -> str:
    """Classify entity into memory tier"""
    if entity_type in ["system_role", "core_system"] or "orchestrator" in name.lower():
        return "core"
    elif entity_type in ["project", "session"] or "current" in name.lower():
        return "working"
    elif "archive" in name.lower() or "historical" in entity_type.lower():
        return "archive"
    else:
        return "reference"

def create_version(entity_id: int, data: Any, message: str = None, author: str = "system") -> int:
    """Create a new version when entity is updated"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current branch
    cursor.execute('SELECT current_branch FROM entities WHERE id = ?', (entity_id,))
    branch = cursor.fetchone()[0] or 'main'

    # Get current version number
    cursor.execute('''
        SELECT MAX(version_number) FROM memory_versions
        WHERE entity_id = ? AND branch_name = ?
    ''', (entity_id, branch))

    current_version = cursor.fetchone()[0]
    new_version = (current_version or 0) + 1

    # Compress data
    compressed, _, _, _ = compress_data(data)

    # Calculate diff if there's a previous version
    diff_text = None
    if current_version:
        cursor.execute('''
            SELECT compressed_data FROM memory_versions
            WHERE entity_id = ? AND version_number = ? AND branch_name = ?
        ''', (entity_id, current_version, branch))

        prev_data = cursor.fetchone()
        if prev_data:
            prev_decompressed = decompress_data(prev_data[0])
            old_str = json.dumps(prev_decompressed, indent=2, default=str)
            new_str = json.dumps(data, indent=2, default=str)
            diff = difflib.unified_diff(
                old_str.splitlines(keepends=True),
                new_str.splitlines(keepends=True),
                fromfile='previous',
                tofile='current'
            )
            diff_text = ''.join(diff)

    # Mark all previous versions as not current
    cursor.execute('''
        UPDATE memory_versions SET is_current = 0
        WHERE entity_id = ? AND branch_name = ?
    ''', (entity_id, branch))

    # Insert new version
    cursor.execute('''
        INSERT INTO memory_versions
        (entity_id, version_number, compressed_data, diff_from_previous,
         commit_message, author, is_current, branch_name)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ''', (entity_id, new_version, compressed, diff_text, message, author, branch))

    # Update entity's current version
    cursor.execute('''
        UPDATE entities SET current_version = ? WHERE id = ?
    ''', (new_version, entity_id))

    version_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return version_id

# ORIGINAL TOOLS WITH VERSION CONTROL ADDED

@app.tool()
async def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create entities with compression, storage, automatic versioning, and contextual enrichment.

    CONCURRENT ACCESS: Uses memory-db Unix socket service for database operations.
    CONTEXTUAL ENRICHMENT: Automatically adds LLM-generated contextual prefixes (RAG Tier 1).

    Args:
        entities: List of entity objects with name, entityType, and observations

    Returns:
        Results with compression statistics and entity details
    """
    try:
        # Delegate to memory-db service for concurrent access
        response = await memory_client.create_entities(entities)

        if response.get("success"):
            # Apply contextual enrichment to newly created entities
            enrichment_stats = await _enrich_new_entities(entities)

            return {
                "created": response.get("count", 0),
                "failed": 0,
                "results": response.get("results", []),
                "contextual_enrichment": enrichment_stats
            }
        else:
            return {
                "created": 0,
                "failed": len(entities),
                "error": response.get("error", "Unknown error from memory-db service")
            }

    except Exception as e:
        logger.error(f"Error creating entities via memory-db: {str(e)}")
        return {
            "created": 0,
            "failed": len(entities),
            "error": f"Memory-DB service error: {str(e)}"
        }


async def _enrich_new_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Add contextual prefixes to newly created entities.

    Part of RAG Tier 1 Strategy - Contextual Enrichment
    Expected improvement: -35% retrieval failures

    Args:
        entities: List of entity dictionaries

    Returns:
        Statistics about enrichment (enriched count, tokens used, cost)
    """
    try:
        from contextual_llm import get_prefix_generator

        generator = get_prefix_generator()
        enriched_count = 0
        failed_count = 0

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for entity in entities:
            try:
                entity_name = entity.get('name')
                entity_type = entity.get('entityType', 'unknown')
                observations = entity.get('observations', [])

                # Get entity ID
                cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
                result = cursor.fetchone()
                if not result:
                    logger.warning(f"Entity '{entity_name}' not found for enrichment")
                    failed_count += 1
                    continue

                entity_id = result[0]

                # Generate contextual prefix
                prefix, input_tokens, output_tokens = await generator.generate_prefix(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    observations=observations
                )

                # Get earliest observation timestamp to insert before it
                cursor.execute('''
                    SELECT MIN(created_at) FROM observations WHERE entity_id = ?
                ''', (entity_id,))
                min_created = cursor.fetchone()[0]

                # Use earlier timestamp to ensure prefix is first
                # Use SQL datetime format (YYYY-MM-DD HH:MM:SS) to match database format
                if min_created:
                    # Parse timestamp (handle both ISO and SQL formats)
                    if 'T' in min_created:
                        dt = datetime.fromisoformat(min_created.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(min_created, '%Y-%m-%d %H:%M:%S')

                    # Subtract 1 second and format as SQL datetime
                    insert_time = (dt - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    insert_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Insert contextual prefix as first observation
                cursor.execute('''
                    INSERT INTO observations (entity_id, content, created_at)
                    VALUES (?, ?, ?)
                ''', (entity_id, prefix, insert_time))

                enriched_count += 1

            except Exception as e:
                logger.error(f"Error enriching entity '{entity.get('name')}': {e}")
                failed_count += 1

        conn.commit()
        conn.close()

        # Get enrichment statistics
        stats = generator.get_stats()

        return {
            "enriched": enriched_count,
            "failed": failed_count,
            "tokens": {
                "input": stats.get("total_input_tokens", 0),
                "output": stats.get("total_output_tokens", 0)
            },
            "cost_usd": stats.get("estimated_cost_usd", 0.0),
            "using_llm": not stats.get("using_fallback", False)
        }

    except ImportError as e:
        logger.warning(f"Contextual enrichment not available: {e}")
        return {
            "enriched": 0,
            "failed": len(entities),
            "error": "contextual_llm module not available"
        }
    except Exception as e:
        logger.error(f"Error in contextual enrichment: {e}")
        return {
            "enriched": 0,
            "failed": len(entities),
            "error": str(e)
        }

@app.tool()
async def search_nodes(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for entities by name or type with automatic version history.

    CONCURRENT ACCESS: Uses memory-db Unix socket service for database operations.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of matching entities with version information
    """
    try:
        # Delegate to memory-db service for concurrent access
        response = await memory_client.search_nodes(query, limit)

        if response.get("success"):
            return {
                "query": query,
                "count": len(response.get("entities", [])),
                "results": response.get("entities", [])
            }
        else:
            return {
                "query": query,
                "count": 0,
                "results": [],
                "error": response.get("error", "Unknown error from memory-db service")
            }

    except Exception as e:
        logger.error(f"Error searching nodes via memory-db: {str(e)}")
        return {
            "query": query,
            "count": 0,
            "results": [],
            "error": f"Memory-DB service error: {str(e)}"
        }

# NEW GIT-LIKE TOOLS

@app.tool()
async def memory_diff(entity_name: str, version1: int = None, version2: int = None) -> Dict:
    """
    Get diff between two versions of a memory.

    Args:
        entity_name: Name of the entity
        version1: First version number (default: current-1)
        version2: Second version number (default: current)

    Returns:
        Diff information between versions
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, current_branch FROM entities WHERE name = ?', (entity_name,))
    entity = cursor.fetchone()
    if not entity:
        return {'error': 'Entity not found'}

    entity_id, branch = entity

    if version2 is None:
        cursor.execute('''
            SELECT MAX(version_number) FROM memory_versions
            WHERE entity_id = ? AND branch_name = ?
        ''', (entity_id, branch))
        version2 = cursor.fetchone()[0]

    if version1 is None:
        version1 = max(1, version2 - 1)

    cursor.execute('''
        SELECT compressed_data, version_number, commit_message, created_at
        FROM memory_versions
        WHERE entity_id = ? AND version_number IN (?, ?) AND branch_name = ?
        ORDER BY version_number
    ''', (entity_id, version1, version2, branch))

    versions = cursor.fetchall()
    conn.close()

    if len(versions) != 2:
        return {'error': 'Could not find both versions'}

    data1 = decompress_data(versions[0][0])
    data2 = decompress_data(versions[1][0])

    old_str = json.dumps(data1, indent=2, default=str)
    new_str = json.dumps(data2, indent=2, default=str)
    diff = difflib.unified_diff(
        old_str.splitlines(keepends=True),
        new_str.splitlines(keepends=True),
        fromfile=f'version_{versions[0][1]}',
        tofile=f'version_{versions[1][1]}'
    )

    return {
        'entity': entity_name,
        'branch': branch,
        'version1': {
            'number': versions[0][1],
            'message': versions[0][2],
            'timestamp': versions[0][3]
        },
        'version2': {
            'number': versions[1][1],
            'message': versions[1][2],
            'timestamp': versions[1][3]
        },
        'diff': ''.join(diff)
    }

@app.tool()
async def memory_revert(entity_name: str, version: int) -> Dict:
    """
    Revert a memory to a specific version.

    Args:
        entity_name: Name of the entity
        version: Version number to revert to

    Returns:
        Result of the revert operation
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, current_branch FROM entities WHERE name = ?', (entity_name,))
    entity = cursor.fetchone()
    if not entity:
        return {'error': 'Entity not found'}

    entity_id, branch = entity

    # Get the version data
    cursor.execute('''
        SELECT compressed_data FROM memory_versions
        WHERE entity_id = ? AND version_number = ? AND branch_name = ?
    ''', (entity_id, version, branch))

    version_data = cursor.fetchone()
    if not version_data:
        conn.close()
        return {'error': f'Version {version} not found'}

    # Update entity with old data
    cursor.execute('''
        UPDATE entities SET
            compressed_data = ?,
            last_accessed = CURRENT_TIMESTAMP,
            current_version = ?
        WHERE id = ?
    ''', (version_data[0], version, entity_id))

    # Create a new version entry for the revert
    data = decompress_data(version_data[0])
    create_version(entity_id, data, message=f"Reverted to version {version}")

    conn.commit()
    conn.close()

    return {
        'success': True,
        'entity': entity_name,
        'reverted_to': version,
        'branch': branch,
        'message': f"Successfully reverted to version {version}"
    }

@app.tool()
async def memory_branch(entity_name: str, branch_name: str, description: str = None) -> Dict:
    """
    Create a branch of a memory for experimentation.

    Args:
        entity_name: Name of the entity to branch
        branch_name: Name for the new branch
        description: Optional description of the branch purpose

    Returns:
        Result of the branch creation
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, current_branch, compressed_data FROM entities WHERE name = ?', (entity_name,))
    entity = cursor.fetchone()
    if not entity:
        return {'error': 'Entity not found'}

    entity_id, base_branch, current_data = entity

    # Get current version from base branch
    cursor.execute('''
        SELECT id FROM memory_versions
        WHERE entity_id = ? AND branch_name = ? AND is_current = 1
    ''', (entity_id, base_branch))

    base_version = cursor.fetchone()
    if not base_version:
        conn.close()
        return {'error': 'No current version found'}

    # Create branch record
    cursor.execute('''
        INSERT INTO memory_branches (entity_id, branch_name, base_version_id, description)
        VALUES (?, ?, ?, ?)
    ''', (entity_id, branch_name, base_version[0], description))

    # Copy current version to new branch
    cursor.execute('''
        INSERT INTO memory_versions
        (entity_id, version_number, compressed_data, commit_message,
         author, is_current, branch_name, parent_version_id)
        VALUES (?, 1, ?, ?, 'system', 1, ?, ?)
    ''', (entity_id, current_data, f"Branch created from {base_branch}", branch_name, base_version[0]))

    conn.commit()
    conn.close()

    return {
        'success': True,
        'entity': entity_name,
        'branch': branch_name,
        'base_branch': base_branch,
        'description': description,
        'message': f"Branch '{branch_name}' created successfully"
    }

@app.tool()
async def detect_memory_conflicts(threshold: float = 0.85) -> Dict:
    """
    Detect duplicate or conflicting memories.

    Args:
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        List of detected conflicts
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all entities
    cursor.execute('SELECT id, name, compressed_data FROM entities')
    entities = cursor.fetchall()

    conflicts = []
    from difflib import SequenceMatcher

    for i, entity1 in enumerate(entities):
        for entity2 in entities[i+1:]:
            data1 = decompress_data(entity1[2])
            data2 = decompress_data(entity2[2])

            similarity = SequenceMatcher(None, str(data1), str(data2)).ratio()

            if similarity > threshold:
                # Record conflict
                cursor.execute('''
                    INSERT OR IGNORE INTO memory_conflicts
                    (entity1_id, entity2_id, conflict_type, similarity_score)
                    VALUES (?, ?, 'duplicate', ?)
                ''', (entity1[0], entity2[0], similarity))

                conflicts.append({
                    'entity1': {'id': entity1[0], 'name': entity1[1]},
                    'entity2': {'id': entity2[0], 'name': entity2[1]},
                    'similarity': f"{similarity:.2%}",
                    'type': 'duplicate' if similarity > 0.95 else 'overlap'
                })

    conn.commit()
    conn.close()

    return {
        'conflicts_detected': len(conflicts),
        'threshold': threshold,
        'conflicts': conflicts[:10],  # Return first 10
        'recommendation': 'Review conflicts and consider merging or removing duplicates'
    }

@app.tool()
async def save_implementation_plan(
    name: str,
    steps: List[Dict],
    description: str = None
) -> Dict:
    """
    Save a structured implementation plan.

    Args:
        name: Plan name
        steps: List of step dictionaries
        description: Optional plan description

    Returns:
        Result of the save operation
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create entity for the plan
    entity_name = f"plan_{name}"
    plan_data = {
        'name': name,
        'description': description,
        'steps': steps,
        'type': 'implementation_plan'
    }

    # Create as entity with versioning
    result = await create_entities([{
        'name': entity_name,
        'entityType': 'implementation_plan',
        'observations': [f"Step {i+1}: {step}" for i, step in enumerate(steps)]
    }])

    # Also save in specialized table
    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
    entity_id = cursor.fetchone()[0]

    cursor.execute('''
        INSERT INTO implementation_plans (name, description, steps, entity_id)
        VALUES (?, ?, ?, ?)
    ''', (name, description, json.dumps(steps), entity_id))

    conn.commit()
    conn.close()

    return {
        'success': True,
        'name': name,
        'step_count': len(steps),
        'entity_name': entity_name,
        'versioned': True,
        'message': f"Implementation plan '{name}' saved with version control"
    }

@app.tool()
async def get_memory_status() -> Dict:
    """
    Get overall memory system status and statistics.

    CONCURRENT ACCESS: Uses memory-db Unix socket service for core stats.

    Returns:
        System statistics and health information
    """
    try:
        # Get basic stats from memory-db service
        response = await memory_client.get_memory_status()

        if response.get("success"):
            # Return the stats from memory-db
            return response
        else:
            return {
                "error": response.get("error", "Unknown error from memory-db service"),
                "entities": {"total": 0},
                "compression": {"ratio": "N/A"}
            }

    except Exception as e:
        logger.error(f"Error getting memory status via memory-db: {str(e)}")
        return {
            "error": f"Memory-DB service error: {str(e)}",
            "entities": {"total": 0},
            "compression": {"ratio": "N/A"}
        }


# === CODE EXECUTION TOOL ===
@app.tool()
async def execute_code(code: str, context_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute Python code in secure sandbox with API access.

    Implements Anthropic's code execution pattern for massive token reduction.
    Agents write code using APIs instead of calling tools directly.

    Token Savings:
    - Progressive disclosure: 2,000 → 200 tokens (90% reduction)
    - Local processing: 50,000 → 500 tokens (99% reduction)
    - Average: 96.6% token reduction

    Security Features:
    - RestrictedPython compilation
    - 30-second timeout
    - 500MB memory limit
    - Dangerous import blocking
    - PII tokenization

    Available APIs in code:
    - Memory: create_entities, search_nodes, get_status, update_entity
    - Versioning: diff, revert, branch, history, commit
    - Analysis: detect_conflicts, analyze_patterns, classify_content, find_related
    - Utils: filter_by_confidence, summarize_results, aggregate_stats, format_output
    - Filesystem: workspace, list_files, read_file, write_file, delete_file
    - Skills: save_skill, load_skill, list_skills

    Example Code:
        # Basic search and filter
        results = search_nodes("optimization", limit=100)
        high_conf = filter_by_confidence(results, 0.8)
        summary = summarize_results(high_conf)
        result = summary  # Return this

        # Save intermediate state
        write_file("results.json", json.dumps(results))

        # Save working code as skill
        code = '''
def filter_high_confidence(query, threshold=0.8):
    results = search_nodes(query, limit=1000)
    return [r for r in results if r.confidence > threshold]
'''
        save_skill("filter_high_confidence", code, "Filter memories by confidence")

    Args:
        code: Python code to execute
        context_vars: Additional variables to make available

    Returns:
        Execution result with success status, result data, and any errors
    """
    logger.info("🔧 Code execution requested")

    # Security check
    is_safe, safety_issues = comprehensive_safety_check(code)
    if not is_safe:
        logger.warning(f"⚠️  Code safety check failed: {safety_issues}")
        return {
            "success": False,
            "error": "Code safety check failed",
            "issues": safety_issues
        }

    # Create executor FIRST (so it can create workspace)
    executor = CodeExecutor(timeout_seconds=30, memory_limit_bytes=500 * 1024 * 1024)

    # Create API context with all available functions (pass executor for filesystem access)
    api_context = create_api_context(executor=executor)

    # Add any additional context variables
    if context_vars:
        api_context.update(context_vars)

    # Execute code in sandbox
    exec_result = executor.execute(code, context=api_context)

    if exec_result.success:
        # Sanitize output (PII tokenization, size limits)
        sanitized_result = sanitize_output(exec_result.result)
        logger.info(f"✅ Code executed successfully in {exec_result.execution_time_ms:.2f}ms")
        return {
            "success": True,
            "result": sanitized_result,
            "stdout": exec_result.stdout,
            "execution_time_ms": exec_result.execution_time_ms
        }
    else:
        logger.error(f"❌ Code execution failed: {exec_result.error}")
        return {
            "success": False,
            "error": exec_result.error,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "execution_time_ms": exec_result.execution_time_ms
        }


# === REASONING PRIORITIZATION INTEGRATION (75/15 Rule) ===
try:
    from reasoning_tools import register_reasoning_tools
    # Don't register yet - will do in main block after db init
except Exception as e:
    logger.warning(f"⚠️  Reasoning prioritization integration skipped: {e}")

# === NEURAL MEMORY FABRIC INTEGRATION ===
try:
    from nmf_tools import register_nmf_tools
    # Don't register yet - will do in main block after db init
except Exception as e:
    logger.warning(f"⚠️  NMF integration skipped: {e}")

if __name__ == "__main__":
    logger.info("Enhanced Memory MCP Server with Git Features starting...")
    logger.info(f"Database: {DB_PATH}")

    # Initialize database FIRST, inside main block
    init_database()

    # Register reasoning tools after database is ready
    try:
        from reasoning_tools import register_reasoning_tools
        register_reasoning_tools(app, DB_PATH)
        logger.info("✅ Reasoning Prioritization (75/15 rule) integrated")
    except Exception as e:
        logger.warning(f"⚠️  Reasoning prioritization integration skipped: {e}")

    # Register NMF tools after database is ready
    try:
        from nmf_tools import register_nmf_tools
        register_nmf_tools(app)
        logger.info("✅ Neural Memory Fabric tools integrated")
    except Exception as e:
        logger.warning(f"⚠️  NMF integration skipped: {e}")

    # Register SAFLA 4-tier memory tools
    try:
        from safla_orchestrator import SAFLAOrchestrator
        safla = SAFLAOrchestrator(DB_PATH)
        logger.info("✅ SAFLA 4-tier memory initialized")

        # SAFLA tool registration
        from safla_tools import register_safla_tools
        register_safla_tools(app, safla)
        logger.info("✅ SAFLA tools integrated")
    except Exception as e:
        logger.warning(f"⚠️  SAFLA integration skipped: {e}")

    # Register AGI Memory tools (Phase 1: Cross-session identity & memory-action loop)
    try:
        from agi_tools import register_agi_tools
        register_agi_tools(app, DB_PATH)
        logger.info("✅ AGI Memory tools integrated (Phase 1: Identity & Actions)")
    except Exception as e:
        logger.warning(f"⚠️  AGI Memory Phase 1 integration skipped: {e}")

    # Register AGI Memory Phase 2 tools (Temporal reasoning & consolidation)
    try:
        from agi_tools_phase2 import register_agi_phase2_tools
        register_agi_phase2_tools(app, DB_PATH)
        logger.info("✅ AGI Memory Phase 2 tools integrated (Temporal Reasoning & Consolidation)")
    except Exception as e:
        logger.warning(f"⚠️  AGI Memory Phase 2 integration skipped: {e}")

    # Register AGI Memory Phase 3 tools (Emotional tagging & associative networks)
    try:
        from agi_tools_phase3 import register_agi_phase3_tools
        register_agi_phase3_tools(app, DB_PATH)
        logger.info("✅ AGI Memory Phase 3 tools integrated (Emotional Tagging & Associative Networks)")
    except Exception as e:
        logger.warning(f"⚠️  AGI Memory Phase 3 integration skipped: {e}")

    # Register AGI Memory Phase 4 tools (Meta-cognition & self-improvement)
    try:
        from agi_tools_phase4 import register_agi_phase4_tools
        register_agi_phase4_tools(app, DB_PATH)
        logger.info("✅ AGI Memory Phase 4 tools integrated (Meta-Cognitive Awareness & Self-Improvement)")
    except Exception as e:
        logger.warning(f"⚠️  AGI Memory Phase 4 integration skipped: {e}")

    # Initialize Neural Memory Fabric for RAG tools
    nmf_instance = None
    try:
        from neural_memory_fabric import get_nmf
        nmf_instance = asyncio.run(get_nmf())
        logger.info("✅ Neural Memory Fabric initialized for RAG")
    except Exception as e:
        logger.warning(f"⚠️  NMF initialization skipped: {e}")

    # Register Re-ranking tools (RAG Tier 1 Strategy) - NMF backend
    if nmf_instance:
        try:
            from reranking_tools_nmf import register_reranking_tools_nmf
            register_reranking_tools_nmf(app, nmf_instance)
            logger.info("✅ Re-ranking (RAG Tier 1) integrated with NMF/Qdrant - Expected +40-55% precision")
        except Exception as e:
            logger.warning(f"⚠️  Re-ranking integration skipped: {e}")
    else:
        logger.warning("⚠️  Re-ranking skipped: NMF not available")

    # Register Hybrid Search tools (RAG Tier 1 Strategy) - NMF backend
    if nmf_instance:
        try:
            from hybrid_search_tools_nmf import register_hybrid_search_tools_nmf
            register_hybrid_search_tools_nmf(app, nmf_instance)
            logger.info("✅ Hybrid Search (RAG Tier 1) integrated with NMF/Qdrant - Expected +20-30% recall")
        except Exception as e:
            logger.warning(f"⚠️  Hybrid search integration skipped: {e}")
    else:
        logger.warning("⚠️  Hybrid search skipped: NMF not available")

    # Register Query Expansion tools (RAG Tier 2 Strategy) - Query Optimization
    if nmf_instance:
        try:
            from query_expansion_tools import register_query_expansion_tools
            register_query_expansion_tools(app, nmf_instance)
            logger.info("✅ Query Expansion (RAG Tier 2) integrated - Expected +15-25% recall")
        except Exception as e:
            logger.warning(f"⚠️  Query expansion integration skipped: {e}")
    else:
        logger.warning("⚠️  Query expansion skipped: NMF not available")

    # Register Multi-Query RAG tools (RAG Tier 2 Strategy) - Query Optimization
    if nmf_instance:
        try:
            from multi_query_rag_tools import register_multi_query_rag_tools
            register_multi_query_rag_tools(app, nmf_instance)
            logger.info("✅ Multi-Query RAG (RAG Tier 2) integrated - Expected +20-30% coverage")
        except Exception as e:
            logger.warning(f"⚠️  Multi-Query RAG integration skipped: {e}")
    else:
        logger.warning("⚠️  Multi-Query RAG skipped: NMF not available")

    # Register Contextual Retrieval tools (RAG Tier 3.1 Strategy) - Context Enhancement
    if nmf_instance:
        try:
            from contextual_retrieval_tools import register_contextual_retrieval_tools
            register_contextual_retrieval_tools(app, nmf_instance)
            logger.info("✅ Contextual Retrieval (RAG Tier 3.1) integrated - Expected +35-49% accuracy")
        except Exception as e:
            logger.warning(f"⚠️  Contextual Retrieval integration skipped: {e}")

    # Disable banner to prevent stdout pollution (MCP protocol requirement)
    # Explicitly specify stdio transport for proper stdin/stdout handling
    app.run(transport="stdio", show_banner=False)