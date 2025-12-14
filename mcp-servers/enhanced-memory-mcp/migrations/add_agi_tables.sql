-- Add AGI Tables to Enhanced Memory Database
-- This migration adds all AGI-related tables that were missing
-- Date: 2025-11-22

-- ================================================================
-- ACTION OUTCOMES TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS action_outcomes (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    entity_id INTEGER,
    session_id TEXT,

    -- Action details
    action_type TEXT NOT NULL,  -- code_change, command_execution, research, etc.
    action_description TEXT NOT NULL,
    action_context TEXT,  -- What led to this action

    -- Expected vs actual
    expected_result TEXT,
    actual_result TEXT,

    -- Outcome assessment
    success_score REAL DEFAULT 0.5,  -- 0.0 (failure) to 1.0 (success)
    outcome_category TEXT,  -- success, partial, failure, error

    -- Learning extraction
    learning_extracted TEXT,  -- What did we learn from this?
    will_retry BOOLEAN DEFAULT 0,
    retry_with_changes TEXT,  -- What to change if retrying

    -- Timing
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,

    -- Metadata
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_action_outcomes_type
    ON action_outcomes(agent_id, action_type, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_action_outcomes_success
    ON action_outcomes(agent_id, success, success_score DESC);

-- ================================================================
-- KNOWLEDGE GAPS TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Gap identification
    domain TEXT NOT NULL,
    gap_description TEXT NOT NULL,
    gap_type TEXT DEFAULT 'factual',  -- factual, procedural, conceptual, meta
    severity REAL NOT NULL,  -- 0.0-1.0

    -- Discovery
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ADDED: When gap was discovered
    discovered_by TEXT DEFAULT 'self-reflection',
    discovery_context TEXT DEFAULT '{}',  -- JSON

    -- Learning progress
    status TEXT DEFAULT 'open',  -- open, learning, resolved
    learning_progress REAL DEFAULT 0.0,  -- 0.0-1.0
    learning_plan TEXT DEFAULT '{}',  -- JSON

    -- Resolution
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status
    ON knowledge_gaps(agent_id, status, severity DESC);

CREATE TRIGGER IF NOT EXISTS update_knowledge_gap_timestamp
AFTER UPDATE ON knowledge_gaps
BEGIN
    UPDATE knowledge_gaps
    SET updated_at = CURRENT_TIMESTAMP
    WHERE gap_id = NEW.gap_id;
END;

CREATE TRIGGER IF NOT EXISTS auto_resolve_knowledge_gap
AFTER UPDATE OF learning_progress ON knowledge_gaps
WHEN NEW.learning_progress >= 1.0 AND NEW.status != 'resolved'
BEGIN
    UPDATE knowledge_gaps
    SET status = 'resolved',
        resolved_at = CURRENT_TIMESTAMP
    WHERE gap_id = NEW.gap_id;
END;

-- ================================================================
-- METACOGNITIVE STATES TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS metacognitive_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Awareness dimensions (0.0-1.0)
    self_awareness REAL DEFAULT 0.5,
    knowledge_awareness REAL DEFAULT 0.5,
    process_awareness REAL DEFAULT 0.5,
    limitation_awareness REAL DEFAULT 0.5,

    -- Cognitive state
    cognitive_load REAL DEFAULT 0.5,
    confidence_level REAL DEFAULT 0.5,
    uncertainty_level REAL DEFAULT 0.5,  -- Added: 1.0 - confidence

    -- Context
    task_context TEXT DEFAULT '{}',  -- JSON
    reasoning_trace TEXT DEFAULT '[]'  -- JSON array
);

CREATE INDEX IF NOT EXISTS idx_metacognitive_states
    ON metacognitive_states(agent_id, recorded_at DESC);

-- ================================================================
-- REASONING STRATEGIES TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS reasoning_strategies (
    strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Strategy identification
    strategy_name TEXT NOT NULL,
    strategy_type TEXT NOT NULL,  -- deductive, inductive, abductive, analogical

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,

    -- Performance
    average_confidence REAL DEFAULT 0.5,
    success_rate REAL DEFAULT 0.0,

    -- Context
    effective_contexts TEXT DEFAULT '[]',  -- JSON array

    UNIQUE(agent_id, strategy_name)
);

CREATE TRIGGER IF NOT EXISTS update_reasoning_strategy_timestamp
AFTER UPDATE ON reasoning_strategies
BEGIN
    UPDATE reasoning_strategies
    SET updated_at = CURRENT_TIMESTAMP
    WHERE strategy_id = NEW.strategy_id;
END;

CREATE TRIGGER IF NOT EXISTS update_strategy_success_rate
AFTER UPDATE OF success_count, usage_count ON reasoning_strategies
WHEN NEW.usage_count > 0
BEGIN
    UPDATE reasoning_strategies
    SET success_rate = CAST(success_count AS REAL) / usage_count
    WHERE strategy_id = NEW.strategy_id;
END;

-- ================================================================
-- PERFORMANCE TRENDS TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS performance_trends (
    trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Metric identification
    metric_name TEXT NOT NULL,
    metric_category TEXT NOT NULL,  -- cognitive, knowledge, social, meta

    -- Performance data
    current_value REAL NOT NULL,
    previous_value REAL,
    target_value REAL,

    -- Trend analysis
    trend TEXT DEFAULT 'stable',  -- improving, declining, stable
    change_rate REAL,

    -- Context
    measurement_context TEXT DEFAULT '{}'  -- JSON
);

CREATE INDEX IF NOT EXISTS idx_performance_trends
    ON performance_trends(agent_id, metric_name, recorded_at DESC);

-- ================================================================
-- IMPROVEMENT CYCLES TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS improvement_cycles (
    cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    cycle_number INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- Cycle type
    cycle_type TEXT NOT NULL,  -- performance, knowledge, reasoning, meta
    improvement_goals TEXT DEFAULT '{}',  -- JSON

    -- Baseline assessment
    baseline_metrics TEXT DEFAULT '{}',  -- JSON
    identified_weaknesses TEXT DEFAULT '[]',  -- JSON array

    -- Applied strategies
    strategies_applied TEXT DEFAULT '[]',  -- JSON array
    changes_made TEXT DEFAULT '[]',  -- JSON array

    -- Validation
    new_metrics TEXT DEFAULT '{}',  -- JSON
    success_criteria TEXT DEFAULT '{}',  -- JSON
    success BOOLEAN,

    -- Learnings
    lessons_learned TEXT DEFAULT '[]',  -- JSON array
    next_recommendations TEXT DEFAULT '[]',  -- JSON array

    -- Status
    status TEXT DEFAULT 'in_progress'  -- in_progress, completed, failed
);

CREATE INDEX IF NOT EXISTS idx_improvement_cycles
    ON improvement_cycles(agent_id, cycle_number DESC);

-- ================================================================
-- CONSOLIDATION JOBS TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS consolidation_jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- Job type
    job_type TEXT NOT NULL,  -- pattern_extraction, causal_discovery, compression, full
    time_window_hours INTEGER DEFAULT 24,

    -- Results
    patterns_extracted INTEGER DEFAULT 0,
    causal_links_created INTEGER DEFAULT 0,
    memories_compressed INTEGER DEFAULT 0,
    semantic_memories_created INTEGER DEFAULT 0,

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    error_message TEXT,

    -- Metadata
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_consolidation_jobs
    ON consolidation_jobs(agent_id, started_at DESC);

-- ================================================================
-- PERFORMANCE METRICS TABLE
-- ================================================================
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,

    -- Metric definition
    metric_name TEXT NOT NULL,                  -- "reasoning_speed", "accuracy", "creativity"
    metric_category TEXT NOT NULL,              -- "cognitive", "knowledge", "social", "meta"

    -- Measurement
    current_value REAL NOT NULL,
    baseline_value REAL,
    target_value REAL,

    -- History
    historical_values TEXT,                     -- JSON: [{timestamp, value}, ...]
    trend TEXT,                                 -- "improving", "declining", "stable"

    -- Analysis
    contributing_factors TEXT,                  -- JSON: what affects this metric
    improvement_actions TEXT,                   -- JSON: actions to improve

    -- Metadata
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(agent_id, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_metrics_agent ON performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_metrics_category ON performance_metrics(metric_category);

-- ================================================================
-- VERIFICATION
-- ================================================================
-- Run these queries to verify migration:
-- SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%action%' OR name LIKE '%knowledge%' OR name LIKE '%metacognitive%';
-- SELECT COUNT(*) FROM action_outcomes;
-- SELECT COUNT(*) FROM knowledge_gaps;
-- SELECT COUNT(*) FROM metacognitive_states;
