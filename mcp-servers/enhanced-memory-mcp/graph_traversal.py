#!/usr/bin/env python3
"""
Bi-Directional Graph Traversal for Knowledge Graph Memory
Implements temporal edge modeling and multi-hop relationship traversal

Inspired by: "You're Doing Memory All Wrong" - Zapai
Key features:
- Bi-directional traversal (navigate relationships both ways)
- Temporal edge filtering (query relationships by time)
- Multi-hop traversal (explore connected context)
- Causal chain tracking (follow cause-effect relationships)
"""

import sqlite3
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TraversalDirection(str, Enum):
    """Direction for graph traversal"""
    OUTBOUND = "outbound"  # Follow edges from entity
    INBOUND = "inbound"    # Follow edges to entity
    BOTH = "both"          # Traverse in both directions


class TraversalStrategy(str, Enum):
    """Strategy for multi-hop traversal"""
    BREADTH_FIRST = "breadth_first"  # Explore all neighbors at current depth first
    DEPTH_FIRST = "depth_first"      # Explore as deep as possible before backtracking
    CAUSAL_CHAIN = "causal_chain"    # Follow causal relationships specifically


@dataclass
class TraversalResult:
    """Result of a graph traversal operation"""
    entity_id: int
    entity_name: str
    entity_type: str
    depth: int  # How many hops from root
    path: List[str]  # Path from root to this entity
    relationship_type: Optional[str] = None
    relationship_timestamp: Optional[datetime] = None
    relationship_strength: float = 0.0
    is_causal: bool = False


