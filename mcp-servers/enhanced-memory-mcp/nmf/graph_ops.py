"""
Graph operations for Neural Memory Fabric (Phase 3).

Implements:
- Temporal entity nodes (Neo4j)
- Bi-temporal edges
- A-MEM style dynamic linking
- Graph traversal
- Temporal queries

Extracted from neural_memory_fabric.py for modularity.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import logger


async def create_graph_node(
    graph_driver,
    memory_id: str,
    content: str,
    timestamp: str,
    agent_id: str,
    tags: List[str],
    importance_score: float
) -> bool:
    """
    Create temporal entity node in Neo4j graph database.

    Implements bi-temporal tracking (Zep/Graphiti pattern):
    - event_time: When the memory was created
    - valid_from: When this version became valid
    - valid_until: When this version was superseded (None if current)

    Args:
        graph_driver: Neo4j driver instance
        memory_id: Unique memory identifier
        content: Memory content
        timestamp: ISO timestamp
        agent_id: Agent that created the memory
        tags: Memory tags
        importance_score: Memory importance (0.0-1.0)

    Returns:
        True if successful, False otherwise
    """
    if not graph_driver:
        return False

    try:
        with graph_driver.session() as session:
            # Create memory node with bi-temporal properties
            session.run("""
                CREATE (m:Memory {
                    id: $id,
                    content: $content,
                    agent_id: $agent_id,
                    event_time: datetime($timestamp),
                    valid_from: datetime($valid_from),
                    valid_until: null,
                    importance_score: $importance,
                    access_count: 0,
                    tags: $tags
                })
            """, {
                'id': memory_id,
                'content': content[:500],  # Store excerpt
                'agent_id': agent_id,
                'timestamp': timestamp,
                'valid_from': timestamp,
                'importance': importance_score,
                'tags': tags
            })

            logger.info(f"Created graph node for {memory_id}")
            return True

    except Exception as e:
        logger.error(f"Failed to create graph node: {e}")
        return False


async def create_temporal_edge(
    graph_driver,
    from_id: str,
    to_id: str,
    relationship_type: str = "RELATES_TO",
    link_score: float = 0.5,
    valid_from: Optional[str] = None
) -> bool:
    """
    Create bi-temporal edge between memory nodes.

    Args:
        graph_driver: Neo4j driver instance
        from_id: Source memory ID
        to_id: Target memory ID
        relationship_type: Type of relationship (RELATES_TO, REFERENCES, CONTRADICTS, etc.)
        link_score: Strength of relationship (0.0 to 1.0)
        valid_from: When this relationship became valid (default: now)

    Returns:
        True if successful, False otherwise
    """
    if not graph_driver:
        return False

    if valid_from is None:
        valid_from = datetime.utcnow().isoformat()

    try:
        with graph_driver.session() as session:
            session.run(f"""
                MATCH (from:Memory {{id: $from_id}})
                MATCH (to:Memory {{id: $to_id}})
                CREATE (from)-[r:{relationship_type} {{
                    link_score: $score,
                    valid_from: datetime($valid_from),
                    valid_until: null,
                    created_at: datetime()
                }}]->(to)
            """, {
                'from_id': from_id,
                'to_id': to_id,
                'score': link_score,
                'valid_from': valid_from
            })

            logger.info(f"Created {relationship_type} edge: {from_id} -> {to_id} (score: {link_score})")
            return True

    except Exception as e:
        logger.error(f"Failed to create temporal edge: {e}")
        return False


async def find_related_memories(
    vector_db,
    vector_collection_name: str,
    sqlite_conn: sqlite3.Connection,
    embedding_func,
    memory_id: str,
    similarity_threshold: float = 0.6,
    max_links: int = 5
) -> List[Tuple[str, float]]:
    """
    Find related memories using semantic similarity (A-MEM pattern).

    Args:
        vector_db: Qdrant client
        vector_collection_name: Name of Qdrant collection
        sqlite_conn: SQLite connection
        embedding_func: Function to generate embeddings
        memory_id: Source memory ID
        similarity_threshold: Minimum similarity score
        max_links: Maximum number of related memories

    Returns:
        List of (memory_id, similarity_score) tuples
    """
    if not vector_db:
        return []

    try:
        # Get embedding for the source memory
        cursor = sqlite_conn.cursor()
        cursor.execute('SELECT content FROM nmf_entities WHERE id = ?', (memory_id,))
        row = cursor.fetchone()

        if not row:
            return []

        content = row[0]
        query_embedding = await embedding_func(content)

        if not query_embedding:
            return []

        # Search for similar memories
        search_results = vector_db.search(
            collection_name=vector_collection_name,
            query_vector=query_embedding,
            limit=max_links + 1  # +1 because it includes itself
        )

        related = []
        if search_results:
            for result in search_results:
                result_memory_id = result.payload.get('memory_id', result.id)
                if result_memory_id == memory_id:
                    continue  # Skip self

                similarity = result.score

                if similarity >= similarity_threshold:
                    related.append((result_memory_id, similarity))

        return related[:max_links]

    except Exception as e:
        logger.error(f"Failed to find related memories: {e}")
        return []


async def create_dynamic_links(
    vector_db,
    vector_collection_name: str,
    sqlite_conn: sqlite3.Connection,
    graph_driver,
    embedding_func,
    memory_id: str,
    similarity_threshold: float = 0.6,
    max_links: int = 5
) -> int:
    """
    Automatically create links to related memories (A-MEM pattern).

    Args:
        vector_db: Qdrant client
        vector_collection_name: Name of Qdrant collection
        sqlite_conn: SQLite connection
        graph_driver: Neo4j driver (optional)
        embedding_func: Function to generate embeddings
        memory_id: Source memory ID
        similarity_threshold: Minimum similarity score
        max_links: Maximum number of links to create

    Returns:
        Number of links created
    """
    related = await find_related_memories(
        vector_db,
        vector_collection_name,
        sqlite_conn,
        embedding_func,
        memory_id,
        similarity_threshold,
        max_links
    )

    if not related:
        logger.info(f"No related memories found for {memory_id}")
        return 0

    links_created = 0
    cursor = sqlite_conn.cursor()

    for related_id, similarity in related:
        try:
            # Store in SQLite
            cursor.execute('''
                INSERT OR IGNORE INTO nmf_links (from_memory_id, to_memory_id, link_type, link_score)
                VALUES (?, ?, ?, ?)
            ''', (memory_id, related_id, 'relates_to', similarity))

            # Create graph edge if Neo4j available
            await create_temporal_edge(
                graph_driver,
                memory_id,
                related_id,
                "RELATES_TO",
                similarity
            )

            links_created += 1
            logger.info(f"Linked {memory_id} -> {related_id} (similarity: {similarity:.3f})")

        except Exception as e:
            logger.error(f"Failed to create link: {e}")

    sqlite_conn.commit()
    logger.info(f"Created {links_created} dynamic links for {memory_id}")

    return links_created


async def traverse_graph(
    graph_driver,
    start_memory_id: str,
    max_depth: int = 2,
    relationship_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Traverse memory graph from starting node.

    Args:
        graph_driver: Neo4j driver instance
        start_memory_id: Starting memory ID
        max_depth: Maximum traversal depth
        relationship_types: Filter by relationship types (default: all)

    Returns:
        List of connected memories with relationship info
    """
    if not graph_driver:
        logger.warning("Graph traversal requires Neo4j")
        return []

    if relationship_types is None:
        relationship_types = ["RELATES_TO", "REFERENCES", "CONTRADICTS"]

    try:
        with graph_driver.session() as session:
            # Cypher query for graph traversal
            rel_pattern = "|".join(relationship_types)

            result = session.run(f"""
                MATCH path = (start:Memory {{id: $start_id}})-[r:{rel_pattern}*1..{max_depth}]-(connected:Memory)
                WHERE all(rel in relationships(path) WHERE rel.valid_until IS NULL)
                RETURN
                    connected.id AS id,
                    connected.content AS content,
                    connected.importance_score AS importance,
                    length(path) AS distance,
                    [rel in relationships(path) | type(rel)] AS relationship_chain,
                    [rel in relationships(path) | rel.link_score] AS score_chain
                ORDER BY distance ASC, importance DESC
                LIMIT 20
            """, {'start_id': start_memory_id})

            connected_memories = []
            for record in result:
                connected_memories.append({
                    'memory_id': record['id'],
                    'content': record['content'],
                    'importance': record['importance'],
                    'graph_distance': record['distance'],
                    'relationship_path': record['relationship_chain'],
                    'link_scores': record['score_chain']
                })

            logger.info(f"Graph traversal from {start_memory_id} found {len(connected_memories)} connected memories")
            return connected_memories

    except Exception as e:
        logger.error(f"Graph traversal failed: {e}")
        return []


