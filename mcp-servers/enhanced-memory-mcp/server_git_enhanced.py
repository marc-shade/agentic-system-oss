#!/usr/bin/env python3
"""
Enhanced Memory MCP Server with Git-like Version Control
Combines existing compression/tiering with version control features
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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced-memory-git")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastMCP app
app = FastMCP("enhanced-memory")

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
    Create entities with compression, storage, and automatic versioning.

    Args:
        entities: List of entity objects with name, entityType, and observations

    Returns:
        Results with compression statistics and entity details
    """
    results = []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for entity in entities:
        try:
            name = entity.get("name", "")
            entity_type = entity.get("entityType", "unknown")
            observations = entity.get("observations", [])

            # Classify tier
            tier = classify_tier(entity_type, name)

            # Prepare entity data
            entity_data = {
                "name": name,
                "type": entity_type,
                "observations": observations,
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "tier": tier
                }
            }

            # Compress the entity data
            compressed, original_size, compressed_size, compression_ratio = compress_data(entity_data)
            checksum = calculate_checksum(compressed)

            # Check if entity exists (for update)
            cursor.execute('SELECT id FROM entities WHERE name = ?', (name,))
            existing = cursor.fetchone()

            if existing:
                entity_id = existing[0]
                # Update existing entity
                cursor.execute('''
                    UPDATE entities SET
                        compressed_data = ?, original_size = ?, compressed_size = ?,
                        compression_ratio = ?, checksum = ?, last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE id = ?
                ''', (compressed, original_size, compressed_size, compression_ratio, checksum, entity_id))

                # Create a version for the update
                create_version(entity_id, entity_data, message=f"Updated entity: {name}")
            else:
                # Insert new entity
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, tier, compressed_data,
                                        original_size, compressed_size, compression_ratio, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, entity_type, tier, compressed, original_size, compressed_size,
                      compression_ratio, checksum))

                entity_id = cursor.lastrowid

                # Create initial version
                create_version(entity_id, entity_data, message=f"Created entity: {name}")

            # Store observations
            for obs in observations:
                obs_compressed, _, _, _ = compress_data(obs)
                cursor.execute('''
                    INSERT INTO observations (entity_id, content, compressed)
                    VALUES (?, ?, ?)
                ''', (entity_id, obs, obs_compressed))

            results.append({
                "entityId": entity_id,
                "name": name,
                "type": entity_type,
                "tier": tier,
                "observationCount": len(observations),
                "compression": {
                    "originalSize": original_size,
                    "compressedSize": compressed_size,
                    "ratio": f"{compression_ratio:.2%}",
                    "saved": original_size - compressed_size
                },
                "checksum": checksum[:8] + "...",
                "versioned": True
            })

        except Exception as e:
            logger.error(f"Error creating entity {entity.get('name', 'unknown')}: {str(e)}")
            results.append({"error": str(e), "entity": entity.get("name", "unknown")})

    conn.commit()
    conn.close()

    return {
        "created": len([r for r in results if "entityId" in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results
    }

@app.tool()
async def search_nodes(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for entities by name or type with automatic version history.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of matching entities with version information
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Search in entities
    cursor.execute('''
        SELECT e.id, e.name, e.entity_type, e.tier, e.access_count,
               e.created_at, e.last_accessed, e.compression_ratio,
               e.current_version, e.current_branch,
               COUNT(DISTINCT v.id) as version_count
        FROM entities e
        LEFT JOIN memory_versions v ON e.id = v.entity_id
        WHERE e.name LIKE ? OR e.entity_type LIKE ?
        GROUP BY e.id
        ORDER BY e.access_count DESC, e.last_accessed DESC
        LIMIT ?
    ''', (f'%{query}%', f'%{query}%', limit))

    results = []
    for row in cursor.fetchall():
        # Get observations count
        cursor.execute('SELECT COUNT(*) FROM observations WHERE entity_id = ?', (row[0],))
        obs_count = cursor.fetchone()[0]

        # Get relations count
        cursor.execute('''
            SELECT COUNT(*) FROM relations
            WHERE from_entity_id = ? OR to_entity_id = ?
        ''', (row[0], row[0]))
        rel_count = cursor.fetchone()[0]

        results.append({
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "tier": row[3],
            "accessCount": row[4],
            "created": row[5],
            "lastAccessed": row[6],
            "compressionRatio": f"{row[7]:.2%}" if row[7] else "N/A",
            "currentVersion": row[8],
            "currentBranch": row[9],
            "totalVersions": row[10],
            "observations": obs_count,
            "relations": rel_count
        })

    conn.close()

    return {
        "query": query,
        "count": len(results),
        "results": results
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

    Returns:
        System statistics and health information
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity statistics
    cursor.execute('SELECT COUNT(*) FROM entities')
    total_entities = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM memory_versions')
    total_versions = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM memory_branches')
    total_branches = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM memory_conflicts WHERE resolved = 0')
    unresolved_conflicts = cursor.fetchone()[0]

    # Get compression statistics
    cursor.execute('''
        SELECT SUM(original_size), SUM(compressed_size)
        FROM entities WHERE original_size IS NOT NULL
    ''')
    sizes = cursor.fetchone()
    total_original = sizes[0] or 0
    total_compressed = sizes[1] or 0

    # Get tier distribution
    cursor.execute('''
        SELECT tier, COUNT(*) FROM entities GROUP BY tier
    ''')
    tier_distribution = dict(cursor.fetchall())

    # Get recent activity
    cursor.execute('''
        SELECT COUNT(*) FROM entities
        WHERE datetime(last_accessed) > datetime('now', '-1 day')
    ''')
    recent_access = cursor.fetchone()[0]

    conn.close()

    return {
        'entities': {
            'total': total_entities,
            'versions': total_versions,
            'branches': total_branches,
            'recent_access': recent_access
        },
        'compression': {
            'total_original': total_original,
            'total_compressed': total_compressed,
            'ratio': f"{(total_compressed/total_original*100):.1f}%" if total_original > 0 else "N/A",
            'saved_bytes': total_original - total_compressed
        },
        'tiers': tier_distribution,
        'conflicts': {
            'unresolved': unresolved_conflicts
        },
        'database': {
            'path': str(DB_PATH),
            'size': DB_PATH.stat().st_size if DB_PATH.exists() else 0
        }
    }

# Initialize database when module loads
init_database()

if __name__ == "__main__":
    logger.info("Enhanced Memory MCP Server with Git Features starting...")
    logger.info(f"Database: {DB_PATH}")
    app.run()