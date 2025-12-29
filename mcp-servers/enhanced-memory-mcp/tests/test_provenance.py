#!/usr/bin/env python3
"""
Tests for Provenance & L-Score System.

Tests the God Agent L-Score formula:
L = geometric_mean(confidence) × average(relevance) / depth_factor

Coverage:
- ProvenanceChain dataclass
- LScoreResult dataclass
- calculate_l_score() function
- calculate_l_score_from_chain() function
- ProvenanceManager class (with anti-gaming protections)
"""

import json
import math
import sqlite3
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

# Import the modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from provenance import (
    ProvenanceChain,
    LScoreResult,
    calculate_l_score,
    calculate_l_score_from_chain,
    init_provenance_schema,
    ProvenanceManager
)


# ============================================================================
# ProvenanceChain Tests
# ============================================================================

class TestProvenanceChain:
    """Tests for ProvenanceChain dataclass."""

    def test_default_initialization(self):
        """Test empty chain initialization."""
        chain = ProvenanceChain()
        assert chain.source_ids == []
        assert chain.confidence_scores == []
        assert chain.relevance_scores == []
        assert chain.derivation_methods == []
        assert chain.timestamps == []
        assert chain.depth == 0

    def test_initialization_with_values(self):
        """Test chain initialization with values."""
        chain = ProvenanceChain(
            source_ids=[1, 2, 3],
            confidence_scores=[0.9, 0.8, 0.7],
            relevance_scores=[0.85, 0.9],
            derivation_methods=["inference", "citation"],
            timestamps=["2025-01-01T00:00:00", "2025-01-02T00:00:00"]
        )
        assert chain.source_ids == [1, 2, 3]
        assert len(chain.confidence_scores) == 3
        assert chain.depth == 3

    def test_to_json(self):
        """Test JSON serialization."""
        chain = ProvenanceChain(
            source_ids=[1, 2],
            confidence_scores=[0.9, 0.8],
            relevance_scores=[0.85],
            derivation_methods=["inference"],
            timestamps=["2025-01-01T00:00:00"]
        )
        json_str = chain.to_json()
        data = json.loads(json_str)

        assert data["source_ids"] == [1, 2]
        assert data["confidence_scores"] == [0.9, 0.8]
        assert data["relevance_scores"] == [0.85]
        assert data["derivation_methods"] == ["inference"]
        assert data["timestamps"] == ["2025-01-01T00:00:00"]

    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = json.dumps({
            "source_ids": [5, 6],
            "confidence_scores": [0.75, 0.85],
            "relevance_scores": [0.9],
            "derivation_methods": ["synthesis"],
            "timestamps": ["2025-12-01T12:00:00"]
        })
        chain = ProvenanceChain.from_json(json_str)

        assert chain.source_ids == [5, 6]
        assert chain.confidence_scores == [0.75, 0.85]
        assert chain.depth == 2

    def test_from_json_empty_string(self):
        """Test JSON deserialization with empty string."""
        chain = ProvenanceChain.from_json("")
        assert chain.source_ids == []
        assert chain.depth == 0

    def test_from_json_missing_fields(self):
        """Test JSON deserialization with missing fields."""
        json_str = json.dumps({"source_ids": [1]})
        chain = ProvenanceChain.from_json(json_str)

        assert chain.source_ids == [1]
        assert chain.confidence_scores == []
        assert chain.depth == 1

    def test_depth_property(self):
        """Test depth calculation based on source_ids length."""
        chain = ProvenanceChain(source_ids=[1, 2, 3, 4, 5])
        assert chain.depth == 5

        chain.source_ids.append(6)
        assert chain.depth == 6

    def test_roundtrip_serialization(self):
        """Test JSON roundtrip maintains data integrity."""
        original = ProvenanceChain(
            source_ids=[10, 20, 30],
            confidence_scores=[0.95, 0.85, 0.75],
            relevance_scores=[0.8, 0.9],
            derivation_methods=["inference", "citation"],
            timestamps=["2025-01-01", "2025-01-02"]
        )
        restored = ProvenanceChain.from_json(original.to_json())

        assert original.source_ids == restored.source_ids
        assert original.confidence_scores == restored.confidence_scores
        assert original.relevance_scores == restored.relevance_scores
        assert original.derivation_methods == restored.derivation_methods
        assert original.timestamps == restored.timestamps


# ============================================================================
# LScoreResult Tests
# ============================================================================

