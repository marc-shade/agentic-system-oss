"""
Git-like version control for Enhanced Memory MCP Server.

Extracted from server.py for better organization.
"""

import difflib
import json
import sqlite3
from typing import Any, Optional

from .compression import compress_data, decompress_data
from .config import DB_PATH


def create_version(
    entity_id: int,
    data: Any,
    message: Optional[str] = None,
    author: str = "system"
) -> int:
    """
    Create a new version when entity is updated.

    Args:
        entity_id: ID of the entity to version
        data: New data to store
        message: Optional commit message
        author: Author of the version (default: "system")

    Returns:
        ID of the new version record
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current branch
    cursor.execute('SELECT current_branch FROM entities WHERE id = ?', (entity_id,))
    result = cursor.fetchone()
    branch = result[0] if result else 'main'

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


def get_version_history(entity_id: int, branch: str = 'main', limit: int = 10) -> list:
    """
    Get version history for an entity.

    Args:
        entity_id: ID of the entity
        branch: Branch name (default: 'main')
        limit: Maximum versions to return

    Returns:
        List of version records
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT version_number, commit_message, author, created_at, is_current
        FROM memory_versions
        WHERE entity_id = ? AND branch_name = ?
        ORDER BY version_number DESC
        LIMIT ?
    ''', (entity_id, branch, limit))

    versions = [
        {
            'version': row[0],
            'message': row[1],
            'author': row[2],
            'timestamp': row[3],
            'is_current': bool(row[4])
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return versions


def get_branches(entity_id: int) -> list:
    """
    Get all branches for an entity.

    Args:
        entity_id: ID of the entity

    Returns:
        List of branch records
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT branch_name, is_active, created_at, created_by, description
        FROM memory_branches
        WHERE entity_id = ?
    ''', (entity_id,))

    branches = [
        {
            'name': row[0],
            'is_active': bool(row[1]),
            'created_at': row[2],
            'created_by': row[3],
            'description': row[4]
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return branches
