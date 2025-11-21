#!/usr/bin/env python3
"""
Comprehensive Tests for Knowledge Graph Enhancements

Tests:
- Ontology validation
- Bi-directional traversal
- Temporal edge filtering
- Causal chain tracking
- Hybrid retrieval
"""

import unittest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from ontology_schema import (
    EntitySchema, ConceptEntity, EpisodeEntity, SkillEntity,
    RelationshipSchema, OntologyValidator, EntityType, RelationType
)
from graph_traversal import GraphTraversal, TraversalDirection, TraversalStrategy
from knowledge_graph_tools import KnowledgeGraphManager


class TestOntologySchema(unittest.TestCase):
    """Test ontology validation and schemas"""

    def test_concept_entity_validation(self):
        """Test concept entity validation"""
        concept_data = {
            "name": "knowledge_graphs",
            "entity_type": "concept",
            "tier": "semantic",
            "definition": "Graph structures for representing knowledge",
            "related_concepts": ["vector_databases", "semantic_networks"],
            "observations": ["Used in AI systems"],
            "confidence_score": 0.9
        }

        is_valid, model, error = OntologyValidator.validate_entity(concept_data)

        self.assertTrue(is_valid, f"Validation failed: {error}")
        self.assertIsNotNone(model)
        self.assertEqual(model.name, "knowledge_graphs")
        self.assertEqual(model.entity_type, EntityType.CONCEPT)

    def test_relationship_validation(self):
        """Test relationship validation"""
        rel_data = {
            "from_entity": "knowledge_graphs",
            "to_entity": "better_retrieval",
            "relation_type": "causes",
            "strength": 0.85,
            "is_causal": True,
            "causal_direction": "forward",
            "causal_strength": 0.8
        }

        is_valid, model, error = OntologyValidator.validate_relationship(rel_data)

        self.assertTrue(is_valid, f"Validation failed: {error}")
        self.assertIsNotNone(model)
        self.assertEqual(model.relation_type, RelationType.CAUSES)
        self.assertTrue(model.is_causal)

    def test_invalid_causal_strength(self):
        """Test that causal_strength without is_causal fails"""
        rel_data = {
            "from_entity": "a",
            "to_entity": "b",
            "relation_type": "relates_to",
            "is_causal": False,
            "causal_strength": 0.8  # Invalid: not causal but has strength
        }

        is_valid, model, error = OntologyValidator.validate_relationship(rel_data)

        self.assertFalse(is_valid)
        self.assertIn("causal_strength", str(error).lower())


class TestGraphTraversal(unittest.TestCase):
    """Test graph traversal functionality"""

    def setUp(self):
        """Create temporary test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

        # Create test database with knowledge graph schema
        self._setup_test_database()

    def tearDown(self):
        """Clean up temporary database"""
        shutil.rmtree(self.temp_dir)

    def _setup_test_database(self):
        """Setup test database with sample data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create entities table
        cursor.execute('''
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                tier TEXT DEFAULT 'working'
            )
        ''')

        # Create enhanced relations table
        cursor.execute('''
            CREATE TABLE relations (
                id INTEGER PRIMARY KEY,
                from_entity_id INTEGER,
                to_entity_id INTEGER,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strength REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                is_causal BOOLEAN DEFAULT 0,
                causal_direction TEXT,
                causal_strength REAL,
                bidirectional BOOLEAN DEFAULT 0,
                FOREIGN KEY (from_entity_id) REFERENCES entities (id),
                FOREIGN KEY (to_entity_id) REFERENCES entities (id)
            )
        ''')

        # Insert test entities
        entities = [
            ("vector_search", "concept", "semantic"),
            ("knowledge_graphs", "concept", "semantic"),
            ("temporal_reasoning", "concept", "semantic"),
            ("improved_retrieval", "outcome", "episodic"),
            ("causal_tracking", "skill", "procedural"),
        ]

        for name, etype, tier in entities:
            cursor.execute(
                'INSERT INTO entities (name, entity_type, tier) VALUES (?, ?, ?)',
                (name, etype, tier)
            )

        # Insert test relationships
        # knowledge_graphs causes improved_retrieval
        cursor.execute('''
            INSERT INTO relations (
                from_entity_id, to_entity_id, relation_type,
                strength, is_causal, causal_direction, causal_strength
            ) VALUES (
                (SELECT id FROM entities WHERE name = 'knowledge_graphs'),
                (SELECT id FROM entities WHERE name = 'improved_retrieval'),
                'causes',
                0.9, 1, 'forward', 0.85
            )
        ''')

        # temporal_reasoning enables causal_tracking
        cursor.execute('''
            INSERT INTO relations (
                from_entity_id, to_entity_id, relation_type,
                strength, is_causal, causal_direction, causal_strength
            ) VALUES (
                (SELECT id FROM entities WHERE name = 'temporal_reasoning'),
                (SELECT id FROM entities WHERE name = 'causal_tracking'),
                'enables',
                0.8, 1, 'forward', 0.75
            )
        ''')

        # knowledge_graphs extends vector_search (bidirectional)
        cursor.execute('''
            INSERT INTO relations (
                from_entity_id, to_entity_id, relation_type,
                strength, bidirectional
            ) VALUES (
                (SELECT id FROM entities WHERE name = 'knowledge_graphs'),
                (SELECT id FROM entities WHERE name = 'vector_search'),
                'extends',
                0.7, 1
            )
        ''')

        conn.commit()
        conn.close()

    def test_outbound_traversal(self):
        """Test outbound graph traversal"""
        traversal = GraphTraversal(self.db_path)

        results = traversal.traverse(
            entity_name="knowledge_graphs",
            direction=TraversalDirection.OUTBOUND,
            max_depth=2
        )

        # Should find at least improved_retrieval and vector_search
        self.assertGreaterEqual(len(results), 2)

        entity_names = [r.entity_name for r in results]
        self.assertIn("improved_retrieval", entity_names)
        self.assertIn("vector_search", entity_names)

    def test_causal_chain_traversal(self):
        """Test causal chain following"""
        traversal = GraphTraversal(self.db_path)

        results = traversal.traverse(
            entity_name="knowledge_graphs",
            strategy=TraversalStrategy.CAUSAL_CHAIN,
            max_depth=3
        )

        # Filter to only causal relationships
        causal_results = [r for r in results if r.is_causal]

        self.assertGreater(len(causal_results), 0)

        # Check we found the causal link
        causal_names = [r.entity_name for r in causal_results]
        self.assertIn("improved_retrieval", causal_names)

    def test_connected_context(self):
        """Test getting connected context"""
        traversal = GraphTraversal(self.db_path)

        context = traversal.get_connected_context(
            entity_name="knowledge_graphs",
            max_depth=2
        )

        self.assertGreater(context['total_connected'], 0)
        self.assertIn('context_by_depth', context)
        self.assertEqual(context['root'], "knowledge_graphs")