class TestLScoreResult:
    """Tests for LScoreResult dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion with rounding."""
        result = LScoreResult(
            l_score=0.72345678,
            geometric_mean_confidence=0.85123456,
            average_relevance=0.90111111,
            depth_penalty=1.1,
            derivation_depth=1,
            is_acceptable=True,
            reasoning_quality=0.85123456
        )
        d = result.to_dict()

        assert d["l_score"] == 0.7235  # Rounded to 4 decimal places
        assert d["geometric_mean_confidence"] == 0.8512
        assert d["average_relevance"] == 0.9011
        assert d["depth_penalty"] == 1.1
        assert d["derivation_depth"] == 1
        assert d["is_acceptable"] is True
        assert d["reasoning_quality"] == 0.8512
        assert d["threshold"] == 0.3

    def test_threshold_always_present(self):
        """Test that threshold is always 0.3 in dict."""
        result = LScoreResult(
            l_score=0.5, geometric_mean_confidence=0.5,
            average_relevance=0.5, depth_penalty=1.0,
            derivation_depth=0, is_acceptable=True,
            reasoning_quality=0.5
        )
        assert result.to_dict()["threshold"] == 0.3


# ============================================================================
# calculate_l_score Tests
# ============================================================================

class TestCalculateLScore:
    """Tests for calculate_l_score function."""

    def test_empty_confidence_scores(self):
        """Test default values for empty confidence scores."""
        result = calculate_l_score([], [], 0)

        assert result.l_score == 0.5
        assert result.geometric_mean_confidence == 0.5
        assert result.average_relevance == 0.5
        assert result.depth_penalty == 1.0
        assert result.derivation_depth == 0
        assert result.is_acceptable is True
        assert result.reasoning_quality == 0.5

    def test_single_confidence_score(self):
        """Test with single confidence score."""
        result = calculate_l_score([0.9], [0.8], 1)

        # L = 0.9 * 0.8 / 1.1 = 0.6545...
        assert 0.65 < result.l_score < 0.66
        assert result.geometric_mean_confidence == 0.9
        assert result.average_relevance == 0.8
        assert result.is_acceptable is True

    def test_multiple_confidence_scores(self):
        """Test geometric mean calculation with multiple scores."""
        result = calculate_l_score([0.8, 0.8], [0.9], 1)

        # Geometric mean of [0.8, 0.8] = 0.8
        # L = 0.8 * 0.9 / 1.1 = 0.6545...
        assert result.geometric_mean_confidence == 0.8
        assert 0.65 < result.l_score < 0.66

    def test_geometric_mean_varied_scores(self):
        """Test geometric mean with varied scores."""
        result = calculate_l_score([0.9, 0.4], [0.8], 1)

        # Geometric mean of [0.9, 0.4] = sqrt(0.36) = 0.6
        expected_gm = math.sqrt(0.9 * 0.4)
        assert abs(result.geometric_mean_confidence - expected_gm) < 0.0001

    def test_depth_penalty(self):
        """Test depth penalty calculation."""
        # Depth 0
        result0 = calculate_l_score([0.8], [0.8], 0)
        assert result0.depth_penalty == 1.0

        # Depth 1: penalty = 1 + (1 * 0.1) = 1.1
        result1 = calculate_l_score([0.8], [0.8], 1)
        assert result1.depth_penalty == 1.1

        # Depth 5: penalty = 1 + (5 * 0.1) = 1.5
        result5 = calculate_l_score([0.8], [0.8], 5)
        assert result5.depth_penalty == 1.5

        # Higher depth = lower L-Score
        assert result0.l_score > result1.l_score > result5.l_score

    def test_custom_depth_penalty_factor(self):
        """Test custom depth penalty factor."""
        result = calculate_l_score([0.8], [0.8], 5, depth_penalty_factor=0.2)

        # penalty = 1 + (5 * 0.2) = 2.0
        assert result.depth_penalty == 2.0

    def test_clamping_high_values(self):
        """Test clamping of values > 1.0."""
        result = calculate_l_score([1.5, 2.0], [1.2], 1)

        # Values should be clamped to 1.0
        assert result.geometric_mean_confidence == 1.0
        assert result.average_relevance == 1.0

    def test_clamping_negative_values(self):
        """Test clamping of negative values to 0.0."""
        result = calculate_l_score([-0.5, 0.8], [-0.2], 1)

        # -0.5 clamped to epsilon, then geometric mean
        # Since we use epsilon (1e-10), the geo mean will be very small
        assert result.geometric_mean_confidence < 0.01

    def test_threshold_boundary_below(self):
        """Test is_acceptable at threshold boundary - below."""
        # Create conditions for L-Score just below 0.3
        result = calculate_l_score([0.4], [0.5], 1)

        # L = 0.4 * 0.5 / 1.1 = 0.182 (below 0.3)
        assert result.is_acceptable is False

    def test_threshold_boundary_above(self):
        """Test is_acceptable at threshold boundary - above."""
        result = calculate_l_score([0.7], [0.7], 1)

        # L = 0.7 * 0.7 / 1.1 = 0.445 (above 0.3)
        assert result.is_acceptable is True

    def test_threshold_boundary_exact(self):
        """Test is_acceptable at exactly 0.3."""
        # Find values that give exactly 0.3 (or very close)
        # L = gm * rel / (1 + d*0.1)
        # 0.3 = gm * rel / 1.1 => gm * rel = 0.33
        result = calculate_l_score([0.66], [0.5], 1)

        # Should be close to 0.3
        if result.l_score >= 0.3:
            assert result.is_acceptable is True
        else:
            assert result.is_acceptable is False

    def test_reasoning_quality_equals_geometric_mean(self):
        """Test that reasoning_quality equals geometric_mean_confidence."""
        result = calculate_l_score([0.7, 0.8, 0.9], [0.85], 2)

        assert result.reasoning_quality == result.geometric_mean_confidence

    def test_empty_relevance_scores_defaults(self):
        """Test that empty relevance scores default to [0.5]."""
        result = calculate_l_score([0.8], [], 1)

        assert result.average_relevance == 0.5

    def test_l_score_formula_correctness(self):
        """Test L-Score formula: L = gm(conf) × avg(rel) / depth_factor."""
        confidence = [0.9, 0.8, 0.7]
        relevance = [0.85, 0.95]
        depth = 2

        result = calculate_l_score(confidence, relevance, depth)

        # Calculate expected values manually
        expected_gm = (0.9 * 0.8 * 0.7) ** (1/3)
        expected_rel = (0.85 + 0.95) / 2
        expected_depth_factor = 1 + (2 * 0.1)
        expected_l_score = expected_gm * expected_rel / expected_depth_factor

        assert abs(result.l_score - expected_l_score) < 0.0001
        assert abs(result.geometric_mean_confidence - expected_gm) < 0.0001
        assert abs(result.average_relevance - expected_rel) < 0.0001
        assert result.depth_penalty == expected_depth_factor


