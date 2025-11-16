-- Schema Migration: Enhanced Knowledge Graph with Temporal Edges and Causal Reasoning
-- Inspired by: "You're Doing Memory All Wrong" - Zapai
-- Adds: Temporal timestamps, causal attributes, bi-directional support, strength/confidence

-- ===================================================================
-- STEP 1: Backup existing relations table
-- ===================================================================

CREATE TABLE IF NOT EXISTS relations_backup AS
SELECT * FROM relations;

-- ===================================================================
-- STEP 2: Drop old relations table
-- ===================================================================

DROP TABLE IF EXISTS relations;

-- ===================================================================
-- STEP 3: Create enhanced relations table with temporal and causal attributes
-- ===================================================================

CREATE TABLE relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Core relationship
    from_entity_id INTEGER NOT NULL,
    to_entity_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,

    -- Temporal attributes (NEW - temporal edge modeling)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP,  -- When relationship became valid
    valid_until TIMESTAMP,  -- When relationship becomes invalid (for time-bound relationships)

    -- Strength and confidence (NEW)
    strength REAL DEFAULT 0.5 CHECK(strength >= 0.0 AND strength <= 1.0),
    confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),

    -- Causal attributes (NEW - causal reasoning)
    is_causal BOOLEAN DEFAULT 0,
    causal_direction TEXT CHECK(causal_direction IN ('forward', 'backward', NULL)),
    causal_strength REAL CHECK(causal_strength IS NULL OR (causal_strength >= 0.0 AND causal_strength <= 1.0)),

    -- Context and evidence
    context_json TEXT,  -- JSON object for additional context
    evidence_json TEXT,  -- JSON array of evidence strings

    -- Bi-directional support (NEW)
    bidirectional BOOLEAN DEFAULT 0,
    reverse_relation_id INTEGER,  -- Reference to auto-created reverse relationship

    -- Metadata
    metadata_json TEXT,  -- Additional metadata as JSON

    -- Foreign keys
    FOREIGN KEY (from_entity_id) REFERENCES entities (id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity_id) REFERENCES entities (id) ON DELETE CASCADE,
    FOREIGN KEY (reverse_relation_id) REFERENCES relations (id) ON DELETE SET NULL,

    -- Constraints
    CHECK (from_entity_id != to_entity_id),  -- No self-loops
    CHECK (is_causal = 0 OR causal_strength IS NOT NULL)  -- If causal, must have strength
);

-- ===================================================================
-- STEP 4: Create indexes for optimal query performance
-- ===================================================================

-- Core relationship queries
CREATE INDEX idx_relations_from_entity ON relations(from_entity_id);
CREATE INDEX idx_relations_to_entity ON relations(to_entity_id);
CREATE INDEX idx_relations_type ON relations(relation_type);

-- Temporal queries
CREATE INDEX idx_relations_created ON relations(created_at);
CREATE INDEX idx_relations_valid_from ON relations(valid_from);
CREATE INDEX idx_relations_valid_until ON relations(valid_until);

-- Bi-directional traversal
CREATE INDEX idx_relations_reverse ON relations(reverse_relation_id);

-- Causal queries
CREATE INDEX idx_relations_causal ON relations(is_causal) WHERE is_causal = 1;
CREATE INDEX idx_relations_causal_strength ON relations(causal_strength) WHERE causal_strength IS NOT NULL;

-- Strength filtering
CREATE INDEX idx_relations_strength ON relations(strength);

-- Composite index for common traversal pattern
CREATE INDEX idx_relations_from_type_strength ON relations(from_entity_id, relation_type, strength);
CREATE INDEX idx_relations_to_type_strength ON relations(to_entity_id, relation_type, strength);

-- ===================================================================
-- STEP 5: Migrate existing data from backup
-- ===================================================================

INSERT INTO relations (
    from_entity_id,
    to_entity_id,
    relation_type,
    created_at,
    strength,
    confidence
)
SELECT
    from_entity_id,
    to_entity_id,
    relation_type,
    created_at,
    0.5,  -- Default strength
    0.5   -- Default confidence
FROM relations_backup;

-- ===================================================================
-- STEP 6: Create trigger for automatic updated_at timestamp
-- ===================================================================

CREATE TRIGGER update_relations_timestamp
AFTER UPDATE ON relations
FOR EACH ROW
BEGIN
    UPDATE relations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ===================================================================
-- STEP 7: Create trigger for bi-directional relationship support
-- ===================================================================