async def enrich_with_graph_traversal(
    graph_driver,
    traverse_func,
    results: List[Dict[str, Any]],
    limit: int
) -> List[Dict[str, Any]]:
    """
    Enrich recall results with graph-connected memories.

    Uses the existing traverse_graph method to find related memories
    through the knowledge graph and adds them to results.

    Args:
        graph_driver: Neo4j driver instance
        traverse_func: Function to traverse graph
        results: Current recall results
        limit: Maximum total results

    Returns:
        Enriched results including graph-connected memories
    """
    if not graph_driver or not results:
        return results

    try:
        seen_ids = {r.get('memory_id') for r in results}
        graph_additions = []

        # Traverse from top results to find connected memories
        for result in results[:3]:  # Only traverse from top 3 to limit overhead
            memory_id = result.get('memory_id')
            if not memory_id:
                continue

            connected = await traverse_func(
                start_memory_id=memory_id,
                max_depth=1,  # Shallow traversal for performance
                relationship_types=["RELATES_TO", "REFERENCES"]
            )

            for conn in connected:
                conn_id = conn.get('memory_id')
                if conn_id and conn_id not in seen_ids:
                    seen_ids.add(conn_id)
                    # Add graph context to the result
                    conn['source'] = 'graph'
                    conn['graph_path_from'] = memory_id
                    conn['rank_score'] = conn.get('importance', 0.5) * 0.5  # Reduced weight for graph results
                    graph_additions.append(conn)

        if graph_additions:
            # Merge and re-sort
            results.extend(graph_additions[:limit - len(results)])
            results.sort(key=lambda x: x.get('rank_score', x.get('similarity_score', 0)), reverse=True)
            logger.info(f"Added {len(graph_additions)} graph-connected memories")

        return results[:limit]

    except Exception as e:
        logger.warning(f"Graph enrichment failed: {e}")
        return results


