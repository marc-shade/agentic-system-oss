-- Phase 2: AGI Memory - Temporal Reasoning & Causal Chains
-- Migration: 002_agi_phase2_temporal_reasoning
-- Created: 2025-11-13
-- Purpose: Add temporal chains and causal reasoning capabilities

-- ============================================================================
-- TEMPORAL CHAINS: Link events in causal sequences
-- ============================================================================

CREATE TABLE IF NOT EXISTS temporal_chains (
    chain_id TEXT PRIMARY KEY,
    chain_type TEXT NOT NULL, -- "causal", "sequential", "conditional", "cyclic"

    -- Chain metadata
    chain_name TEXT,
    description TEXT,

    -- Entities in the chain (ordered JSON array of entity IDs)
    entities TEXT NOT NULL, -- JSON: [id1, id2, id3, ...]

    -- Chain strength and confidence
    confidence REAL DEFAULT 0.5, -- How confident in this chain (0.0-1.0)
    strength REAL DEFAULT 0.5,   -- How strong the relationships are

    -- Discovery metadata
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discovery_method TEXT,        -- "automatic", "manual", "consolidation"
    evidence_count INTEGER DEFAULT 1,

    -- Validation
    validated BOOLEAN DEFAULT 0,
    validation_score REAL,
    last_validated TIMESTAMP,

    -- Temporal metadata
    time_span_seconds INTEGER,    -- How long does this chain typically take
    typical_delays TEXT,           -- JSON: delays between each step

    metadata TEXT DEFAULT '{}'
);

-- ============================================================================
-- CAUSAL LINKS: Individual cause-effect relationships
-- ============================================================================

CREATE TABLE IF NOT EXISTS causal_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Cause and effect
    cause_entity_id INTEGER NOT NULL,
    effect_entity_id INTEGER NOT NULL,

    -- Causal relationship details
    relationship_type TEXT, -- "direct", "indirect", "contributory", "preventive"
    strength REAL DEFAULT 0.5, -- 0.0 (weak) to 1.0 (strong)

    -- Evidence
    evidence_count INTEGER DEFAULT 1,
    last_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_observed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Temporal details
    typical_delay_seconds INTEGER, -- How long between cause and effect
    delay_variance_seconds INTEGER,

    -- Confidence and validation
    confidence REAL DEFAULT 0.5,
    validated BOOLEAN DEFAULT 0,

    -- Context
    context_conditions TEXT, -- JSON: conditions under which this link holds

    -- Which temporal chain does this belong to (if any)
    chain_id TEXT,
    position_in_chain INTEGER,

    metadata TEXT DEFAULT '{}',

    FOREIGN KEY (cause_entity_id) REFERENCES entities (id),
    FOREIGN KEY (effect_entity_id) REFERENCES entities (id),
    FOREIGN KEY (chain_id) REFERENCES temporal_chains (chain_id),
    UNIQUE(cause_entity_id, effect_entity_id)
);

-- ============================================================================
-- CAUSAL HYPOTHESES: Proposed causal relationships to test
-- ============================================================================

CREATE TABLE IF NOT EXISTS causal_hypotheses (
    hypothesis_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Hypothesis details
    proposed_cause_id INTEGER NOT NULL,
    proposed_effect_id INTEGER NOT NULL,
    hypothesis_description TEXT NOT NULL,

    -- Testing status
    status TEXT DEFAULT 'proposed', -- "proposed", "testing", "confirmed", "rejected"
    confidence_score REAL DEFAULT 0.5,

    -- Evidence
    supporting_evidence TEXT, -- JSON: list of observations
    contradicting_evidence TEXT,
    test_count INTEGER DEFAULT 0,

    -- Timestamps
    proposed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_tested TIMESTAMP,
    resolved_at TIMESTAMP,

    -- Outcome
    resolution TEXT, -- Why confirmed or rejected

    metadata TEXT DEFAULT '{}',

    FOREIGN KEY (proposed_cause_id) REFERENCES entities (id),
    FOREIGN KEY (proposed_effect_id) REFERENCES entities (id)
);

