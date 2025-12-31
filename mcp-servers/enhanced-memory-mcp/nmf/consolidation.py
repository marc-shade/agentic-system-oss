"""
Memory consolidation for Neural Memory Fabric (Phase 4).

Implements sleep-time memory consolidation:
- Find frequently accessed memories
- Identify similar memory clusters
- Create abstract summaries
- Strengthen important connections
- Prune weak links

Extracted from neural_memory_fabric.py for modularity.
"""

import sqlite3
from typing import Any, Dict, List, Optional

from .config import logger
from .intelligence import generate_cluster_summary


async def consolidate_memories(
    sqlite_conn: sqlite3.Connection,
    vector_db,
    find_related_func,
    remember_func,
    agent_id: str,
    min_access_count: int = 3,
    similarity_threshold: float = 0.8
) -> Dict[str, Any]:
    """
    Consolidate related memories (sleep-time processing).

    This implements memory consolidation inspired by human memory:
    1. Find frequently accessed memories
    2. Identify highly similar memory clusters
    3. Create abstract summaries
    4. Strengthen important connections
    5. Prune weak links

    Args:
        sqlite_conn: SQLite connection
        vector_db: Qdrant client (for similarity search)
        find_related_func: Function to find related memories
        remember_func: Function to store new memories
        agent_id: Agent to consolidate memories for
        min_access_count: Minimum access count to consider
        similarity_threshold: Threshold for grouping similar memories

    Returns:
        Consolidation statistics
    """
    logger.info(f"Starting memory consolidation for {agent_id}")

    # Find frequently accessed memories
    cursor = sqlite_conn.cursor()
    cursor.execute('''
        SELECT id, content, access_count, importance_score
        FROM nmf_entities
        WHERE agent_id = ? AND access_count >= ?
        ORDER BY access_count DESC, importance_score DESC
        LIMIT 50
    ''', (agent_id, min_access_count))

    frequent_memories = cursor.fetchall()

    if not frequent_memories or not vector_db:
        return {
            'memories_processed': 0,
            'clusters_created': 0,
            'summaries_created': 0,
            'links_strengthened': 0,
            'links_pruned': 0
        }

    # Group similar memories into clusters
    clusters = []
    processed = set()

    for mem_id, content, access_count, importance in frequent_memories:
        if mem_id in processed:
            continue

        # Find similar memories
        related = await find_related_func(
            mem_id,
            similarity_threshold=similarity_threshold,
            max_links=10
        )

        if related:
            cluster = {
                'anchor': mem_id,
                'members': [r[0] for r in related],
                'similarities': [r[1] for r in related],
                'avg_similarity': sum(r[1] for r in related) / len(related)
            }
            clusters.append(cluster)
            processed.add(mem_id)
            processed.update(cluster['members'])

    # Create abstract summaries for each cluster
    summaries_created = 0
    for cluster in clusters:
        try:
            # Get all content from cluster
            member_ids = [cluster['anchor']] + cluster['members']
            cursor.execute(f'''
                SELECT content FROM nmf_entities
                WHERE id IN ({','.join('?' * len(member_ids))})
            ''', member_ids)

            contents = [row[0] for row in cursor.fetchall()]
            combined_content = ' '.join(contents)

            # Generate summary using LLM
            summary = await generate_cluster_summary(combined_content)

            if summary:
                # Store summary as new memory
                await remember_func(
                    content=summary,
                    metadata={
                        'tags': ['consolidated', 'summary'],
                        'cluster_members': member_ids,
                        'importance': 0.8  # High importance for summaries
                    },
                    agent_id=agent_id
                )
                summaries_created += 1

        except Exception as e:
            logger.error(f"Failed to consolidate cluster: {e}")

    # Strengthen important links (increase score)
    cursor.execute('''
        UPDATE nmf_links
        SET link_score = MIN(1.0, link_score * 1.2)
        WHERE from_memory_id IN (
            SELECT id FROM nmf_entities
            WHERE agent_id = ? AND importance_score > 0.7
        )
    ''', (agent_id,))

    links_strengthened = cursor.rowcount

    # Prune weak links (below 0.3 similarity)
    cursor.execute('''
        DELETE FROM nmf_links
        WHERE link_score < 0.3
        AND from_memory_id IN (
            SELECT id FROM nmf_entities WHERE agent_id = ?
        )
    ''', (agent_id,))

    links_pruned = cursor.rowcount
    sqlite_conn.commit()

    logger.info(f"Consolidation complete: {len(clusters)} clusters, {summaries_created} summaries")

    return {
        'memories_processed': len(frequent_memories),
        'clusters_created': len(clusters),
        'summaries_created': summaries_created,
        'links_strengthened': links_strengthened,
        'links_pruned': links_pruned
    }


__all__ = [
    'consolidate_memories',
]
