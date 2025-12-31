"""
Git-like version control tools for Enhanced Memory MCP Server.

Tools:
- memory_diff: Get diff between versions
- memory_revert: Revert to specific version
- memory_branch: Create branch for experimentation
- detect_memory_conflicts: Find duplicate/conflicting memories
"""

import json
import sqlite3
from difflib import SequenceMatcher
import difflib
from typing import Dict, Optional

from ..compression import decompress_data
from ..config import DB_PATH
from ..versioning import create_version


def register_git_tools(app):
    """Register git-like version control tools with FastMCP app."""

    @app.tool()
    async def memory_diff(
        entity_name: str,
        version1: Optional[int] = None,
        version2: Optional[int] = None
    ) -> Dict:
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

        cursor.execute(
            'SELECT id, current_branch FROM entities WHERE name = ?',
            (entity_name,)
        )
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

        cursor.execute(
            'SELECT id, current_branch FROM entities WHERE name = ?',
            (entity_name,)
        )
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
    async def memory_branch(
        entity_name: str,
        branch_name: str,
        description: Optional[str] = None
    ) -> Dict:
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

        cursor.execute(
            'SELECT id, current_branch, compressed_data FROM entities WHERE name = ?',
            (entity_name,)
        )
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
        ''', (
            entity_id,
            current_data,
            f"Branch created from {base_branch}",
            branch_name,
            base_version[0]
        ))

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

    return {
        'memory_diff': memory_diff,
        'memory_revert': memory_revert,
        'memory_branch': memory_branch,
        'detect_memory_conflicts': detect_memory_conflicts,
    }