-- ============================================================================
-- EVENT SEQUENCES: Ordered sequences of events for pattern detection
-- ============================================================================

CREATE TABLE IF NOT EXISTS event_sequences (
    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Sequence details
    sequence_type TEXT, -- "workflow", "pattern", "routine", "anomaly"
    entities TEXT NOT NULL, -- JSON: ordered list of entity IDs

    -- Frequency and occurrence
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Timing patterns
    avg_duration_seconds INTEGER,
    avg_intervals TEXT, -- JSON: average time between each step

    -- Predictive value
    predictability_score REAL, -- How predictable is next step
    completion_rate REAL,      -- How often does sequence complete

    -- Context
    typical_context TEXT, -- JSON: common conditions when this occurs

    metadata TEXT DEFAULT '{}'
);

-- ============================================================================
-- CONSOLIDATION JOBS: Track background consolidation processing
-- ============================================================================

CREATE TABLE IF NOT EXISTS consolidation_jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Job details
    job_type TEXT NOT NULL, -- "pattern_extraction", "causal_discovery", "memory_compression"
    status TEXT DEFAULT 'pending', -- "pending", "running", "completed", "failed"

    -- Scope
    time_window_start TIMESTAMP,
    time_window_end TIMESTAMP,
    entity_count INTEGER,

    -- Execution
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Results
    patterns_found INTEGER DEFAULT 0,
    chains_created INTEGER DEFAULT 0,
    links_created INTEGER DEFAULT 0,
    memories_promoted INTEGER DEFAULT 0,
    memories_compressed INTEGER DEFAULT 0,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Output
    results_summary TEXT, -- JSON: detailed results

    metadata TEXT DEFAULT '{}'
);

-- ============================================================================
-- INDEXES: Performance optimization for temporal queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_causal_links_cause ON causal_links(cause_entity_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_effect ON causal_links(effect_entity_id);
CREATE INDEX IF NOT EXISTS idx_causal_links_strength ON causal_links(strength);
CREATE INDEX IF NOT EXISTS idx_causal_links_chain ON causal_links(chain_id);

CREATE INDEX IF NOT EXISTS idx_temporal_chains_type ON temporal_chains(chain_type);
CREATE INDEX IF NOT EXISTS idx_temporal_chains_confidence ON temporal_chains(confidence);
CREATE INDEX IF NOT EXISTS idx_temporal_chains_discovered ON temporal_chains(discovered_at);

CREATE INDEX IF NOT EXISTS idx_causal_hypotheses_status ON causal_hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_causal_hypotheses_confidence ON causal_hypotheses(confidence_score);

CREATE INDEX IF NOT EXISTS idx_event_sequences_type ON event_sequences(sequence_type);
CREATE INDEX IF NOT EXISTS idx_event_sequences_last_seen ON event_sequences(last_seen);

CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_status ON consolidation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_type ON consolidation_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_started ON consolidation_jobs(started_at);

-- ============================================================================
-- VIEWS: Convenient queries for temporal reasoning
-- ============================================================================

-- View: Strong causal links (high confidence and strength)
CREATE VIEW IF NOT EXISTS strong_causal_links AS
SELECT
    cl.*,
    e1.name as cause_name,
    e2.name as effect_name
FROM causal_links cl
JOIN entities e1 ON cl.cause_entity_id = e1.id
JOIN entities e2 ON cl.effect_entity_id = e2.id
WHERE cl.strength >= 0.7 AND cl.confidence >= 0.7
ORDER BY cl.strength DESC, cl.confidence DESC;

-- View: Recent temporal chains (discovered in last 7 days)
CREATE VIEW IF NOT EXISTS recent_temporal_chains AS
SELECT *
FROM temporal_chains
WHERE discovered_at >= datetime('now', '-7 days')
ORDER BY discovered_at DESC;

-- View: Active consolidation jobs
CREATE VIEW IF NOT EXISTS active_consolidation_jobs AS
SELECT *
FROM consolidation_jobs
WHERE status IN ('pending', 'running')
ORDER BY started_at DESC;
