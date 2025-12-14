#!/usr/bin/env python3
"""
GraphRAG: Relationship-Aware Retrieval for Enhanced Memory
============================================================

Lightweight GraphRAG implementation compatible with Qdrant vector store.
Adds graph-based context expansion to existing vector search.

Architecture:
- SQLite for entity relationships (relations table)
- Qdrant for vector embeddings (existing setup)
- Hybrid retrieval: Vector search + Graph expansion + Re-ranking

Research basis:
- Microsoft GraphRAG: Knowledge graph-based retrieval
- "You're Doing Memory All Wrong" (Zapai): Graph traversal patterns
- Anthropic Contextual Retrieval: Context-aware chunk enhancement

Usage:
    from graph_rag import GraphRAG

    rag = GraphRAG()

    # Basic relationship management
    rag.add_relationship(source_id=1, target_id=2, rel_type="causes", weight=0.8)

    # Graph-enhanced search
    results = rag.graph_enhanced_search(
        query="TRAP framework",
        include_neighbors=True,
        depth=2
    )

    # Auto-extract relationships from observations
    rag.extract_all_relationships()
"""

import sqlite3
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json

# Try to import Qdrant client (optional - falls back to SQLite-only)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("Warning: qdrant-client not available. Using SQLite-only mode.")


@dataclass
class GraphNode:
    """Entity node in knowledge graph"""
    entity_id: int
    name: str
    entity_type: str
    tier: str
    created_at: datetime
    salience_score: float = 0.5


