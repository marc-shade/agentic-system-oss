-- ============================================================================
-- AGI Memory Phase 3: Emotional Tagging & Associative Networks
-- ============================================================================
-- Purpose: Add emotional context and associative recall to memory system
--
-- Features:
-- 1. Emotional valence and arousal for memories
-- 2. Importance/salience scoring
-- 3. Associative links between memories
-- 4. Context-dependent retrieval
-- 5. Attention mechanisms
-- 6. Forgetting curves
-- ============================================================================

-- ============================================================================
-- TABLE: emotional_tags
-- Purpose: Store emotional metadata for entities
-- ============================================================================
CREATE TABLE IF NOT EXISTS emotional_tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,

    -- Emotion dimensions (Russell's circumplex model)
    valence REAL NOT NULL DEFAULT 0.0,        -- -1.0 (negative) to +1.0 (positive)
    arousal REAL NOT NULL DEFAULT 0.0,        -- 0.0 (calm) to 1.0 (excited)
    dominance REAL DEFAULT 0.5,               -- 0.0 (controlled) to 1.0 (in control)

    -- Specific emotions (optional, can be NULL)
    primary_emotion TEXT,                     -- joy, sadness, anger, fear, surprise, disgust
    emotion_intensity REAL DEFAULT 0.5,       -- 0.0 to 1.0

    -- Importance/salience
    salience_score REAL NOT NULL DEFAULT 0.5, -- 0.0 (unimportant) to 1.0 (critical)
    personal_significance REAL DEFAULT 0.5,   -- How personally relevant (0.0-1.0)

    -- Context
    context_type TEXT,                        -- "success", "failure", "neutral", "surprising"
    emotional_context TEXT,                   -- JSON: additional context

    -- Decay (forgetting curve)
    initial_strength REAL DEFAULT 1.0,        -- Initial memory strength
    current_strength REAL DEFAULT 1.0,        -- Current strength (decays over time)
    decay_rate REAL DEFAULT 0.1,              -- How fast it decays (0.0-1.0)
    last_accessed TIMESTAMP,                  -- Last retrieval (resets decay)
    access_count INTEGER DEFAULT 0,           -- Number of retrievals

    -- Metadata
    tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(entity_id)  -- One emotional tag per entity
);

CREATE INDEX IF NOT EXISTS idx_emotional_tags_entity ON emotional_tags(entity_id);
CREATE INDEX IF NOT EXISTS idx_emotional_tags_valence ON emotional_tags(valence);
CREATE INDEX IF NOT EXISTS idx_emotional_tags_arousal ON emotional_tags(arousal);
CREATE INDEX IF NOT EXISTS idx_emotional_tags_salience ON emotional_tags(salience_score);
CREATE INDEX IF NOT EXISTS idx_emotional_tags_strength ON emotional_tags(current_strength);

-- ============================================================================
-- TABLE: memory_associations
-- Purpose: Store associative links between memories
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_associations (
    association_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The two associated entities
    entity_a_id INTEGER NOT NULL,
    entity_b_id INTEGER NOT NULL,

    -- Association metadata
    association_type TEXT NOT NULL,           -- "semantic", "temporal", "causal", "emotional", "spatial"
    association_strength REAL NOT NULL DEFAULT 0.5, -- 0.0 to 1.0

    -- Directionality
    bidirectional BOOLEAN DEFAULT TRUE,       -- Can activate in both directions?

    -- Activation spreading
    activation_threshold REAL DEFAULT 0.3,    -- Minimum strength to spread activation
    spread_decay REAL DEFAULT 0.5,            -- How much activation decreases when spreading

    -- Context conditions
    context_dependent BOOLEAN DEFAULT FALSE,  -- Only activates in certain contexts?
    context_conditions TEXT,                  -- JSON: required context

    -- Learning and reinforcement
    co_activation_count INTEGER DEFAULT 0,    -- How often activated together
    last_co_activation TIMESTAMP,
    reinforcement_rate REAL DEFAULT 0.1,      -- How fast strength increases with co-activation

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discovered_method TEXT,                   -- "manual", "consolidation", "spreading"

    FOREIGN KEY (entity_a_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_b_id) REFERENCES entities(id) ON DELETE CASCADE,
    CHECK (entity_a_id < entity_b_id),  -- Prevent duplicates (always a < b)
    UNIQUE(entity_a_id, entity_b_id)
);

CREATE INDEX IF NOT EXISTS idx_associations_a ON memory_associations(entity_a_id);
CREATE INDEX IF NOT EXISTS idx_associations_b ON memory_associations(entity_b_id);
CREATE INDEX IF NOT EXISTS idx_associations_type ON memory_associations(association_type);
CREATE INDEX IF NOT EXISTS idx_associations_strength ON memory_associations(association_strength);

