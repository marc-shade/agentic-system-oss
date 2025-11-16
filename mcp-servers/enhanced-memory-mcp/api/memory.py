"""
Core Memory Operations API
Provides Python functions for agent code execution
"""

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create one or more memory entities.

    Args:
        entities: List of entity dictionaries with:
            - name (str): Unique entity name
            - entityType (str): Type classification
            - observations (List[str]): Content to store

    Returns:
        Dict with created entity IDs and compression stats

    Example:
        result = create_entities([{
            "name": "project-success-2025",
            "entityType": "project_outcome",
            "observations": ["Used parallel agents", "Token savings 45%"]
        }])
        # Returns: {"created": [123], "compression_ratio": 0.23}
    """
    from memory_client import MemoryClient

    client = MemoryClient()
    return client.create_entities(entities)


def search_nodes(
    query: str,
    limit: int = 10,
    entity_type: Optional[str] = None,
    min_confidence: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Search memory entities by query.

    Args:
        query: Search query string
        limit: Maximum results to return
        entity_type: Optional filter by entity type
        min_confidence: Minimum confidence score (0.0-1.0)

    Returns:
        List of matching entity dictionaries

    Example:
        # Agent can filter locally
        all_results = search_nodes("optimization", limit=100)
        high_conf = [r for r in all_results if r.get('confidence', 0) > 0.8]
        return {"count": len(high_conf), "top": high_conf[0]}
    """
    from memory_client import MemoryClient

    client = MemoryClient()
    results = client.search_nodes(query, limit)

    # Local filtering if specified
    if entity_type:
        results = [r for r in results if r.get('entityType') == entity_type]
    if min_confidence > 0:
        results = [r for r in results if r.get('confidence', 0) >= min_confidence]

    return results


def get_status() -> Dict[str, Any]:
    """
    Get memory system status and statistics.

    Returns:
        Dict with system metrics:
            - total_entities
            - compression_stats
            - tier_distribution
            - recent_activity

    Example:
        status = get_status()
        # Agent can extract just what's needed
        return {"entities": status['total_entities']}
    """
    from memory_client import MemoryClient

    client = MemoryClient()
    return client.get_memory_status()


def update_entity(
    name: str,
    observations: List[str],
    commit_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update existing entity with new observations.

    Args:
        name: Entity name
        observations: New observations to add
        commit_message: Optional commit message for versioning

    Returns:
        Dict with update status and new version number

    Example:
        result = update_entity(
            "project-alpha",
            ["Completed milestone 3", "Performance improved 20%"],
            "Milestone 3 completion"
        )
        # Returns: {"entity_id": 45, "version": 3}
    """
    import sqlite3
    from pathlib import Path

    DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get entity ID
    cursor.execute('SELECT id FROM entities WHERE name = ?', (name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Entity not found: {name}")

    entity_id = row[0]

    # Add observations
    for obs in observations:
        cursor.execute(
            'INSERT INTO observations (entity_id, content) VALUES (?, ?)',
            (entity_id, obs)
        )

    # Create version (import from server module)
    try:
        import server
        version_id = server.create_version(entity_id, {"observations": observations}, commit_message)
    except Exception as e:
        # Fallback: Just return entity info without versioning
        version_id = None

    conn.commit()
    conn.close()

    return {
        "entity_id": entity_id,
        "version_id": version_id,
        "observations_added": len(observations)
    }
