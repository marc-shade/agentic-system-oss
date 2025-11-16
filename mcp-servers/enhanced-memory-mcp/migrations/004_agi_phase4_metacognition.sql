-- ============================================================================
-- AGI Memory Phase 4: Meta-Cognitive Awareness & Self-Improvement
-- ============================================================================
-- Purpose: Add meta-cognitive capabilities and self-improvement mechanisms
--
-- Features:
-- 1. Meta-cognitive monitoring (thinking about thinking)
-- 2. Self-improvement loops
-- 3. Performance tracking and optimization
-- 4. Knowledge gap detection
-- 5. Learning strategy adaptation
-- 6. Multi-agent coordination
-- ============================================================================

-- ============================================================================
-- TABLE: metacognitive_states
-- Purpose: Track meta-cognitive awareness states
-- ============================================================================
CREATE TABLE IF NOT EXISTS metacognitive_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT,

    -- Awareness levels (0.0-1.0)
    self_awareness REAL DEFAULT 0.5,           -- Awareness of own existence
    knowledge_awareness REAL DEFAULT 0.5,       -- Awareness of what it knows
    process_awareness REAL DEFAULT 0.5,         -- Awareness of how it thinks
    limitation_awareness REAL DEFAULT 0.5,      -- Awareness of limitations

    -- Current cognitive state
    cognitive_load REAL DEFAULT 0.5,            -- Mental effort level (0.0-1.0)
    confidence_level REAL DEFAULT 0.5,          -- Confidence in current reasoning
    uncertainty_level REAL DEFAULT 0.5,         -- Recognized uncertainty

    -- Reasoning quality
    reasoning_depth INTEGER DEFAULT 0,          -- Depth of current reasoning
    alternative_perspectives INTEGER DEFAULT 0, -- Alternatives considered
    assumption_count INTEGER DEFAULT 0,         -- Assumptions made

    -- Meta-cognitive actions
    self_reflection_count INTEGER DEFAULT 0,
    strategy_adjustments INTEGER DEFAULT 0,
    knowledge_gap_checks INTEGER DEFAULT 0,

    -- Context
    task_context TEXT,                          -- JSON: what task is being performed
    reasoning_trace TEXT,                       -- JSON: trace of reasoning steps

    -- Timestamp
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metacog_agent ON metacognitive_states(agent_id);
CREATE INDEX IF NOT EXISTS idx_metacog_session ON metacognitive_states(session_id);
CREATE INDEX IF NOT EXISTS idx_metacog_time ON metacognitive_states(recorded_at);

-- ============================================================================
-- TABLE: knowledge_gaps
-- Purpose: Track identified knowledge gaps for targeted learning
-- ============================================================================
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,

    -- Gap definition
    domain TEXT NOT NULL,                       -- What domain/topic
    gap_description TEXT NOT NULL,
    gap_type TEXT NOT NULL,                     -- "factual", "procedural", "conceptual", "meta"
    severity REAL DEFAULT 0.5,                  -- How critical (0.0-1.0)

    -- Discovery
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discovered_by TEXT,                         -- "self-reflection", "failure", "query"
    discovery_context TEXT,                     -- JSON: circumstances of discovery

    -- Resolution
    status TEXT DEFAULT 'open',                 -- "open", "learning", "resolved"
    learning_plan TEXT,                         -- JSON: plan to fill gap
    resolution_strategy TEXT,                   -- How to address this gap

    -- Progress tracking
    learning_progress REAL DEFAULT 0.0,         -- 0.0 to 1.0
    attempts_count INTEGER DEFAULT 0,
    resources_consulted TEXT,                   -- JSON: what was used to learn

    -- Verification
    verified BOOLEAN DEFAULT FALSE,
    verification_method TEXT,
    verification_score REAL,

    -- Metadata
    resolved_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gaps_agent ON knowledge_gaps(agent_id);
CREATE INDEX IF NOT EXISTS idx_gaps_domain ON knowledge_gaps(domain);
CREATE INDEX IF NOT EXISTS idx_gaps_status ON knowledge_gaps(status);
CREATE INDEX IF NOT EXISTS idx_gaps_severity ON knowledge_gaps(severity);

