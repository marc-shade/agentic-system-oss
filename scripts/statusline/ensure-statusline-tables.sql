-- Ensure all tables needed for agentic statusline observability exist
-- Run against enhanced-memory-mcp database

-- Action outcomes table (for learning rate)
CREATE TABLE IF NOT EXISTS action_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    action_description TEXT,
    expected_result TEXT,
    actual_result TEXT,
    success_score REAL DEFAULT 0.5,
    session_id TEXT,
    entity_id INTEGER,
    action_context TEXT,
    duration_ms INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_action_outcomes_created ON action_outcomes(created_at);
CREATE INDEX IF NOT EXISTS idx_action_outcomes_type ON action_outcomes(action_type);

-- Knowledge gaps table (for learning needs)
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT DEFAULT 'default_agent',
    domain TEXT NOT NULL,
    gap_description TEXT NOT NULL,
    gap_type TEXT DEFAULT 'factual',  -- factual, procedural, conceptual, meta
    severity REAL DEFAULT 0.5,
    status TEXT DEFAULT 'open',  -- open, learning, resolved
    learning_progress REAL DEFAULT 0.0,
    learning_plan TEXT,
    discovered_by TEXT DEFAULT 'self-reflection',
    discovery_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_status ON knowledge_gaps(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_gaps_severity ON knowledge_gaps(severity);

-- Improvement cycles table (for self-improvement tracking)
CREATE TABLE IF NOT EXISTS improvement_cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT DEFAULT 'default_agent',
    cycle_type TEXT NOT NULL,  -- performance, knowledge, reasoning, meta
    cycle_number INTEGER,
    status TEXT DEFAULT 'pending',  -- pending, baseline_assessed, strategies_applied, validated, completed
    improvement_goals TEXT,
    baseline_metrics TEXT,
    identified_weaknesses TEXT,
    strategies TEXT,
    changes TEXT,
    new_metrics TEXT,
    success_criteria TEXT,
    lessons_learned TEXT,
    next_recommendations TEXT,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_improvement_cycles_status ON improvement_cycles(status);

-- Consolidation jobs table (for memory health)
CREATE TABLE IF NOT EXISTS consolidation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,  -- pattern_extraction, causal_discovery, compression, full
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    time_window_hours INTEGER DEFAULT 24,
    patterns_found INTEGER DEFAULT 0,
    patterns_promoted INTEGER DEFAULT 0,
    chains_created INTEGER DEFAULT 0,
    links_created INTEGER DEFAULT 0,
    memories_compressed INTEGER DEFAULT 0,
    space_saved_bytes INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_status ON consolidation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_consolidation_jobs_completed ON consolidation_jobs(completed_at);

-- Verify tables created
SELECT 'action_outcomes' as table_name, COUNT(*) as row_count FROM action_outcomes
UNION ALL
SELECT 'knowledge_gaps', COUNT(*) FROM knowledge_gaps
UNION ALL
SELECT 'improvement_cycles', COUNT(*) FROM improvement_cycles
UNION ALL
SELECT 'consolidation_jobs', COUNT(*) FROM consolidation_jobs;