CREATE TRIGGER create_bidirectional_relation
AFTER INSERT ON relations
WHEN NEW.bidirectional = 1 AND NEW.reverse_relation_id IS NULL
BEGIN
    -- Create reverse relationship
    INSERT INTO relations (
        from_entity_id,
        to_entity_id,
        relation_type,
        created_at,
        updated_at,
        strength,
        confidence,
        is_causal,
        causal_direction,
        causal_strength,
        bidirectional,
        reverse_relation_id
    ) VALUES (
        NEW.to_entity_id,
        NEW.from_entity_id,
        NEW.relation_type || '_reverse',  -- Add _reverse suffix
        NEW.created_at,
        NEW.updated_at,
        NEW.strength,
        NEW.confidence,
        NEW.is_causal,
        CASE
            WHEN NEW.causal_direction = 'forward' THEN 'backward'
            WHEN NEW.causal_direction = 'backward' THEN 'forward'
            ELSE NULL
        END,
        NEW.causal_strength,
        1,  -- Also bidirectional
        NEW.id  -- Link back to original
    );

    -- Update original with reverse relation ID
    UPDATE relations
    SET reverse_relation_id = last_insert_rowid()
    WHERE id = NEW.id;
END;

-- ===================================================================
-- STEP 8: Create view for temporal queries
-- ===================================================================

CREATE VIEW current_relations AS
SELECT
    r.*,
    e1.name as from_entity_name,
    e1.entity_type as from_entity_type,
    e2.name as to_entity_name,
    e2.entity_type as to_entity_type
FROM relations r
JOIN entities e1 ON r.from_entity_id = e1.id
JOIN entities e2 ON r.to_entity_id = e2.id
WHERE
    (r.valid_from IS NULL OR r.valid_from <= CURRENT_TIMESTAMP)
    AND (r.valid_until IS NULL OR r.valid_until > CURRENT_TIMESTAMP);

-- ===================================================================
-- STEP 9: Create view for causal chains
-- ===================================================================

CREATE VIEW causal_relationships AS
SELECT
    r.*,
    e1.name as from_entity_name,
    e2.name as to_entity_name
FROM relations r
JOIN entities e1 ON r.from_entity_id = e1.id
JOIN entities e2 ON r.to_entity_id = e2.id
WHERE r.is_causal = 1
ORDER BY r.created_at, r.causal_strength DESC;

-- ===================================================================
-- STEP 10: Create helper functions via stored procedures (SQLite equivalent)
-- Note: SQLite doesn't have stored procedures, but we can document these as
-- application-level functions
-- ===================================================================

-- These would be implemented in Python:
--
-- get_temporal_relationships(entity_id, from_date, to_date)
--   Returns relationships within time window
--
-- get_causal_chain(entity_id, direction='forward', max_depth=5)
--   Follows causal relationships to build cause-effect chain
--
-- find_strongest_relationships(entity_id, top_n=10)
--   Returns highest strength relationships
--
-- get_bidirectional_context(entity_id, max_hops=2)
--   Traverses both directions from entity

-- ===================================================================
-- STEP 11: Add statistics table for tracking relationship patterns
-- ===================================================================

CREATE TABLE IF NOT EXISTS relationship_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_type TEXT NOT NULL,
    total_count INTEGER DEFAULT 0,
    avg_strength REAL,
    avg_causal_strength REAL,
    causal_count INTEGER DEFAULT 0,
    bidirectional_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(relation_type)
);

-- ===================================================================
-- STEP 12: Create trigger to update statistics
-- ===================================================================

CREATE TRIGGER update_relationship_stats
AFTER INSERT ON relations
BEGIN
    INSERT INTO relationship_statistics (relation_type, total_count, avg_strength, causal_count, bidirectional_count)
    VALUES (NEW.relation_type, 1, NEW.strength, CASE WHEN NEW.is_causal THEN 1 ELSE 0 END, CASE WHEN NEW.bidirectional THEN 1 ELSE 0 END)
    ON CONFLICT(relation_type) DO UPDATE SET
        total_count = total_count + 1,
        avg_strength = (avg_strength * total_count + NEW.strength) / (total_count + 1),
        causal_count = causal_count + CASE WHEN NEW.is_causal THEN 1 ELSE 0 END,
        bidirectional_count = bidirectional_count + CASE WHEN NEW.bidirectional THEN 1 ELSE 0 END,
        last_updated = CURRENT_TIMESTAMP;
END;

-- ===================================================================
-- MIGRATION COMPLETE
-- ===================================================================

-- Verification queries:
--
-- SELECT COUNT(*) FROM relations;  -- Should match relations_backup
-- SELECT COUNT(*) FROM relations WHERE bidirectional = 1;
-- SELECT COUNT(*) FROM relations WHERE is_causal = 1;
-- SELECT * FROM relationship_statistics;
-- SELECT * FROM current_relations LIMIT 10;
