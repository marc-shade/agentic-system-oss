"""
Version Control Operations API
Git-like versioning for memory entities
"""

from typing import Dict, List, Any, Optional
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


def diff(
    entity_name: str,
    version1: Optional[int] = None,
    version2: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get diff between two versions of a memory.

    Args:
        entity_name: Name of entity
        version1: First version (default: current-1)
        version2: Second version (default: current)

    Returns:
        Dict with diff information

    Example:
        # Agent can analyze diff and return summary
        diff_data = diff("project-alpha")
        changes = len(diff_data['diff'].splitlines())
        return {"lines_changed": changes}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity ID and current version
    cursor.execute(
        'SELECT id, current_version FROM entities WHERE name = ?',
        (entity_name,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {entity_name}")

    entity_id, current = row

    # Default versions
    if version2 is None:
        version2 = current
    if version1 is None:
        version1 = current - 1 if current > 1 else current

    # Get diff from version 2
    cursor.execute('''
        SELECT diff_from_previous, commit_message, created_at, author
        FROM memory_versions
        WHERE entity_id = ? AND version_number = ?
    ''', (entity_id, version2))

    diff_data = cursor.fetchone()
    conn.close()

    if not diff_data:
        return {"error": f"Version {version2} not found"}

    return {
        "entity": entity_name,
        "version1": version1,
        "version2": version2,
        "diff": diff_data[0] or "",
        "message": diff_data[1],
        "timestamp": diff_data[2],
        "author": diff_data[3]
    }


def revert(entity_name: str, version: int) -> Dict[str, Any]:
    """
    Revert entity to a specific version.

    Args:
        entity_name: Name of entity
        version: Version number to revert to

    Returns:
        Dict with revert status

    Example:
        result = revert("project-alpha", 5)
        # Returns: {"reverted": True, "new_version": 8}
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity ID
    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {entity_name}")

    entity_id = row[0]

    # Get old version data
    cursor.execute('''
        SELECT compressed_data
        FROM memory_versions
        WHERE entity_id = ? AND version_number = ?
    ''', (entity_id, version))

    old_data = cursor.fetchone()
    if not old_data:
        conn.close()
        raise ValueError(f"Version {version} not found")

    # Decompress old data
    from server import decompress_data
    data = decompress_data(old_data[0])

    # Create new version with reverted data
    from server import create_version
    new_version_id = create_version(
        entity_id,
        data,
        f"Reverted to version {version}",
        "system"
    )

    cursor.execute('SELECT version_number FROM memory_versions WHERE id = ?', (new_version_id,))
    new_version = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "reverted": True,
        "entity": entity_name,
        "reverted_to": version,
        "new_version": new_version
    }


def branch(
    entity_name: str,
    branch_name: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create experimental branch of entity.

    Args:
        entity_name: Entity to branch
        branch_name: New branch name
        description: Optional description

    Returns:
        Dict with branch creation status

    Example:
        result = branch("project-alpha", "experiment-1", "Testing new approach")
        # Returns: {"branch_id": 12, "base_version": 7}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity ID and current version
    cursor.execute(
        'SELECT id, current_version FROM entities WHERE name = ?',
        (entity_name,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {entity_name}")

    entity_id, current_version = row

    # Get current version ID
    cursor.execute('''
        SELECT id FROM memory_versions
        WHERE entity_id = ? AND version_number = ? AND is_current = 1
    ''', (entity_id, current_version))

    version_row = cursor.fetchone()
    if not version_row:
        conn.close()
        raise ValueError("Current version not found")

    base_version_id = version_row[0]

    # Create branch
    cursor.execute('''
        INSERT INTO memory_branches
        (entity_id, branch_name, base_version_id, description)
        VALUES (?, ?, ?, ?)
    ''', (entity_id, branch_name, base_version_id, description))

    branch_id = cursor.lastrowid

    # Update entity to use new branch
    cursor.execute('''
        UPDATE entities SET current_branch = ? WHERE id = ?
    ''', (branch_name, entity_id))

    conn.commit()
    conn.close()

    return {
        "branch_id": branch_id,
        "entity": entity_name,
        "branch": branch_name,
        "base_version": current_version,
        "description": description
    }


def history(entity_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get version history for entity.

    Args:
        entity_name: Entity name
        limit: Max versions to return

    Returns:
        List of version dictionaries

    Example:
        # Agent can analyze history
        versions = history("project-alpha", limit=50)
        recent = [v for v in versions if is_recent(v['timestamp'])]
        return {"recent_changes": len(recent)}
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get entity ID
    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {entity_name}")

    entity_id = row['id']

    # Get version history
    cursor.execute('''
        SELECT version_number, commit_message, author, created_at, branch_name
        FROM memory_versions
        WHERE entity_id = ?
        ORDER BY version_number DESC
        LIMIT ?
    ''', (entity_id, limit))

    versions = []
    for row in cursor.fetchall():
        versions.append({
            "version": row['version_number'],
            "message": row['commit_message'],
            "author": row['author'],
            "timestamp": row['created_at'],
            "branch": row['branch_name']
        })

    conn.close()
    return versions


def commit(
    entity_name: str,
    message: str,
    author: str = "agent"
) -> Dict[str, Any]:
    """
    Create a commit (version snapshot) of current entity state.

    Args:
        entity_name: Entity to commit
        message: Commit message
        author: Author name

    Returns:
        Dict with commit details

    Example:
        result = commit("project-alpha", "Completed optimization phase")
        # Returns: {"version": 8, "commit_id": 234}
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity ID
    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {entity_name}")

    entity_id = row[0]

    # Get current observations
    cursor.execute('''
        SELECT content FROM observations
        WHERE entity_id = ?
        ORDER BY created_at
    ''', (entity_id,))

    observations = [row[0] for row in cursor.fetchall()]

    # Create version
    from server import create_version
    version_id = create_version(
        entity_id,
        {"observations": observations},
        message,
        author
    )

    cursor.execute(
        'SELECT version_number FROM memory_versions WHERE id = ?',
        (version_id,)
    )
    version_number = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return {
        "commit_id": version_id,
        "version": version_number,
        "entity": entity_name,
        "message": message,
        "author": author
    }
