-- Add source attribution and conflict resolution support
-- Migration: add_source_attribution.sql
-- Date: 2025-11-12

-- Source tracking columns
ALTER TABLE entities ADD COLUMN source_session TEXT;
ALTER TABLE entities ADD COLUMN source_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE entities ADD COLUMN extraction_method TEXT DEFAULT 'manual'; -- manual, auto, import

-- Temporal decay columns (for future relevance scoring)
ALTER TABLE entities ADD COLUMN last_confirmed TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE entities ADD COLUMN relevance_score REAL DEFAULT 1.0;

-- Conflict resolution metadata
ALTER TABLE entities ADD COLUMN parent_entity_id INTEGER; -- For merged/updated entities
ALTER TABLE entities ADD COLUMN conflict_resolution_method TEXT; -- merge, update, branch

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_source_session ON entities(source_session);
CREATE INDEX IF NOT EXISTS idx_entities_extraction_method ON entities(extraction_method);
CREATE INDEX IF NOT EXISTS idx_entities_relevance_score ON entities(relevance_score);
CREATE INDEX IF NOT EXISTS idx_entities_parent_entity ON entities(parent_entity_id);

-- Conflicts tracking table
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    conflicting_entity_id INTEGER,
    conflict_type TEXT NOT NULL, -- contradiction, duplicate, update, complementary
    confidence REAL NOT NULL,
    suggested_action TEXT, -- merge, update, branch, ignore
    resolution_status TEXT DEFAULT 'pending', -- pending, resolved, ignored
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities (id),
    FOREIGN KEY (conflicting_entity_id) REFERENCES entities (id)
);

CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON conflicts(entity_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_status);
