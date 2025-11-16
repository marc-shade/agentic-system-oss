#!/usr/bin/env python3
"""
Knowledge Graph Tools for Enhanced Memory MCP
Integrates ontology, graph traversal, temporal edges, and causal reasoning

Inspired by: "You're Doing Memory All Wrong" - Zapai
Provides MCP tools for knowledge graph operations
"""

import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from ontology_schema import (
    EntitySchema, RelationshipSchema, OntologyValidator,
    OntologyRegistry, EntityType, RelationType
)
from graph_traversal import GraphTraversal, TraversalDirection, TraversalStrategy

logger = logging.getLogger("knowledge-graph-tools")


class KnowledgeGraphManager:
    """
    Manager for knowledge graph operations
    Combines ontology validation with graph traversal
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.traversal = GraphTraversal(db_path)
        self.validator = OntologyValidator()

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def create_relationship(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        strength: float = 0.5,
        confidence: float = 0.5,
        is_causal: bool = False,
        causal_direction: Optional[str] = None,
        causal_strength: Optional[float] = None,
        bidirectional: bool = False,
        context: Optional[Dict] = None,
        evidence: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a relationship with full validation and temporal tracking

        Args:
            from_entity: Source entity name
            to_entity: Target entity name
            relation_type: Type of relationship (validated against ontology)
            strength: Relationship strength (0.0-1.0)
            confidence: Confidence in relationship (0.0-1.0)
            is_causal: Whether this is a causal relationship
            causal_direction: 'forward' or 'backward' if causal
            causal_strength: Strength of causal link (0.0-1.0)
            bidirectional: Create reverse relationship automatically
            context: Additional context as dict
            evidence: List of evidence strings

        Returns:
            Result dictionary with relationship ID and status
        """
        # Validate relationship schema
        rel_data = {
            'from_entity': from_entity,
            'to_entity': to_entity,
            'relation_type': relation_type,
            'strength': strength,
            'confidence': confidence,
            'is_causal': is_causal,
            'causal_direction': causal_direction,
            'causal_strength': causal_strength,
            'bidirectional': bidirectional,
            'context': context or {},
            'evidence': evidence or []
        }

        is_valid, model, error = self.validator.validate_relationship(rel_data)
        if not is_valid:
            return {
                'success': False,
                'error': f'Relationship validation failed: {error}'
            }

        # Get entity IDs
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM entities WHERE name = ?', (from_entity,))
        from_result = cursor.fetchone()
        if not from_result:
            conn.close()
            return {'success': False, 'error': f'From entity "{from_entity}" not found'}

        cursor.execute('SELECT id FROM entities WHERE name = ?', (to_entity,))
        to_result = cursor.fetchone()
        if not to_result:
            conn.close()
            return {'success': False, 'error': f'To entity "{to_entity}" not found'}

        from_id = from_result[0]
        to_id = to_result[0]

        # Insert relationship (trigger will handle bidirectional if needed)
        try:
            cursor.execute('''
                INSERT INTO relations (
                    from_entity_id, to_entity_id, relation_type,
                    strength, confidence,
                    is_causal, causal_direction, causal_strength,
                    bidirectional,
                    context_json, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                from_id, to_id, relation_type,
                strength, confidence,
                is_causal, causal_direction, causal_strength,
                bidirectional,
                json.dumps(context) if context else None,
                json.dumps(evidence) if evidence else None
            ))

            rel_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return {
                'success': True,
                'relationship_id': rel_id,
                'from_entity': from_entity,
                'to_entity': to_entity,
                'relation_type': relation_type,
                'bidirectional': bidirectional,
                'is_causal': is_causal,
                'message': f'Relationship created successfully'
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error creating relationship: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_entity_relationships(
        self,
        entity_name: str,
        direction: str = 'both',
        relation_types: Optional[List[str]] = None,
        min_strength: float = 0.0,
        only_causal: bool = False
    ) -> Dict[str, Any]:
        """
        Get all relationships for an entity with filtering

        Args:
            entity_name: Entity name
            direction: 'outbound', 'inbound', or 'both'
            relation_types: Filter by relationship types
            min_strength: Minimum relationship strength
            only_causal: Only return causal relationships

        Returns:
            Dictionary with relationships organized by direction
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get entity ID
        cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return {'success': False, 'error': 'Entity not found'}

        entity_id = result[0]

        relationships = {
            'outbound': [],
            'inbound': [],
            'total': 0
        }

        # Build filter clauses
        filters = ['r.strength >= ?']
        params_out = [entity_id, min_strength]
        params_in = [entity_id, min_strength]

        if relation_types:
            placeholders = ','.join(['?' for _ in relation_types])
            filters.append(f'r.relation_type IN ({placeholders})')
            params_out.extend(relation_types)
            params_in.extend(relation_types)

        if only_causal:
            filters.append('r.is_causal = 1')

        filter_clause = ' AND '.join(filters)

        # Get outbound relationships
        if direction in ['outbound', 'both']:
            cursor.execute(f'''
                SELECT
                    r.id, r.relation_type, e.name as to_entity,
                    r.strength, r.confidence,
                    r.is_causal, r.causal_strength,
                    r.created_at, r.bidirectional
                FROM relations r
                JOIN entities e ON r.to_entity_id = e.id
                WHERE r.from_entity_id = ? AND {filter_clause}
                ORDER BY r.strength DESC, r.created_at DESC
            ''', params_out)

            relationships['outbound'] = [
                {
                    'id': row[0],
                    'type': row[1],
                    'to_entity': row[2],
                    'strength': row[3],
                    'confidence': row[4],
                    'is_causal': bool(row[5]),
                    'causal_strength': row[6],
                    'created_at': row[7],
                    'bidirectional': bool(row[8])
                }
                for row in cursor.fetchall()
            ]

        # Get inbound relationships
        if direction in ['inbound', 'both']:
            cursor.execute(f'''
                SELECT
                    r.id, r.relation_type, e.name as from_entity,
                    r.strength, r.confidence,
                    r.is_causal, r.causal_strength,
                    r.created_at, r.bidirectional
                FROM relations r
                JOIN entities e ON r.from_entity_id = e.id
                WHERE r.to_entity_id = ? AND {filter_clause}
                ORDER BY r.strength DESC, r.created_at DESC
            ''', params_in)

            relationships['inbound'] = [
                {
                    'id': row[0],
                    'type': row[1],
                    'from_entity': row[2],
                    'strength': row[3],
                    'confidence': row[4],
                    'is_causal': bool(row[5]),
                    'causal_strength': row[6],
                    'created_at': row[7],
                    'bidirectional': bool(row[8])
                }
                for row in cursor.fetchall()
            ]

        relationships['total'] = len(relationships['outbound']) + len(relationships['inbound'])
        conn.close()

        return {
            'success': True,
            'entity': entity_name,
            'relationships': relationships
        }

    def get_causal_chain(
        self,
        entity_name: str,
        max_depth: int = 5,
        min_causal_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Get causal chain starting from entity
        Follows causes/caused_by relationships

        Args:
            entity_name: Starting entity
            max_depth: Maximum chain length
            min_causal_strength: Minimum causal strength to follow

        Returns:
            Causal chain with strengths
        """
        results = self.traversal.traverse(
            entity_name=entity_name,
            direction=TraversalDirection.OUTBOUND,
            max_depth=max_depth,
            strategy=TraversalStrategy.CAUSAL_CHAIN,
            min_strength=min_causal_strength
        )

        # Build chain representation
        chain = []
        for result in results:
            chain.append({
                'entity': result.entity_name,
                'type': result.entity_type,
                'relationship': result.relationship_type,
                'depth': result.depth,
                'strength': result.relationship_strength,
                'path': result.path
            })

        return {
            'success': True,
            'root_entity': entity_name,
            'chain_length': len(chain),
            'max_depth_reached': max(r.depth for r in results) if results else 0,
            'causal_chain': chain
        }

    def hybrid_search(
        self,
        query: str,
        semantic_limit: int = 10,
        graph_depth: int = 2,
        min_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Hybrid search: Semantic vector search + Graph traversal

        This is the key enhancement from the Zapai video:
        1. Use semantic search to find initial matches
        2. Expand with graph traversal to get connected context
        3. Return enriched results with relationship information

        Args:
            query: Search query
            semantic_limit: Initial semantic search results
            graph_depth: How many hops to traverse from each result
            min_strength: Minimum relationship strength

        Returns:
            Enriched search results with graph context
        """
        # This will be implemented to use the existing search_nodes functionality
        # plus graph traversal for each result
        conn = self._get_connection()
        cursor = conn.cursor()

        # Simple semantic search (would be enhanced with vector search in production)
        cursor.execute('''
            SELECT e.id, e.name, e.entity_type, e.tier
            FROM entities e
            WHERE e.name LIKE ? OR e.entity_type LIKE ?
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', semantic_limit))

        initial_results = cursor.fetchall()
        conn.close()

        # Enrich each result with graph context
        enriched_results = []
        for row in initial_results:
            entity_id, name, entity_type, tier = row

            # Get connected context
            context = self.traversal.get_connected_context(
                entity_name=name,
                max_depth=graph_depth,
                min_strength=min_strength
            )

            enriched_results.append({
                'entity': {
                    'id': entity_id,
                    'name': name,
                    'type': entity_type,
                    'tier': tier
                },
                'connected_entities': context['total_connected'],
                'context_depth': context['max_depth_explored'],
                'context_by_depth': context['context_by_depth'],
                'has_causal_links': len(context['causal_entities']) > 0
            })

        return {
            'success': True,
            'query': query,
            'semantic_results': len(initial_results),
            'total_connected_entities': sum(r['connected_entities'] for r in enriched_results),
            'results': enriched_results
        }


# === MCP TOOL REGISTRATION ===

def register_knowledge_graph_tools(app, db_path: Path):
    """Register knowledge graph tools with FastMCP app"""

    kg_manager = KnowledgeGraphManager(db_path)

    @app.tool()
    async def create_kg_relationship(
        from_entity: str,
        to_entity: str,
        relation_type: str,
        strength: float = 0.5,
        is_causal: bool = False,
        bidirectional: bool = False
    ) -> Dict[str, Any]:
        """
        Create a knowledge graph relationship with validation

        Args:
            from_entity: Source entity name
            to_entity: Target entity name
            relation_type: Relationship type (see ontology for valid types)
            strength: Relationship strength 0.0-1.0
            is_causal: Mark as causal relationship
            bidirectional: Create reverse relationship automatically

        Returns:
            Result with relationship ID
        """
        return kg_manager.create_relationship(
            from_entity=from_entity,
            to_entity=to_entity,
            relation_type=relation_type,
            strength=strength,
            is_causal=is_causal,
            bidirectional=bidirectional
        )

    @app.tool()
    async def get_kg_entity_context(
        entity_name: str,
        max_depth: int = 2,
        min_strength: float = 0.3
    ) -> Dict[str, Any]:
        """
        Get full connected context for an entity via graph traversal

        This provides the "connected context" that vector-only search misses

        Args:
            entity_name: Entity to start from
            max_depth: How many hops to traverse
            min_strength: Minimum relationship strength

        Returns:
            Connected context with relationships
        """
        return kg_manager.traversal.get_connected_context(
            entity_name=entity_name,
            max_depth=max_depth,
            min_strength=min_strength
        )

    @app.tool()
    async def get_causal_chain(
        entity_name: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Get causal chain from entity (cause-effect relationships)

        Tracks "why" something happened by following causal links

        Args:
            entity_name: Starting entity
            max_depth: Maximum chain length

        Returns:
            Causal chain with evidence
        """
        return kg_manager.get_causal_chain(
            entity_name=entity_name,
            max_depth=max_depth
        )

    @app.tool()
    async def kg_hybrid_search(
        query: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Hybrid search: Semantic + Graph traversal

        The key enhancement: Find entities semantically, then expand
        with graph traversal to get connected context

        Args:
            query: Search query
            depth: Graph traversal depth

        Returns:
            Enriched results with graph context
        """
        return kg_manager.hybrid_search(
            query=query,
            graph_depth=depth
        )

    @app.tool()
    async def get_ontology_info() -> Dict[str, Any]:
        """
        Get knowledge graph ontology information

        Returns valid entity types, relationship types, and schema info
        """
        return OntologyRegistry.get_schema_info()

    logger.info("✅ Knowledge Graph tools registered")