-- ============================================================================
-- TABLE: self_improvement_cycles
-- Purpose: Track self-improvement iterations
-- ============================================================================
CREATE TABLE IF NOT EXISTS self_improvement_cycles (
    cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,

    -- Cycle metadata
    cycle_number INTEGER NOT NULL,
    cycle_type TEXT NOT NULL,                   -- "performance", "knowledge", "reasoning", "meta"

    -- Assessment phase
    baseline_performance REAL,                  -- Before improvement
    identified_weaknesses TEXT,                 -- JSON: list of weaknesses
    improvement_goals TEXT,                     -- JSON: specific goals

    -- Execution phase
    strategies_applied TEXT,                    -- JSON: improvement strategies used
    changes_made TEXT,                          -- JSON: what was changed
    experiments_run INTEGER DEFAULT 0,

    -- Validation phase
    new_performance REAL,                       -- After improvement
    improvement_delta REAL,                     -- Change in performance
    success_criteria_met BOOLEAN DEFAULT FALSE,

    -- Learning
    lessons_learned TEXT,                       -- JSON: insights from cycle
    next_cycle_recommendations TEXT,            -- JSON: what to try next

    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    FOREIGN KEY (agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_improvement_agent ON self_improvement_cycles(agent_id);
CREATE INDEX IF NOT EXISTS idx_improvement_cycle ON self_improvement_cycles(cycle_number);
CREATE INDEX IF NOT EXISTS idx_improvement_type ON self_improvement_cycles(cycle_type);

-- ============================================================================
-- TABLE: reasoning_strategies
-- Purpose: Track different reasoning strategies and their effectiveness
-- ============================================================================
CREATE TABLE IF NOT EXISTS reasoning_strategies (
    strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,

    -- Strategy definition
    strategy_name TEXT NOT NULL UNIQUE,
    strategy_type TEXT NOT NULL,                -- "deductive", "inductive", "abductive", "analogical"
    strategy_description TEXT,

    -- Applicability
    applicable_contexts TEXT,                   -- JSON: when to use this strategy
    required_knowledge TEXT,                    -- JSON: prerequisites

    -- Performance tracking
    times_used INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    average_confidence REAL DEFAULT 0.5,

    -- Optimization
    optimal_conditions TEXT,                    -- JSON: when it works best
    known_limitations TEXT,                     -- JSON: when it fails
    improvement_suggestions TEXT,               -- JSON: how to improve

    -- Learning
    last_used TIMESTAMP,
    last_success TIMESTAMP,
    adaptation_count INTEGER DEFAULT 0,         -- Times strategy was adapted

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_strategies_agent ON reasoning_strategies(agent_id);
CREATE INDEX IF NOT EXISTS idx_strategies_name ON reasoning_strategies(strategy_name);
CREATE INDEX IF NOT EXISTS idx_strategies_type ON reasoning_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_strategies_success ON reasoning_strategies(success_rate);

-- ============================================================================
-- TABLE: performance_metrics
-- Purpose: Track performance across different dimensions
-- ============================================================================
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

    FOREIGN KEY (agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE,
    UNIQUE(agent_id, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_metrics_agent ON performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_metrics_category ON performance_metrics(metric_category);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON performance_metrics(metric_name);

-- ============================================================================
-- TABLE: coordination_messages
-- Purpose: Multi-agent coordination and communication
-- ============================================================================
CREATE TABLE IF NOT EXISTS coordination_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Communication
    sender_agent_id TEXT NOT NULL,
    recipient_agent_id TEXT,                    -- NULL = broadcast
    message_type TEXT NOT NULL,                 -- "request", "response", "notification", "coordination"

    -- Content
    subject TEXT,
    message_content TEXT NOT NULL,              -- JSON: structured message
    priority REAL DEFAULT 0.5,                  -- 0.0 (low) to 1.0 (urgent)

    -- Context
    task_context TEXT,                          -- JSON: what task this relates to
    shared_goal_id INTEGER,                     -- Reference to shared goal

    -- State
    status TEXT DEFAULT 'pending',              -- "pending", "delivered", "acknowledged", "completed"
    requires_response BOOLEAN DEFAULT FALSE,
    response_deadline TIMESTAMP,

    -- Response
    response_message_id INTEGER,                -- Link to response
    acknowledged_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Metadata
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sender_agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_agent_id) REFERENCES agent_identity(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (response_message_id) REFERENCES coordination_messages(message_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_coord_sender ON coordination_messages(sender_agent_id);
CREATE INDEX IF NOT EXISTS idx_coord_recipient ON coordination_messages(recipient_agent_id);
CREATE INDEX IF NOT EXISTS idx_coord_status ON coordination_messages(status);
CREATE INDEX IF NOT EXISTS idx_coord_type ON coordination_messages(message_type);

-- ============================================================================
-- VIEWS: Convenient queries for Phase 4
-- ============================================================================

-- Current meta-cognitive state
CREATE VIEW IF NOT EXISTS current_metacognitive_state AS
SELECT
    ms.agent_id,
    ms.self_awareness,
    ms.knowledge_awareness,
    ms.process_awareness,
    ms.limitation_awareness,
    ms.cognitive_load,
    ms.confidence_level,
    ms.uncertainty_level,
    ms.recorded_at
FROM metacognitive_states ms
WHERE ms.recorded_at = (
    SELECT MAX(recorded_at)
    FROM metacognitive_states
    WHERE agent_id = ms.agent_id
);

-- Open knowledge gaps by severity
CREATE VIEW IF NOT EXISTS critical_knowledge_gaps AS
SELECT
    kg.gap_id,
    kg.agent_id,
    kg.domain,
    kg.gap_description,
    kg.severity,
    kg.status,
    kg.learning_progress,
    kg.discovered_at
FROM knowledge_gaps kg
WHERE kg.status != 'resolved'
  AND kg.severity >= 0.7
ORDER BY kg.severity DESC, kg.discovered_at ASC;

-- Recent self-improvement progress
CREATE VIEW IF NOT EXISTS improvement_progress AS
SELECT
    sic.agent_id,
    sic.cycle_number,
    sic.cycle_type,
    sic.baseline_performance,
    sic.new_performance,
    sic.improvement_delta,
    sic.success_criteria_met,
    sic.completed_at
FROM self_improvement_cycles sic
WHERE sic.completed_at IS NOT NULL
ORDER BY sic.cycle_number DESC
LIMIT 10;

-- Most effective reasoning strategies
CREATE VIEW IF NOT EXISTS effective_strategies AS
SELECT
    rs.strategy_name,
    rs.strategy_type,
    rs.times_used,
    rs.success_rate,
    rs.average_confidence,
    rs.last_used
FROM reasoning_strategies rs
WHERE rs.times_used >= 3
  AND rs.success_rate >= 0.6
ORDER BY rs.success_rate DESC, rs.times_used DESC;

-- Performance trends
CREATE VIEW IF NOT EXISTS performance_trends AS
SELECT
    pm.agent_id,
    pm.metric_name,
    pm.metric_category,
    pm.current_value,
    pm.baseline_value,
    pm.target_value,
    pm.trend,
    CASE
        WHEN pm.target_value IS NOT NULL THEN
            (pm.current_value - pm.baseline_value) / (pm.target_value - pm.baseline_value)
        ELSE NULL
    END as progress_percentage,
    pm.updated_at
FROM performance_metrics pm
ORDER BY pm.metric_category, pm.metric_name;

-- Pending coordination tasks
CREATE VIEW IF NOT EXISTS pending_coordination AS
SELECT
    cm.message_id,
    cm.sender_agent_id,
    cm.recipient_agent_id,
    cm.message_type,
    cm.subject,
    cm.priority,
    cm.requires_response,
    cm.response_deadline,
    cm.sent_at
FROM coordination_messages cm
WHERE cm.status IN ('pending', 'delivered')
  AND (cm.response_deadline IS NULL OR cm.response_deadline > datetime('now'))
ORDER BY cm.priority DESC, cm.sent_at ASC;

-- ============================================================================
-- TRIGGERS: Automatic maintenance
-- ============================================================================

-- Update performance metrics trend
CREATE TRIGGER IF NOT EXISTS update_performance_trend
AFTER UPDATE OF current_value ON performance_metrics
BEGIN
    UPDATE performance_metrics
    SET
        trend = CASE
            WHEN NEW.current_value > OLD.current_value * 1.05 THEN 'improving'
            WHEN NEW.current_value < OLD.current_value * 0.95 THEN 'declining'
            ELSE 'stable'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE metric_id = NEW.metric_id;
END;

-- Update reasoning strategy success rate
CREATE TRIGGER IF NOT EXISTS update_strategy_success_rate
AFTER UPDATE OF success_count, failure_count ON reasoning_strategies
BEGIN
    UPDATE reasoning_strategies
    SET
        success_rate = CAST(NEW.success_count AS REAL) /
                       NULLIF(NEW.success_count + NEW.failure_count, 0),
        updated_at = CURRENT_TIMESTAMP
    WHERE strategy_id = NEW.strategy_id;
END;

-- Auto-resolve knowledge gaps when learning complete
CREATE TRIGGER IF NOT EXISTS auto_resolve_gaps
AFTER UPDATE OF learning_progress ON knowledge_gaps
WHEN NEW.learning_progress >= 1.0 AND NEW.status != 'resolved'
BEGIN
    UPDATE knowledge_gaps
    SET
        status = 'resolved',
        resolved_at = CURRENT_TIMESTAMP
    WHERE gap_id = NEW.gap_id;
END;

-- ============================================================================
-- INITIALIZATION: Default data
-- ============================================================================

-- Default reasoning strategies (common patterns)
INSERT OR IGNORE INTO reasoning_strategies (agent_id, strategy_name, strategy_type, strategy_description)
VALUES
    ('default', 'deductive_logic', 'deductive', 'Apply general rules to specific cases'),
    ('default', 'inductive_generalization', 'inductive', 'Generalize from specific examples'),
    ('default', 'analogical_reasoning', 'analogical', 'Reason by analogy to known cases'),
    ('default', 'causal_reasoning', 'abductive', 'Infer causes from observed effects'),
    ('default', 'first_principles', 'deductive', 'Break down to fundamental truths');

-- Default performance metrics categories
INSERT OR IGNORE INTO performance_metrics (agent_id, metric_name, metric_category, current_value, baseline_value)
VALUES
    ('default', 'reasoning_speed', 'cognitive', 0.5, 0.5),
    ('default', 'reasoning_accuracy', 'cognitive', 0.5, 0.5),
    ('default', 'knowledge_breadth', 'knowledge', 0.5, 0.5),
    ('default', 'knowledge_depth', 'knowledge', 0.5, 0.5),
    ('default', 'self_awareness', 'meta', 0.5, 0.5),
    ('default', 'adaptation_speed', 'meta', 0.5, 0.5);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Phase 4 schema is ready for meta-cognitive awareness and self-improvement
-- ============================================================================