@dataclass
class GraphEdge:
    """Relationship edge in knowledge graph"""
    edge_id: int
    from_entity_id: int
    to_entity_id: int
    relation_type: str
    weight: float
    created_at: datetime
    is_causal: bool = False
    context: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Enhanced search result with graph context"""
    entity_id: int
    entity_name: str
    entity_type: str
    content: str
    vector_score: float = 0.0
    graph_score: float = 0.0
    combined_score: float = 0.0
    neighbors: List[Dict[str, Any]] = None
    path_from_root: Optional[List[str]] = None

    def __post_init__(self):
        if self.neighbors is None:
            self.neighbors = []


class GraphRAG:
    """
    GraphRAG implementation for enhanced-memory system

    Provides relationship-aware retrieval with:
    - Entity relationship management
    - Graph traversal and expansion
    - Hybrid vector + graph search
    - Automatic relationship extraction
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "enhanced_memory"
    ):
        """
        Initialize GraphRAG

        Args:
            db_path: Path to SQLite database (default: ~/.claude/enhanced_memories/memory.db)
            qdrant_url: Qdrant server URL
            collection_name: Qdrant collection name
        """
        if db_path is None:
            db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

        self.db_path = Path(db_path)
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name

        # Initialize database connection
        self._init_database()

        # Initialize Qdrant if available
        self.qdrant_client = None
        if QDRANT_AVAILABLE:
            try:
                self.qdrant_client = QdrantClient(url=qdrant_url)
                print(f"Connected to Qdrant at {qdrant_url}")
            except Exception as e:
                print(f"Could not connect to Qdrant: {e}")
                print("Falling back to SQLite-only mode")

    def _init_database(self):
        """Initialize or upgrade database schema for GraphRAG"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if relations table needs upgrade
        cursor.execute("PRAGMA table_info(relations)")
        columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns for enhanced GraphRAG
        if 'weight' not in columns:
            print("Upgrading relations table schema...")
            cursor.execute('ALTER TABLE relations ADD COLUMN weight REAL DEFAULT 1.0')

        if 'is_causal' not in columns:
            cursor.execute('ALTER TABLE relations ADD COLUMN is_causal BOOLEAN DEFAULT 0')

        if 'context' not in columns:
            cursor.execute('ALTER TABLE relations ADD COLUMN context TEXT')  # JSON

        # Create index for faster graph traversal
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_relations_from
            ON relations(from_entity_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_relations_to
            ON relations(to_entity_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_relations_type
            ON relations(relation_type)
        ''')

        # Create table for tracking relationship extraction
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationship_extraction_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                relationships_found INTEGER,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id)
            )
        ''')

        conn.commit()
        conn.close()
        print("Database schema ready for GraphRAG")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==================== Relationship Management ====================

    def add_relationship(
        self,
        source_id: int,
        target_id: int,
        rel_type: str,
        weight: float = 1.0,
        is_causal: bool = False,
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add relationship edge between entities

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            rel_type: Relationship type (causes, relates_to, part_of, implements, extends)
            weight: Relationship strength (0.0-1.0)
            is_causal: Whether this is a causal relationship
            context: Additional context metadata (stored as JSON)

        Returns:
            Relationship ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if relationship already exists
        cursor.execute('''
            SELECT id FROM relations
            WHERE from_entity_id = ? AND to_entity_id = ? AND relation_type = ?
        ''', (source_id, target_id, rel_type))

        existing = cursor.fetchone()
        if existing:
            # Update weight if relationship exists
            cursor.execute('''
                UPDATE relations
                SET weight = ?, is_causal = ?, context = ?
                WHERE id = ?
            ''', (weight, is_causal, json.dumps(context) if context else None, existing['id']))
            rel_id = existing['id']
        else:
            # Insert new relationship
            cursor.execute('''
                INSERT INTO relations (from_entity_id, to_entity_id, relation_type, weight, is_causal, context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (source_id, target_id, rel_type, weight, is_causal, json.dumps(context) if context else None))
            rel_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return rel_id

    def get_neighbors(
        self,
        entity_id: int,
        rel_type: Optional[str] = None,
        direction: str = "both",  # "outbound", "inbound", "both"
        min_weight: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring entities

        Args:
            entity_id: Entity to get neighbors for
            rel_type: Filter by relationship type
            direction: Traversal direction
            min_weight: Minimum relationship weight

        Returns:
            List of neighbor dictionaries with relationship info
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        neighbors = []

        # Outbound neighbors (entity -> others)
        if direction in ["outbound", "both"]:
            query = '''
                SELECT
                    r.id as rel_id,
                    r.to_entity_id as neighbor_id,
                    e.name as neighbor_name,
                    e.entity_type,
                    e.tier,
                    e.salience_score,
                    r.relation_type,
                    r.weight,
                    r.is_causal,
                    r.context,
                    'outbound' as direction
                FROM relations r
                JOIN entities e ON r.to_entity_id = e.id
                WHERE r.from_entity_id = ? AND r.weight >= ?
            '''
            params = [entity_id, min_weight]

            if rel_type:
                query += " AND r.relation_type = ?"
                params.append(rel_type)

            cursor.execute(query, params)
            neighbors.extend([dict(row) for row in cursor.fetchall()])

        # Inbound neighbors (others -> entity)
        if direction in ["inbound", "both"]:
            query = '''
                SELECT
                    r.id as rel_id,
                    r.from_entity_id as neighbor_id,
                    e.name as neighbor_name,
                    e.entity_type,
                    e.tier,
                    e.salience_score,
                    r.relation_type,
                    r.weight,
                    r.is_causal,
                    r.context,
                    'inbound' as direction
                FROM relations r
                JOIN entities e ON r.from_entity_id = e.id
                WHERE r.to_entity_id = ? AND r.weight >= ?
            '''
            params = [entity_id, min_weight]

            if rel_type:
                query += " AND r.relation_type = ?"
                params.append(rel_type)

            cursor.execute(query, params)
            neighbors.extend([dict(row) for row in cursor.fetchall()])

        conn.close()
        return neighbors

    # ==================== Graph Traversal ====================

    def expand_graph_context(
        self,
        entity_ids: List[int],
        depth: int = 2,
        min_weight: float = 0.3
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Expand context by traversing graph from entity IDs

        Args:
            entity_ids: Starting entity IDs
            depth: Maximum traversal depth
            min_weight: Minimum relationship weight to follow

        Returns:
            Dictionary mapping entity_id -> list of connected entities
        """
        context_map = {}
        visited = set()

        for entity_id in entity_ids:
            context_map[entity_id] = []
            queue = [(entity_id, 0)]  # (entity_id, current_depth)

            while queue:
                current_id, current_depth = queue.pop(0)

                if current_id in visited or current_depth >= depth:
                    continue

                visited.add(current_id)

                # Get neighbors
                neighbors = self.get_neighbors(
                    current_id,
                    direction="both",
                    min_weight=min_weight
                )

                for neighbor in neighbors:
                    neighbor_id = neighbor['neighbor_id']
                    if neighbor_id not in visited:
                        context_map[entity_id].append({
                            'entity_id': neighbor_id,
                            'name': neighbor['neighbor_name'],
                            'type': neighbor['entity_type'],
                            'relation': neighbor['relation_type'],
                            'weight': neighbor['weight'],
                            'depth': current_depth + 1,
                            'is_causal': neighbor['is_causal']
                        })
                        queue.append((neighbor_id, current_depth + 1))

        return context_map

    # ==================== Relationship Extraction ====================

    def extract_relationships_from_text(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract relationships from text using pattern matching

        Patterns:
        - "X causes Y"
        - "X implements Y"
        - "X relates to Y"
        - "X is part of Y"
        - "X extends Y"

        Args:
            text: Text to analyze

        Returns:
            List of (entity1, relation_type, entity2) tuples
        """
        relationships = []

        # Define extraction patterns
        patterns = [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+causes\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'causes'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+implements\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'implements'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+relates\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'relates_to'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+part\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'part_of'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+extends\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'extends'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+uses\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'uses'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+depends\s+on\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'depends_on'),
        ]

        for pattern, rel_type in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entity1, entity2 = match
                relationships.append((entity1.strip(), rel_type, entity2.strip()))

        return relationships

    def extract_relationships_from_entity(self, entity_id: int) -> int:
        """
        Extract and store relationships from an entity's observations

        Args:
            entity_id: Entity ID to process

        Returns:
            Number of relationships extracted
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get entity observations
        cursor.execute('''
            SELECT content FROM observations WHERE entity_id = ?
        ''', (entity_id,))

        observations = cursor.fetchall()
        all_text = " ".join([obs['content'] for obs in observations])

        # Extract relationships
        extracted = self.extract_relationships_from_text(all_text)

        count = 0
        for entity1_name, rel_type, entity2_name in extracted:
            # Find entity IDs by name (fuzzy match)
            cursor.execute('''
                SELECT id FROM entities WHERE name LIKE ? LIMIT 1
            ''', (f"%{entity1_name}%",))
            entity1 = cursor.fetchone()

            cursor.execute('''
                SELECT id FROM entities WHERE name LIKE ? LIMIT 1
            ''', (f"%{entity2_name}%",))
            entity2 = cursor.fetchone()

            if entity1 and entity2:
                # Add relationship
                self.add_relationship(
                    source_id=entity1['id'],
                    target_id=entity2['id'],
                    rel_type=rel_type,
                    weight=0.5,  # Medium confidence for auto-extracted
                    is_causal=(rel_type == 'causes')
                )
                count += 1

        # Log extraction
        cursor.execute('''
            INSERT INTO relationship_extraction_log (entity_id, relationships_found)
            VALUES (?, ?)
        ''', (entity_id, count))

        conn.commit()
        conn.close()

        return count

    def extract_all_relationships(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Extract relationships from all entities

        Args:
            limit: Maximum entities to process (None = all)

        Returns:
            Statistics dictionary
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get entities that haven't been processed
        query = '''
            SELECT e.id, e.name
            FROM entities e
            LEFT JOIN relationship_extraction_log l ON e.id = l.entity_id
            WHERE l.id IS NULL
        '''

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        entities = cursor.fetchall()
        conn.close()

        stats = {
            'total_processed': 0,
            'total_relationships': 0,
            'entities_with_relationships': 0
        }

        for entity in entities:
            count = self.extract_relationships_from_entity(entity['id'])
            stats['total_processed'] += 1
            stats['total_relationships'] += count
            if count > 0:
                stats['entities_with_relationships'] += 1

            if stats['total_processed'] % 100 == 0:
                print(f"Processed {stats['total_processed']} entities...")

        return stats

    # ==================== Graph-Enhanced Search ====================

    def graph_enhanced_search(
        self,
        query: str,
        include_neighbors: bool = True,
        depth: int = 2,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Graph-enhanced hybrid search

        Process:
        1. Vector search in Qdrant for initial results
        2. Expand context via graph traversal
        3. Re-rank by combined vector + graph centrality scores

        Args:
            query: Search query
            include_neighbors: Include graph neighbors in results
            depth: Graph expansion depth
            vector_weight: Weight for vector similarity (0.0-1.0)
            graph_weight: Weight for graph centrality (0.0-1.0)
            limit: Number of results to return

        Returns:
            List of enhanced search results
        """
        # Step 1: Vector search (if Qdrant available)
        if self.qdrant_client:
            results = self._vector_search(query, limit=limit * 2)  # Over-retrieve
        else:
            # Fallback to SQLite text search
            results = self._text_search(query, limit=limit * 2)

        if not results:
            return []

        # Step 2: Expand with graph context
        if include_neighbors:
            entity_ids = [r.entity_id for r in results]
            context_map = self.expand_graph_context(entity_ids, depth=depth)

            # Add graph context to results
            for result in results:
                if result.entity_id in context_map:
                    result.neighbors = context_map[result.entity_id]

        # Step 3: Calculate graph scores
        for result in results:
            # Graph score based on:
            # - Number of high-quality connections
            # - Salience of connected entities
            # - Causal relationship presence
            graph_score = 0.0
            if result.neighbors:
                for neighbor in result.neighbors:
                    # Weight by relationship strength and depth
                    weight = neighbor['weight'] * (1.0 / (neighbor['depth'] + 1))
                    graph_score += weight

                    # Bonus for causal relationships
                    if neighbor['is_causal']:
                        graph_score += 0.2

                # Normalize by number of neighbors
                graph_score = min(1.0, graph_score / max(1, len(result.neighbors)))

            result.graph_score = graph_score

            # Combined score
            result.combined_score = (
                vector_weight * result.vector_score +
                graph_weight * result.graph_score
            )

        # Step 4: Re-rank by combined score
        results.sort(key=lambda x: x.combined_score, reverse=True)

        return results[:limit]

    def _vector_search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Search using Qdrant vector similarity

        Note: Requires embedding model. For now, returns empty.
        Real implementation would use sentence-transformers.
        """
        # TODO: Implement with actual embeddings
        # For now, fall back to text search
        return self._text_search(query, limit)

    def _text_search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """
        Fallback text search using SQLite FTS or LIKE
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Search in entity names and observations
        # Use GROUP_CONCAT to combine observations and GROUP BY to deduplicate
        cursor.execute('''
            SELECT
                e.id,
                e.name,
                e.entity_type,
                e.salience_score,
                GROUP_CONCAT(o.content, ' | ') as all_content
            FROM entities e
            JOIN observations o ON e.id = o.entity_id
            WHERE e.name LIKE ? OR o.content LIKE ?
            GROUP BY e.id
            ORDER BY e.salience_score DESC
            LIMIT ?
        ''', (f"%{query}%", f"%{query}%", limit))

        rows = cursor.fetchall()
        conn.close()

        results = []
        seen_ids = set()
        for row in rows:
            # Skip duplicates
            if row['id'] in seen_ids:
                continue
            seen_ids.add(row['id'])

            # Simple relevance score based on match position
            score = 0.5  # Base score
            if query.lower() in row['name'].lower():
                score += 0.3
            if row['all_content'] and query.lower() in row['all_content'].lower():
                score += 0.2

            results.append(SearchResult(
                entity_id=row['id'],
                entity_name=row['name'],
                entity_type=row['entity_type'],
                content=row['all_content'][:500] if row['all_content'] else "",  # Truncate
                vector_score=min(1.0, score),
                graph_score=0.0,
                combined_score=min(1.0, score)
            ))

        return results

    # ==================== Graph Analytics ====================

    def build_local_graph(self, entity_ids: List[int]) -> Dict[str, Any]:
        """
        Build subgraph for visualization or analysis

        Args:
            entity_ids: Entity IDs to include

        Returns:
            Graph structure with nodes and edges
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get nodes
        placeholders = ','.join(['?' for _ in entity_ids])
        cursor.execute(f'''
            SELECT id, name, entity_type, tier, salience_score
            FROM entities
            WHERE id IN ({placeholders})
        ''', entity_ids)

        nodes = [dict(row) for row in cursor.fetchall()]

        # Get edges between these entities
        cursor.execute(f'''
            SELECT
                id, from_entity_id, to_entity_id,
                relation_type, weight, is_causal
            FROM relations
            WHERE from_entity_id IN ({placeholders})
            AND to_entity_id IN ({placeholders})
        ''', entity_ids + entity_ids)

        edges = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get GraphRAG statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Entity count
        cursor.execute('SELECT COUNT(*) as count FROM entities')
        entity_count = cursor.fetchone()['count']

        # Relationship count
        cursor.execute('SELECT COUNT(*) as count FROM relations')
        relation_count = cursor.fetchone()['count']

        # Relationship types
        cursor.execute('''
            SELECT relation_type, COUNT(*) as count
            FROM relations
            GROUP BY relation_type
            ORDER BY count DESC
        ''')
        rel_types = [dict(row) for row in cursor.fetchall()]

        # Average relationships per entity
        if entity_count > 0:
            avg_rels = relation_count / entity_count
        else:
            avg_rels = 0

        # Causal relationships
        cursor.execute('SELECT COUNT(*) as count FROM relations WHERE is_causal = 1')
        causal_count = cursor.fetchone()['count']

        conn.close()

        return {
            'entities': entity_count,
            'relationships': relation_count,
            'relationship_types': rel_types,
            'avg_relationships_per_entity': round(avg_rels, 2),
            'causal_relationships': causal_count,
            'qdrant_available': QDRANT_AVAILABLE,
            'qdrant_connected': self.qdrant_client is not None
        }


def main():
    """CLI interface for GraphRAG"""
    import argparse

    parser = argparse.ArgumentParser(description="GraphRAG for Enhanced Memory")
    parser.add_argument('command', choices=[
        'extract', 'search', 'stats', 'neighbors', 'add-rel'
    ], help='Command to run')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--entity-id', type=int, help='Entity ID')
    parser.add_argument('--limit', type=int, default=10, help='Result limit')
    parser.add_argument('--depth', type=int, default=2, help='Graph depth')
    parser.add_argument('--source', type=int, help='Source entity ID')
    parser.add_argument('--target', type=int, help='Target entity ID')
    parser.add_argument('--rel-type', help='Relationship type')

    args = parser.parse_args()

    rag = GraphRAG()

    if args.command == 'extract':
        print("Extracting relationships from entities...")
        stats = rag.extract_all_relationships(limit=args.limit if args.limit != 10 else None)
        print(f"\n=== Extraction Complete ===")
        print(f"Processed: {stats['total_processed']} entities")
        print(f"Found: {stats['total_relationships']} relationships")
        print(f"Entities with relationships: {stats['entities_with_relationships']}")

    elif args.command == 'search':
        if not args.query:
            print("Error: --query required")
            return

        print(f"Searching for: {args.query}")
        results = rag.graph_enhanced_search(args.query, depth=args.depth, limit=args.limit)

        print(f"\n=== Found {len(results)} Results ===\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.entity_name} ({result.entity_type})")
            print(f"   Vector: {result.vector_score:.3f} | Graph: {result.graph_score:.3f} | Combined: {result.combined_score:.3f}")
            if result.neighbors:
                print(f"   Neighbors: {len(result.neighbors)}")
                for neighbor in result.neighbors[:3]:
                    print(f"     - {neighbor['name']} ({neighbor['relation']})")
            print(f"   Content: {result.content[:200]}...")
            print()

    elif args.command == 'stats':
        stats = rag.get_statistics()
        print("\n=== GraphRAG Statistics ===")
        print(f"Entities: {stats['entities']}")
        print(f"Relationships: {stats['relationships']}")
        print(f"Avg relationships/entity: {stats['avg_relationships_per_entity']}")
        print(f"Causal relationships: {stats['causal_relationships']}")
        print(f"\nRelationship Types:")
        for rel in stats['relationship_types'][:10]:
            print(f"  {rel['relation_type']}: {rel['count']}")
        print(f"\nQdrant: {'Connected' if stats['qdrant_connected'] else 'Not connected'}")

    elif args.command == 'neighbors':
        if not args.entity_id:
            print("Error: --entity-id required")
            return

        neighbors = rag.get_neighbors(args.entity_id, direction="both")
        print(f"\n=== Neighbors for Entity {args.entity_id} ===")
        print(f"Found {len(neighbors)} neighbors\n")

        for neighbor in neighbors[:20]:
            print(f"- {neighbor['neighbor_name']} ({neighbor['entity_type']})")
            print(f"  Relation: {neighbor['relation_type']} ({neighbor['direction']})")
            print(f"  Weight: {neighbor['weight']:.2f}")
            if neighbor['is_causal']:
                print(f"  [CAUSAL]")
            print()

    elif args.command == 'add-rel':
        if not all([args.source, args.target, args.rel_type]):
            print("Error: --source, --target, and --rel-type required")
            return

        rel_id = rag.add_relationship(
            source_id=args.source,
            target_id=args.target,
            rel_type=args.rel_type,
            weight=1.0
        )
        print(f"Added relationship {rel_id}: {args.source} --[{args.rel_type}]--> {args.target}")


if __name__ == "__main__":
    main()