-- ============================================================================
-- TABLE: retrieval_contexts
-- Purpose: Store context for context-dependent retrieval
-- ============================================================================
CREATE TABLE IF NOT EXISTS retrieval_contexts (
    context_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Context definition
    context_name TEXT NOT NULL UNIQUE,
    context_type TEXT NOT NULL,               -- "temporal", "emotional", "task", "environmental"

    -- Context features (JSON)
    features TEXT NOT NULL,                   -- JSON: {"time_of_day": "morning", "mood": "focused"}

    -- Active entities in this context
    active_entities TEXT,                     -- JSON: list of entity IDs

    -- Context statistics
    activation_count INTEGER DEFAULT 0,
    last_activated TIMESTAMP,
    average_duration_seconds INTEGER,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contexts_name ON retrieval_contexts(context_name);
CREATE INDEX IF NOT EXISTS idx_contexts_type ON retrieval_contexts(context_type);

-- ============================================================================
-- TABLE: attention_weights
-- Purpose: Store attention mechanisms for selective retrieval
-- ============================================================================
CREATE TABLE IF NOT EXISTS attention_weights (
    weight_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- What is being attended to
    entity_id INTEGER NOT NULL,

    -- Attention dimensions
    relevance_score REAL NOT NULL DEFAULT 0.5, -- How relevant right now (0.0-1.0)
    recency_weight REAL DEFAULT 0.3,           -- Weight for recent vs old (0.0-1.0)
    frequency_weight REAL DEFAULT 0.3,         -- Weight for frequently accessed (0.0-1.0)
    emotional_weight REAL DEFAULT 0.4,         -- Weight for emotional salience (0.0-1.0)

    -- Context-specific attention
    context_id INTEGER,                        -- NULL = global attention

    -- Attention state
    current_attention REAL DEFAULT 0.0,        -- Current attention level (0.0-1.0)
    attention_decay_rate REAL DEFAULT 0.2,     -- How fast attention fades

    -- Learning
    manual_boost REAL DEFAULT 0.0,             -- Manual attention boost (-1.0 to 1.0)
    learned_importance REAL DEFAULT 0.0,       -- Learned from usage patterns

    -- Metadata
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (context_id) REFERENCES retrieval_contexts(context_id) ON DELETE CASCADE,
    UNIQUE(entity_id, context_id)
);

CREATE INDEX IF NOT EXISTS idx_attention_entity ON attention_weights(entity_id);
CREATE INDEX IF NOT EXISTS idx_attention_context ON attention_weights(context_id);
CREATE INDEX IF NOT EXISTS idx_attention_current ON attention_weights(current_attention);
CREATE INDEX IF NOT EXISTS idx_attention_relevance ON attention_weights(relevance_score);

-- ============================================================================
-- TABLE: forgetting_curves
-- Purpose: Track memory decay and forgetting patterns
-- ============================================================================
CREATE TABLE IF NOT EXISTS forgetting_curves (
    curve_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,

    -- Ebbinghaus forgetting curve parameters
    initial_strength REAL NOT NULL DEFAULT 1.0,
    current_strength REAL NOT NULL DEFAULT 1.0,
    decay_constant REAL NOT NULL DEFAULT 0.5,  -- k in: strength = e^(-kt)

    -- Spacing effect (repeated retrieval)
    retrieval_count INTEGER DEFAULT 0,
    optimal_next_review TIMESTAMP,             -- When to review for best retention

    -- Interference
    proactive_interference REAL DEFAULT 0.0,   -- Old memories interfering (0.0-1.0)
    retroactive_interference REAL DEFAULT 0.0, -- New memories interfering (0.0-1.0)

    -- Measurement
    last_strength_check TIMESTAMP,
    strength_history TEXT,                     -- JSON: [{timestamp, strength}, ...]

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_forgetting_entity ON forgetting_curves(entity_id);
CREATE INDEX IF NOT EXISTS idx_forgetting_strength ON forgetting_curves(current_strength);
CREATE INDEX IF NOT EXISTS idx_forgetting_review ON forgetting_curves(optimal_next_review);

-- ============================================================================
-- TABLE: activation_spreading_log
-- Purpose: Log activation spreading events for analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS activation_spreading_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Spreading event
    source_entity_id INTEGER NOT NULL,
    activated_entity_id INTEGER NOT NULL,
    association_id INTEGER,

    -- Spreading details
    initial_activation REAL NOT NULL,
    final_activation REAL NOT NULL,
    spread_distance INTEGER,                   -- How many hops from source

    -- Context
    context_id INTEGER,
    spreading_triggered_by TEXT,               -- "query", "consolidation", "manual"

    -- Timestamp
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (activated_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (association_id) REFERENCES memory_associations(association_id) ON DELETE SET NULL,
    FOREIGN KEY (context_id) REFERENCES retrieval_contexts(context_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_spreading_source ON activation_spreading_log(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_spreading_activated ON activation_spreading_log(activated_entity_id);
CREATE INDEX IF NOT EXISTS idx_spreading_time ON activation_spreading_log(occurred_at);

-- ============================================================================
-- VIEWS: Convenient queries for Phase 3
-- ============================================================================

-- High salience memories
CREATE VIEW IF NOT EXISTS high_salience_memories AS
SELECT
    e.id,
    e.name,
    e.entity_type,
    et.salience_score,
    et.valence,
    et.arousal,
    et.primary_emotion,
    et.current_strength
FROM entities e
JOIN emotional_tags et ON e.id = et.entity_id
WHERE et.salience_score >= 0.7
ORDER BY et.salience_score DESC;

-- Strong associations
CREATE VIEW IF NOT EXISTS strong_associations AS
SELECT
    ma.association_id,
    ma.entity_a_id,
    e1.name as entity_a_name,
    ma.entity_b_id,
    e2.name as entity_b_name,
    ma.association_type,
    ma.association_strength,
    ma.co_activation_count
FROM memory_associations ma
JOIN entities e1 ON ma.entity_a_id = e1.id
JOIN entities e2 ON ma.entity_b_id = e2.id
WHERE ma.association_strength >= 0.7
ORDER BY ma.association_strength DESC;

-- Memories needing review (forgetting curve)
CREATE VIEW IF NOT EXISTS memories_needing_review AS
SELECT
    e.id,
    e.name,
    e.entity_type,
    fc.current_strength,
    fc.optimal_next_review,
    fc.retrieval_count
FROM entities e
JOIN forgetting_curves fc ON e.id = fc.entity_id
WHERE fc.current_strength < 0.5
   OR fc.optimal_next_review <= datetime('now')
ORDER BY fc.optimal_next_review ASC;

-- Currently attended memories
CREATE VIEW IF NOT EXISTS attended_memories AS
SELECT
    e.id,
    e.name,
    e.entity_type,
    aw.current_attention,
    aw.relevance_score,
    rc.context_name
FROM entities e
JOIN attention_weights aw ON e.id = aw.entity_id
LEFT JOIN retrieval_contexts rc ON aw.context_id = rc.context_id
WHERE aw.current_attention >= 0.3
ORDER BY aw.current_attention DESC;

-- Emotional memory clusters
CREATE VIEW IF NOT EXISTS emotional_clusters AS
SELECT
    et.primary_emotion,
    COUNT(*) as memory_count,
    AVG(et.valence) as avg_valence,
    AVG(et.arousal) as avg_arousal,
    AVG(et.salience_score) as avg_salience
FROM emotional_tags et
WHERE et.primary_emotion IS NOT NULL
GROUP BY et.primary_emotion
ORDER BY memory_count DESC;

-- ============================================================================
-- TRIGGERS: Automatic maintenance
-- ============================================================================

-- Update emotional_tags.updated_at on modification
CREATE TRIGGER IF NOT EXISTS update_emotional_tags_timestamp
AFTER UPDATE ON emotional_tags
BEGIN
    UPDATE emotional_tags
    SET updated_at = CURRENT_TIMESTAMP
    WHERE tag_id = NEW.tag_id;
END;

-- Update memory_associations.updated_at on modification
CREATE TRIGGER IF NOT EXISTS update_associations_timestamp
AFTER UPDATE ON memory_associations
BEGIN
    UPDATE memory_associations
    SET updated_at = CURRENT_TIMESTAMP
    WHERE association_id = NEW.association_id;
END;

-- Increment co-activation count when association is strengthened
CREATE TRIGGER IF NOT EXISTS track_coactivation
AFTER UPDATE OF association_strength ON memory_associations
WHEN NEW.association_strength > OLD.association_strength
BEGIN
    UPDATE memory_associations
    SET
        co_activation_count = co_activation_count + 1,
        last_co_activation = CURRENT_TIMESTAMP
    WHERE association_id = NEW.association_id;
END;

-- Update forgetting curve when entity is accessed
CREATE TRIGGER IF NOT EXISTS update_forgetting_on_access
AFTER UPDATE OF access_count ON entities
BEGIN
    UPDATE forgetting_curves
    SET
        retrieval_count = retrieval_count + 1,
        last_strength_check = CURRENT_TIMESTAMP,
        -- Reset strength on retrieval (spacing effect)
        current_strength = MIN(1.0, current_strength + 0.2)
    WHERE entity_id = NEW.id;
END;

-- ============================================================================
-- INITIALIZATION: Default data
-- ============================================================================

-- Default retrieval contexts
INSERT OR IGNORE INTO retrieval_contexts (context_name, context_type, features)
VALUES
    ('morning_routine', 'temporal', '{"time_of_day": "morning", "energy_level": "high"}'),
    ('evening_reflection', 'temporal', '{"time_of_day": "evening", "energy_level": "low"}'),
    ('focused_work', 'task', '{"task_type": "coding", "interruptions": "low"}'),
    ('creative_mode', 'emotional', '{"mood": "creative", "openness": "high"}'),
    ('problem_solving', 'task', '{"task_type": "debugging", "stress_level": "medium"}');

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Phase 3 schema is ready for emotional tagging and associative networks
-- ============================================================================
