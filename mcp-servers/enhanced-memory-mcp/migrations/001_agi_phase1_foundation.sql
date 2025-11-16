-- Phase 1: AGI Memory Foundation - Cross-Session Identity & Memory-Action Loop
-- Migration: 001_agi_phase1_foundation
-- Created: 2025-11-13
-- Purpose: Add tables for persistent agent identity and action outcome tracking

-- ============================================================================
-- AGENT IDENTITY: Persistent identity across sessions
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_identity (
    agent_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_sessions INTEGER DEFAULT 0,
    total_actions INTEGER DEFAULT 0,
    total_memories INTEGER DEFAULT 0,

    -- Learned capabilities (JSON: {"coding": 0.85, "research": 0.92, ...})
    skill_levels TEXT DEFAULT '{}',

    -- Personality traits learned over time (JSON: {"curiosity": 0.8, "caution": 0.6, ...})
    personality_traits TEXT DEFAULT '{}',

    -- Core beliefs/knowledge (JSON: ["async is better than threads", ...])
    core_beliefs TEXT DEFAULT '[]',

    -- Preferences (JSON: {"preferred_editor": "vim", ...})
    preferences TEXT DEFAULT '{}',

    -- Summary of last session for continuity
    last_session_summary TEXT,

    -- Metadata
    metadata TEXT DEFAULT '{}'
);

-- ============================================================================
-- SESSION CONTINUITY: Link sessions together for context preservation
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_continuity (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Session context summary
    context_summary TEXT,

    -- What the agent learned this session (JSON array)
    key_learnings TEXT DEFAULT '[]',

    -- Unfinished work (JSON: {"goals": [...], "tasks": [...]})
    unfinished_work TEXT DEFAULT '{}',

    -- Session type (JSON: {"primary": "coding", "secondary": ["debugging", "research"]})
    session_type TEXT DEFAULT '{}',

    -- Performance metrics (JSON: success rates, error counts, etc.)
    performance_metrics TEXT DEFAULT '{}',

    -- Previous session for chaining
    previous_session_id TEXT,

    FOREIGN KEY (agent_id) REFERENCES agent_identity (agent_id),
    FOREIGN KEY (previous_session_id) REFERENCES session_continuity (session_id)
);

-- ============================================================================
-- ACTION OUTCOMES: Track what happened when agent took actions
-- ============================================================================

CREATE TABLE IF NOT EXISTS action_outcomes (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    session_id TEXT,

    -- Action details
    action_type TEXT NOT NULL, -- "code_change", "command_execution", "research", etc.
    action_description TEXT NOT NULL,
    action_context TEXT, -- What led to this action

    -- Expected vs actual
    expected_result TEXT,
    actual_result TEXT,

    -- Outcome assessment
    success_score REAL DEFAULT 0.5, -- 0.0 (failure) to 1.0 (success)
    outcome_category TEXT, -- "success", "partial", "failure", "error"

    -- Learning extraction
    learning_extracted TEXT, -- What did we learn from this?
    will_retry BOOLEAN DEFAULT 0,
    retry_with_changes TEXT, -- What to change if retrying

    -- Timing
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,

    -- Metadata
    metadata TEXT DEFAULT '{}',

    FOREIGN KEY (entity_id) REFERENCES entities (id),
    FOREIGN KEY (session_id) REFERENCES session_continuity (session_id)
);

-- ============================================================================
-- EXTEND ENTITIES: Add AGI-relevant fields to existing entities table
-- ============================================================================

-- Add emotional/salience tagging columns
ALTER TABLE entities ADD COLUMN emotional_valence REAL DEFAULT 0.0; -- -1.0 (negative) to 1.0 (positive)
ALTER TABLE entities ADD COLUMN arousal_level REAL DEFAULT 0.0; -- 0.0 (calm) to 1.0 (excited)
ALTER TABLE entities ADD COLUMN salience_score REAL DEFAULT 0.5; -- 0.0 (unimportant) to 1.0 (critical)
ALTER TABLE entities ADD COLUMN emotional_tags TEXT DEFAULT '[]'; -- JSON: ["surprise", "achievement", ...]

-- Add action tracking columns
ALTER TABLE entities ADD COLUMN is_action BOOLEAN DEFAULT 0; -- Is this an action vs observation?
ALTER TABLE entities ADD COLUMN action_outcome_id INTEGER; -- Link to action_outcomes table
ALTER TABLE entities ADD COLUMN action_success REAL; -- Quick reference to success score

-- Add temporal columns
ALTER TABLE entities ADD COLUMN causally_linked_to INTEGER; -- Entity ID that caused this
ALTER TABLE entities ADD COLUMN causal_confidence REAL; -- How confident in causal link

-- ============================================================================
-- INDEXES: Performance optimization for new tables
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_session_agent ON session_continuity(agent_id);
CREATE INDEX IF NOT EXISTS idx_session_started ON session_continuity(started_at);
CREATE INDEX IF NOT EXISTS idx_session_previous ON session_continuity(previous_session_id);

CREATE INDEX IF NOT EXISTS idx_action_entity ON action_outcomes(entity_id);
CREATE INDEX IF NOT EXISTS idx_action_session ON action_outcomes(session_id);
CREATE INDEX IF NOT EXISTS idx_action_type ON action_outcomes(action_type);
CREATE INDEX IF NOT EXISTS idx_action_success ON action_outcomes(success_score);
CREATE INDEX IF NOT EXISTS idx_action_executed ON action_outcomes(executed_at);

CREATE INDEX IF NOT EXISTS idx_entities_salience ON entities(salience_score);
CREATE INDEX IF NOT EXISTS idx_entities_emotion ON entities(emotional_valence);
CREATE INDEX IF NOT EXISTS idx_entities_action ON entities(is_action);
CREATE INDEX IF NOT EXISTS idx_entities_causal ON entities(causally_linked_to);

-- ============================================================================
-- INITIAL DATA: Create default agent identity
-- ============================================================================

INSERT OR IGNORE INTO agent_identity (agent_id, created_at)
VALUES ('default_agent', CURRENT_TIMESTAMP);