# ============================================================================
# calculate_l_score_from_chain Tests
# ============================================================================

class TestCalculateLScoreFromChain:
    """Tests for calculate_l_score_from_chain function."""

    def test_empty_chain(self):
        """Test with empty ProvenanceChain."""
        chain = ProvenanceChain()
        result = calculate_l_score_from_chain(chain)

        assert result.l_score == 0.5
        assert result.derivation_depth == 0

    def test_populated_chain(self):
        """Test with populated ProvenanceChain."""
        chain = ProvenanceChain(
            source_ids=[1, 2],
            confidence_scores=[0.9, 0.8],
            relevance_scores=[0.85, 0.9]
        )
        result = calculate_l_score_from_chain(chain)

        # Verify it uses chain values correctly
        expected_gm = (0.9 * 0.8) ** 0.5
        assert abs(result.geometric_mean_confidence - expected_gm) < 0.0001
        assert result.derivation_depth == 2  # depth from chain.depth


# ============================================================================
# ProvenanceManager Tests
# ============================================================================

class TestProvenanceManager:
    """Tests for ProvenanceManager class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        # Create entities table for testing
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        try:
            db_path.unlink()
        except Exception:
            pass

    @pytest.fixture
    def manager(self, temp_db):
        """Create ProvenanceManager with temp database."""
        return ProvenanceManager(temp_db)

    def test_init_provenance_schema(self, temp_db):
        """Test schema initialization adds required columns."""
        init_provenance_schema(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(entities)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "l_score" in columns
        assert "reasoning_quality" in columns
        assert "source_chain" in columns
        assert "derivation_depth" in columns

    def test_init_provenance_schema_idempotent(self, temp_db):
        """Test schema initialization is idempotent."""
        # Should not raise on multiple calls
        init_provenance_schema(temp_db)
        init_provenance_schema(temp_db)
        init_provenance_schema(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(entities)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        # Should not have duplicates
        assert len(columns) == len(set(columns))

    def _insert_test_entity(self, db_path: Path, entity_id: int, name: str, l_score: float = None):
        """Helper to insert test entity."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO entities (id, name, entity_type, l_score)
            VALUES (?, ?, 'test', ?)
        """, (entity_id, name, l_score))
        conn.commit()
        conn.close()

    def test_create_entity_with_provenance_no_sources(self, manager, temp_db):
        """Test provenance creation with no source entities."""
        self._insert_test_entity(temp_db, 1, "test_entity")

        result = manager.create_entity_with_provenance(
            entity_id=1,
            source_entity_ids=[],
            confidence=0.8,
            relevance=0.9
        )

        # Should create valid L-Score
        assert result.l_score > 0
        assert result.is_acceptable is True

    def test_create_entity_with_provenance_with_sources(self, manager, temp_db):
        """Test provenance creation with source entities."""
        # Create source entities
        self._insert_test_entity(temp_db, 1, "source_1", l_score=0.8)
        self._insert_test_entity(temp_db, 2, "source_2", l_score=0.7)
        self._insert_test_entity(temp_db, 3, "derived_entity")

        result = manager.create_entity_with_provenance(
            entity_id=3,
            source_entity_ids=[1, 2],
            confidence=0.85,
            relevance=0.9
        )

        assert result.l_score > 0
        assert result.derivation_depth >= 1

    def test_citation_cycle_detection_direct(self, manager, temp_db):
        """Test detection of direct citation cycle (A→B→A)."""
        # Create entity A
        self._insert_test_entity(temp_db, 1, "entity_A")

        # Set A's source_chain to reference entity 2
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        source_chain = json.dumps({"source_ids": [2], "confidence_scores": [0.8]})
        cursor.execute("""
            UPDATE entities SET source_chain = ? WHERE id = 1
        """, (source_chain,))
        conn.commit()
        conn.close()

        # Create entity B
        self._insert_test_entity(temp_db, 2, "entity_B")

        # Set B's source_chain to reference entity 1 (creating cycle)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        source_chain = json.dumps({"source_ids": [1], "confidence_scores": [0.7]})
        cursor.execute("""
            UPDATE entities SET source_chain = ? WHERE id = 2
        """, (source_chain,))
        conn.commit()
        conn.close()

        # Now try to create entity 3 that sources from 2
        # This should detect the cycle since 2 → 1 → 2
        self._insert_test_entity(temp_db, 3, "entity_C")

        # Detect cycle: 1 → 2 → 1
        has_cycle, path = manager._detect_citation_cycle(1, [2])
        assert has_cycle is True
        assert path is not None

    def test_citation_cycle_detection_no_cycle(self, manager, temp_db):
        """Test no false positive for valid chain."""
        # Create linear chain: 1 → 2 → 3 (no cycle)
        self._insert_test_entity(temp_db, 1, "source_1")
        self._insert_test_entity(temp_db, 2, "source_2")
        self._insert_test_entity(temp_db, 3, "derived")

        has_cycle, path = manager._detect_citation_cycle(3, [1, 2])
        assert has_cycle is False
        assert path is None

    def test_source_quality_penalty_low_score(self, manager, temp_db):
        """Test penalty for low L-Score sources."""
        # Create source with low L-Score
        self._insert_test_entity(temp_db, 1, "low_quality_source", l_score=0.2)

        penalty = manager._calculate_source_quality_penalty([1])

        # Should have penalty (< 1.0) for low quality source
        assert penalty < 1.0

    def test_source_quality_penalty_high_score(self, manager, temp_db):
        """Test no penalty for high L-Score sources."""
        # Create source with high L-Score
        self._insert_test_entity(temp_db, 1, "high_quality_source", l_score=0.8)

        penalty = manager._calculate_source_quality_penalty([1])

        # Should have no/minimal penalty
        assert penalty >= 0.8

    def test_source_quality_penalty_unknown_source(self, manager, temp_db):
        """Test heavy penalty for unknown sources."""
        penalty = manager._calculate_source_quality_penalty([9999])

        # Unknown source should get heavy penalty
        assert penalty == 0.5

    def test_get_provenance_chain(self, manager, temp_db):
        """Test retrieving provenance chain."""
        # Create entity with provenance
        self._insert_test_entity(temp_db, 1, "source_entity", l_score=0.8)
        self._insert_test_entity(temp_db, 2, "derived_entity")

        manager.create_entity_with_provenance(
            entity_id=2,
            source_entity_ids=[1],
            confidence=0.9,
            relevance=0.85
        )

        chain_info = manager.get_provenance_chain(2)

        assert "entity" in chain_info
        assert "l_score" in chain_info
        assert "provenance_chain" in chain_info
        assert chain_info["entity"]["id"] == 2

    def test_get_provenance_chain_not_found(self, manager, temp_db):
        """Test error for non-existent entity."""
        result = manager.get_provenance_chain(9999)

        assert "error" in result

    def test_validate_l_score_above_threshold(self, manager, temp_db):
        """Test validation passes for L-Score above threshold."""
        self._insert_test_entity(temp_db, 1, "good_entity")

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE entities SET l_score = 0.5 WHERE id = 1
        """)
        conn.commit()
        conn.close()

        result = manager.validate_l_score(1, threshold=0.3)

        assert result["valid"] is True
        assert "ACCEPT" in result["recommendation"]

    def test_validate_l_score_below_threshold(self, manager, temp_db):
        """Test validation fails for L-Score below threshold."""
        self._insert_test_entity(temp_db, 1, "poor_entity")

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE entities SET l_score = 0.1 WHERE id = 1
        """)
        conn.commit()
        conn.close()

        result = manager.validate_l_score(1, threshold=0.3)

        assert result["valid"] is False
        assert "REJECT" in result["recommendation"] or "REVIEW" in result["recommendation"]

    def test_validate_l_score_not_found(self, manager, temp_db):
        """Test validation for non-existent entity."""
        result = manager.validate_l_score(9999)

        assert result["valid"] is False
        assert "error" in result

    def test_update_l_score_with_new_evidence(self, manager, temp_db):
        """Test L-Score update with additional evidence."""
        self._insert_test_entity(temp_db, 1, "entity_to_update")

        # Create initial provenance
        manager.create_entity_with_provenance(
            entity_id=1,
            source_entity_ids=[],
            confidence=0.5,
            relevance=0.5
        )

        # Get initial score
        initial = manager.validate_l_score(1)
        initial_score = initial["l_score"]

        # Update with high confidence evidence
        result = manager.update_l_score(1, additional_confidence=0.95)

        # L-Score should potentially change
        assert result.l_score >= 0

    def test_get_high_provenance_entities(self, manager, temp_db):
        """Test retrieval of high-quality entities."""
        # Create entities with various L-Scores
        for i, l_score in enumerate([0.9, 0.8, 0.5, 0.3, 0.1], start=1):
            self._insert_test_entity(temp_db, i, f"entity_{i}")
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("UPDATE entities SET l_score = ? WHERE id = ?", (l_score, i))
            conn.commit()
            conn.close()

        results = manager.get_high_provenance_entities(min_l_score=0.7)

        # Should only get entities with L-Score >= 0.7
        assert len(results) == 2
        assert all(r["l_score"] >= 0.7 for r in results)

    def test_get_low_provenance_entities(self, manager, temp_db):
        """Test retrieval of low-quality entities."""
        # Create entities with various L-Scores
        for i, l_score in enumerate([0.9, 0.5, 0.25, 0.1], start=1):
            self._insert_test_entity(temp_db, i, f"entity_{i}")
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("UPDATE entities SET l_score = ? WHERE id = ?", (l_score, i))
            conn.commit()
            conn.close()

        results = manager.get_low_provenance_entities(max_l_score=0.3)

        # Should only get entities with L-Score < 0.3
        assert len(results) == 2
        assert all(r["l_score"] < 0.3 for r in results)

    def test_gaming_rejection_raises_error(self, manager, temp_db):
        """Test that citation cycle detection raises ValueError."""
        # Set up circular reference
        self._insert_test_entity(temp_db, 1, "entity_A")
        self._insert_test_entity(temp_db, 2, "entity_B")

        # A sources from B
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        source_chain = json.dumps({"source_ids": [2], "confidence_scores": [0.8]})
        cursor.execute("UPDATE entities SET source_chain = ? WHERE id = 1", (source_chain,))
        conn.commit()
        conn.close()

        # B sources from A (cycle)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        source_chain = json.dumps({"source_ids": [1], "confidence_scores": [0.8]})
        cursor.execute("UPDATE entities SET source_chain = ? WHERE id = 2", (source_chain,))
        conn.commit()
        conn.close()

        # Try to update A to source from B (completes cycle)
        with pytest.raises(ValueError, match="Citation cycle detected"):
            manager.create_entity_with_provenance(
                entity_id=1,
                source_entity_ids=[2],
                confidence=0.9,
                relevance=0.9
            )


# ============================================================================
# Integration Tests
# ============================================================================

class TestProvenanceIntegration:
    """Integration tests for full provenance workflow."""

    @pytest.fixture
    def db_with_entities(self):
        """Create database with multiple test entities."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create test entities
        for i in range(1, 6):
            cursor.execute("""
                INSERT INTO entities (id, name, entity_type)
                VALUES (?, ?, 'test')
            """, (i, f"entity_{i}"))

        conn.commit()
        conn.close()

        yield db_path

        try:
            db_path.unlink()
        except Exception:
            pass

    def test_full_provenance_workflow(self, db_with_entities):
        """Test complete provenance workflow from creation to validation."""
        manager = ProvenanceManager(db_with_entities)

        # Step 1: Create root entities (no sources)
        r1 = manager.create_entity_with_provenance(1, [], confidence=0.95, relevance=0.9)
        r2 = manager.create_entity_with_provenance(2, [], confidence=0.9, relevance=0.85)

        assert r1.is_acceptable is True
        assert r2.is_acceptable is True

        # Step 2: Create derived entity from roots
        r3 = manager.create_entity_with_provenance(
            entity_id=3,
            source_entity_ids=[1, 2],
            confidence=0.85,
            relevance=0.8,
            derivation_method="inference"
        )

        assert r3.derivation_depth >= 1

        # Step 3: Validate derived entity
        validation = manager.validate_l_score(3)
        assert validation["has_sources"] is True

        # Step 4: Get full provenance chain
        chain = manager.get_provenance_chain(3)
        assert chain["provenance_chain"]["depth"] >= 1

        # Step 5: Get high-quality entities
        high = manager.get_high_provenance_entities(min_l_score=0.3)
        assert len(high) >= 1

    def test_multi_level_derivation(self, db_with_entities):
        """Test L-Score degradation through multiple derivation levels."""
        manager = ProvenanceManager(db_with_entities)

        # Level 0: Root (highest score)
        r1 = manager.create_entity_with_provenance(1, [], confidence=0.95, relevance=0.95)

        # Level 1: Derived from root
        r2 = manager.create_entity_with_provenance(2, [1], confidence=0.9, relevance=0.9)

        # Level 2: Derived from level 1
        r3 = manager.create_entity_with_provenance(3, [2], confidence=0.85, relevance=0.85)

        # Level 3: Derived from level 2
        r4 = manager.create_entity_with_provenance(4, [3], confidence=0.8, relevance=0.8)

        # Scores should generally decrease as derivation depth increases
        # (due to confidence decay and depth penalties)
        scores = [r1.l_score, r2.l_score, r3.l_score, r4.l_score]

        # Each level should have lower or equal score than previous
        # (accounting for some variance from confidence values)
        assert scores[0] >= 0  # All should be valid
        assert scores[3] < scores[0]  # Deep derivation should be lower than root


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_confidence_scores(self):
        """Test handling of zero confidence scores."""
        result = calculate_l_score([0.0, 0.0], [0.5], 1)

        # Should handle zeros gracefully (using epsilon)
        assert result.geometric_mean_confidence < 0.001
        assert result.l_score >= 0

    def test_very_deep_derivation(self):
        """Test handling of very deep derivation chains."""
        result = calculate_l_score([0.9] * 10, [0.9] * 10, 100)

        # With depth 100 and 0.1 penalty: factor = 11.0
        assert result.depth_penalty == 11.0
        assert result.l_score > 0
        assert result.l_score < 0.1  # Should be very low due to depth

    def test_single_very_low_confidence(self):
        """Test geometric mean with one very low value."""
        result = calculate_l_score([0.9, 0.9, 0.01], [0.9], 1)

        # Geometric mean pulls down quickly with low values
        # (0.9 * 0.9 * 0.01)^(1/3) ≈ 0.2
        assert result.geometric_mean_confidence < 0.3

    def test_l_score_determinism(self):
        """Test that L-Score calculation is deterministic."""
        conf = [0.8, 0.7, 0.9]
        rel = [0.85, 0.75]
        depth = 2

        results = [calculate_l_score(conf, rel, depth) for _ in range(10)]

        # All results should be identical
        assert all(r.l_score == results[0].l_score for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