class TestKnowledgeGraphManager(unittest.TestCase):
    """Test knowledge graph manager"""

    def setUp(self):
        """Create temporary test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self._setup_test_database()
        self.manager = KnowledgeGraphManager(self.db_path)

    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def _setup_test_database(self):
        """Setup minimal test database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                tier TEXT DEFAULT 'working'
            )
        ''')

        cursor.execute('''
            CREATE TABLE relations (
                id INTEGER PRIMARY KEY,
                from_entity_id INTEGER,
                to_entity_id INTEGER,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                strength REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                is_causal BOOLEAN DEFAULT 0,
                causal_direction TEXT,
                causal_strength REAL,
                bidirectional BOOLEAN DEFAULT 0,
                context_json TEXT,
                evidence_json TEXT,
                FOREIGN KEY (from_entity_id) REFERENCES entities (id),
                FOREIGN KEY (to_entity_id) REFERENCES entities (id)
            )
        ''')

        # Insert test entities
        cursor.execute("INSERT INTO entities (name, entity_type) VALUES ('entity_a', 'concept')")
        cursor.execute("INSERT INTO entities (name, entity_type) VALUES ('entity_b', 'concept')")

        conn.commit()
        conn.close()

    def test_create_relationship(self):
        """Test creating a relationship with validation"""
        result = self.manager.create_relationship(
            from_entity="entity_a",
            to_entity="entity_b",
            relation_type="causes",
            strength=0.85,
            is_causal=True,
            causal_direction="forward",
            causal_strength=0.8
        )

        self.assertTrue(result['success'])
        self.assertIn('relationship_id', result)

    def test_get_entity_relationships(self):
        """Test retrieving entity relationships"""
        # Create a relationship first
        self.manager.create_relationship(
            from_entity="entity_a",
            to_entity="entity_b",
            relation_type="relates_to",
            strength=0.7
        )

        # Get relationships
        result = self.manager.get_entity_relationships(
            entity_name="entity_a",
            direction="outbound"
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['entity'], "entity_a")
        self.assertGreater(result['relationships']['total'], 0)

    def test_hybrid_search(self):
        """Test hybrid search functionality"""
        result = self.manager.hybrid_search(
            query="entity",
            semantic_limit=10,
            graph_depth=1
        )

        self.assertTrue(result['success'])
        self.assertIn('results', result)


class TestMigration(unittest.TestCase):
    """Test migration functionality"""

    def setUp(self):
        """Create temporary old-style database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self._create_old_schema()

    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)

    def _create_old_schema(self):
        """Create old-style schema without temporal/causal features"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE entities (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE relations (
                id INTEGER PRIMARY KEY,
                from_entity_id INTEGER,
                to_entity_id INTEGER,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_entity_id) REFERENCES entities (id),
                FOREIGN KEY (to_entity_id) REFERENCES entities (id)
            )
        ''')

        # Insert test data
        cursor.execute("INSERT INTO entities (name, entity_type) VALUES ('test1', 'concept')")
        cursor.execute("INSERT INTO entities (name, entity_type) VALUES ('test2', 'concept')")
        cursor.execute('''
            INSERT INTO relations (from_entity_id, to_entity_id, relation_type)
            VALUES (1, 2, 'relates_to')
        ''')

        conn.commit()
        conn.close()

    def test_migration_detection(self):
        """Test that migration detects old schema"""
        from migrate_to_knowledge_graph import KnowledgeGraphMigration

        migration = KnowledgeGraphMigration(self.db_path)
        stats = migration._analyze_current_schema()

        self.assertFalse(stats['has_temporal'])
        self.assertFalse(stats['has_causal'])
        self.assertFalse(stats['has_strength'])
        self.assertTrue(stats['needs_migration'])


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOntologySchema))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphTraversal))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeGraphManager))
    suite.addTests(loader.loadTestsFromTestCase(TestMigration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