class GraphTraversal:
    """
    Bi-directional graph traversal with temporal filtering
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def traverse(
        self,
        entity_name: str,
        direction: TraversalDirection = TraversalDirection.BOTH,
        max_depth: int = 3,
        relation_types: Optional[List[str]] = None,
        temporal_filter: Optional[Dict[str, datetime]] = None,
        strategy: TraversalStrategy = TraversalStrategy.BREADTH_FIRST,
        min_strength: float = 0.0
    ) -> List[TraversalResult]:
        """
        Traverse graph from entity with various filters and strategies

        Args:
            entity_name: Starting entity name
            direction: Traversal direction (outbound, inbound, both)
            max_depth: Maximum traversal depth (hops)
            relation_types: Filter by relationship types
            temporal_filter: Filter by timestamps {"from": datetime, "to": datetime}
            strategy: Traversal strategy (BFS, DFS, causal)
            min_strength: Minimum relationship strength

        Returns:
            List of traversal results
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get root entity ID
        cursor.execute('SELECT id, entity_type FROM entities WHERE name = ?', (entity_name,))
        root = cursor.fetchone()
        if not root:
            conn.close()
            return []

        root_id = root['id']
        root_type = root['entity_type']

        # Initialize traversal
        results = []
        visited: Set[int] = set()
        queue: List[Tuple[int, int, List[str]]] = [(root_id, 0, [entity_name])]  # (entity_id, depth, path)

        # Choose traversal method based on strategy
        if strategy == TraversalStrategy.BREADTH_FIRST:
            results = self._breadth_first_traverse(
                cursor, queue, visited, max_depth, direction,
                relation_types, temporal_filter, min_strength
            )
        elif strategy == TraversalStrategy.DEPTH_FIRST:
            results = self._depth_first_traverse(
                cursor, queue, visited, max_depth, direction,
                relation_types, temporal_filter, min_strength
            )
        elif strategy == TraversalStrategy.CAUSAL_CHAIN:
            results = self._causal_chain_traverse(
                cursor, root_id, visited, max_depth,
                temporal_filter, min_strength
            )

        conn.close()
        return results

    def _breadth_first_traverse(
        self,
        cursor: sqlite3.Cursor,
        queue: List[Tuple[int, int, List[str]]],
        visited: Set[int],
        max_depth: int,
        direction: TraversalDirection,
        relation_types: Optional[List[str]],
        temporal_filter: Optional[Dict[str, datetime]],
        min_strength: float
    ) -> List[TraversalResult]:
        """Breadth-first traversal implementation"""
        results = []

        while queue:
            current_id, depth, path = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)

            # Get neighbors
            neighbors = self._get_neighbors(
                cursor, current_id, direction, relation_types,
                temporal_filter, min_strength
            )

            for neighbor in neighbors:
                if neighbor['entity_id'] not in visited and depth < max_depth:
                    new_path = path + [neighbor['entity_name']]

                    # Add to results
                    results.append(TraversalResult(
                        entity_id=neighbor['entity_id'],
                        entity_name=neighbor['entity_name'],
                        entity_type=neighbor['entity_type'],
                        depth=depth + 1,
                        path=new_path,
                        relationship_type=neighbor['relation_type'],
                        relationship_timestamp=neighbor.get('created_at'),
                        relationship_strength=neighbor.get('strength', 0.0),
                        is_causal=neighbor.get('is_causal', False)
                    ))

                    # Add to queue for next level
                    queue.append((neighbor['entity_id'], depth + 1, new_path))

        return results

    def _depth_first_traverse(
        self,
        cursor: sqlite3.Cursor,
        queue: List[Tuple[int, int, List[str]]],
        visited: Set[int],
        max_depth: int,
        direction: TraversalDirection,
        relation_types: Optional[List[str]],
        temporal_filter: Optional[Dict[str, datetime]],
        min_strength: float
    ) -> List[TraversalResult]:
        """Depth-first traversal implementation"""
        results = []

        while queue:
            current_id, depth, path = queue.pop()  # Pop from end for DFS

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Get neighbors
            neighbors = self._get_neighbors(
                cursor, current_id, direction, relation_types,
                temporal_filter, min_strength
            )

            for neighbor in neighbors:
                if neighbor['entity_id'] not in visited:
                    new_path = path + [neighbor['entity_name']]

                    # Add to results
                    results.append(TraversalResult(
                        entity_id=neighbor['entity_id'],
                        entity_name=neighbor['entity_name'],
                        entity_type=neighbor['entity_type'],
                        depth=depth + 1,
                        path=new_path,
                        relationship_type=neighbor['relation_type'],
                        relationship_timestamp=neighbor.get('created_at'),
                        relationship_strength=neighbor.get('strength', 0.0),
                        is_causal=neighbor.get('is_causal', False)
                    ))

                    # Push to stack for DFS
                    queue.append((neighbor['entity_id'], depth + 1, new_path))

        return results

    def _causal_chain_traverse(
        self,
        cursor: sqlite3.Cursor,
        root_id: int,
        visited: Set[int],
        max_depth: int,
        temporal_filter: Optional[Dict[str, datetime]],
        min_strength: float
    ) -> List[TraversalResult]:
        """
        Follow causal chains (causes/caused_by relationships)
        Specifically designed for tracking cause-effect sequences
        """
        results = []
        queue = [(root_id, 0, [])]

        # Causal relationship types
        causal_types = ['causes', 'caused_by', 'triggered_by', 'resulted_in']

        while queue:
            current_id, depth, path = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Get causal relationships only
            neighbors = self._get_neighbors(
                cursor, current_id,
                TraversalDirection.OUTBOUND,  # Follow forward causality
                causal_types,
                temporal_filter,
                min_strength
            )

            # Filter to only truly causal relationships
            causal_neighbors = [n for n in neighbors if n.get('is_causal', False)]

            for neighbor in causal_neighbors:
                if neighbor['entity_id'] not in visited:
                    new_path = path + [(
                        neighbor['entity_name'],
                        neighbor['relation_type'],
                        neighbor.get('causal_strength', 0.0)
                    )]

                    results.append(TraversalResult(
                        entity_id=neighbor['entity_id'],
                        entity_name=neighbor['entity_name'],
                        entity_type=neighbor['entity_type'],
                        depth=depth + 1,
                        path=[str(p) for p in new_path],
                        relationship_type=neighbor['relation_type'],
                        relationship_timestamp=neighbor.get('created_at'),
                        relationship_strength=neighbor.get('strength', 0.0),
                        is_causal=True
                    ))

                    queue.append((neighbor['entity_id'], depth + 1, new_path))

        return results

    def _get_neighbors(
        self,
        cursor: sqlite3.Cursor,
        entity_id: int,
        direction: TraversalDirection,
        relation_types: Optional[List[str]],
        temporal_filter: Optional[Dict[str, datetime]],
        min_strength: float
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring entities with filters

        Returns enriched relationships with entity information
        """
        neighbors = []

        # Build query based on direction
        if direction in [TraversalDirection.OUTBOUND, TraversalDirection.BOTH]:
            # Outbound: entity -> other
            query = '''
                SELECT
                    r.to_entity_id as entity_id,
                    e.name as entity_name,
                    e.entity_type as entity_type,
                    r.relation_type,
                    r.created_at,
                    r.strength,
                    r.is_causal,
                    r.causal_strength,
                    'outbound' as direction
                FROM relations r
                JOIN entities e ON r.to_entity_id = e.id
                WHERE r.from_entity_id = ?
            '''
            neighbors.extend(self._execute_neighbor_query(
                cursor, query, entity_id, relation_types, temporal_filter, min_strength
            ))

        if direction in [TraversalDirection.INBOUND, TraversalDirection.BOTH]:
            # Inbound: other -> entity
            query = '''
                SELECT
                    r.from_entity_id as entity_id,
                    e.name as entity_name,
                    e.entity_type as entity_type,
                    r.relation_type,
                    r.created_at,
                    r.strength,
                    r.is_causal,
                    r.causal_strength,
                    'inbound' as direction
                FROM relations r
                JOIN entities e ON r.from_entity_id = e.id
                WHERE r.to_entity_id = ?
            '''
            neighbors.extend(self._execute_neighbor_query(
                cursor, query, entity_id, relation_types, temporal_filter, min_strength
            ))

        return neighbors

    def _execute_neighbor_query(
        self,
        cursor: sqlite3.Cursor,
        base_query: str,
        entity_id: int,
        relation_types: Optional[List[str]],
        temporal_filter: Optional[Dict[str, datetime]],
        min_strength: float
    ) -> List[Dict[str, Any]]:
        """Execute neighbor query with filters"""
        params = [entity_id]
        filters = []

        # Relationship type filter
        if relation_types:
            placeholders = ','.join(['?' for _ in relation_types])
            filters.append(f"r.relation_type IN ({placeholders})")
            params.extend(relation_types)

        # Temporal filter
        if temporal_filter:
            if 'from' in temporal_filter:
                filters.append("r.created_at >= ?")
                params.append(temporal_filter['from'])
            if 'to' in temporal_filter:
                filters.append("r.created_at <= ?")
                params.append(temporal_filter['to'])

        # Strength filter
        if min_strength > 0:
            filters.append("r.strength >= ?")
            params.append(min_strength)

        # Add filters to query
        if filters:
            base_query += " AND " + " AND ".join(filters)

        cursor.execute(base_query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_connected_context(
        self,
        entity_name: str,
        max_depth: int = 2,
        min_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Get full connected context for an entity
        Returns semantic neighborhood with relationships

        This is the key function for hybrid retrieval enhancement
        """
        results = self.traverse(
            entity_name=entity_name,
            direction=TraversalDirection.BOTH,
            max_depth=max_depth,
            strategy=TraversalStrategy.BREADTH_FIRST,
            min_strength=min_strength
        )

        # Organize by depth
        context_by_depth = {}
        for result in results:
            if result.depth not in context_by_depth:
                context_by_depth[result.depth] = []
            context_by_depth[result.depth].append({
                'name': result.entity_name,
                'type': result.entity_type,
                'relationship': result.relationship_type,
                'strength': result.relationship_strength,
                'path': result.path
            })

        return {
            'root': entity_name,
            'total_connected': len(results),
            'max_depth_explored': max(context_by_depth.keys()) if context_by_depth else 0,
            'context_by_depth': context_by_depth,
            'causal_entities': [r for r in results if r.is_causal]
        }

    def find_paths(
        self,
        from_entity: str,
        to_entity: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        Find all paths between two entities
        Useful for understanding relationships
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get entity IDs
        cursor.execute('SELECT id FROM entities WHERE name IN (?, ?)', (from_entity, to_entity))
        entities = cursor.fetchall()
        if len(entities) != 2:
            conn.close()
            return []

        from_id = entities[0]['id']
        to_id = entities[1]['id']

        # BFS to find all paths
        paths = []
        queue = [(from_id, [from_entity])]
        visited_in_path = set()

        while queue:
            current_id, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            if current_id == to_id:
                paths.append(path)
                continue

            # Get neighbors (outbound only for directed paths)
            neighbors = self._get_neighbors(
                cursor, current_id,
                TraversalDirection.OUTBOUND,
                None, None, 0.0
            )

            for neighbor in neighbors:
                if neighbor['entity_id'] not in visited_in_path:
                    new_path = path + [neighbor['entity_name']]
                    queue.append((neighbor['entity_id'], new_path))

        conn.close()
        return paths


if __name__ == "__main__":
    # Test graph traversal
    from pathlib import Path
    import sys

    # Use test database
    db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

    if not db_path.exists():
        print("Database not found. Run enhanced-memory-mcp first.")
        sys.exit(1)

    traversal = GraphTraversal(db_path)

    # Test traversal (replace with actual entity name from your database)
    print("=== Graph Traversal Test ===\n")
    print("Note: Replace 'test_entity' with an actual entity name from your database\n")

    # This will work once you have entities with relationships
    # For now, it demonstrates the API