async def temporal_query(
    sqlite_conn: sqlite3.Connection,
    agent_id: str,
    as_of_time: str,
    query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query memories as they existed at a specific point in time (Zep pattern).

    Args:
        sqlite_conn: SQLite connection
        agent_id: Filter by agent
        as_of_time: ISO timestamp to query
        query: Optional search query

    Returns:
        Memories that were valid at the specified time
    """
    cursor = sqlite_conn.cursor()

    # SQL query with temporal validity check
    if query:
        cursor.execute('''
            SELECT id, content, timestamp, valid_from, valid_until, importance_score
            FROM nmf_entities
            WHERE agent_id = ?
            AND valid_from <= ?
            AND (valid_until IS NULL OR valid_until > ?)
            AND content LIKE ?
            ORDER BY importance_score DESC, timestamp DESC
            LIMIT 20
        ''', (agent_id, as_of_time, as_of_time, f'%{query}%'))
    else:
        cursor.execute('''
            SELECT id, content, timestamp, valid_from, valid_until, importance_score
            FROM nmf_entities
            WHERE agent_id = ?
            AND valid_from <= ?
            AND (valid_until IS NULL OR valid_until > ?)
            ORDER BY importance_score DESC, timestamp DESC
            LIMIT 20
        ''', (agent_id, as_of_time, as_of_time))

    results = []
    for row in cursor.fetchall():
        results.append({
            'memory_id': row[0],
            'content': row[1],
            'timestamp': row[2],
            'valid_from': row[3],
            'valid_until': row[4],
            'importance_score': row[5],
            'was_valid_at': as_of_time
        })

    logger.info(f"Temporal query found {len(results)} memories valid at {as_of_time}")
    return results


__all__ = [
    'create_graph_node',
    'create_temporal_edge',
    'find_related_memories',
    'create_dynamic_links',
    'traverse_graph',
    'enrich_with_graph_traversal',
    'temporal_query',
]
