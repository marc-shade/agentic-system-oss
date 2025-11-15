"""
SAFLA Orchestrator - 4-Tier Memory Architecture
Self-Aware Feedback Loop with Adaptive Learning

Integrates with enhanced-memory MCP to provide:
- Working Memory: Temporary active context (short-term, volatile)
- Episodic Memory: Experiences and events (time-bound, contextual)
- Semantic Memory: Concepts and relationships (timeless knowledge)
- Procedural Memory: Skills and patterns (how-to knowledge)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class SAFLAOrchestrator:
    """
    SAFLA 4-Tier Memory Orchestrator

    Manages intelligent memory distribution across tiers with
    autonomous curation and meta-cognitive reasoning.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_safla_tables()

    def _init_safla_tables(self):
        """Initialize SAFLA-specific tables."""
        with sqlite3.connect(self.db_path) as conn:
            # Working memory - temporary, high-access, volatile
            conn.execute("""
                CREATE TABLE IF NOT EXISTS working_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER,
                    context_key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    ttl_minutes INTEGER DEFAULT 60,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    promoted_to TEXT,
                    FOREIGN KEY (entity_id) REFERENCES entities(id)
                )
            """)

            # Episodic memory - experiences, events, temporal
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER,
                    event_type TEXT NOT NULL,
                    episode_data TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    emotional_valence REAL,
                    significance_score REAL DEFAULT 0.5,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    consolidated_to_semantic BOOLEAN DEFAULT 0,
                    FOREIGN KEY (entity_id) REFERENCES entities(id)
                )
            """)

            # Semantic memory - concepts, relationships, timeless
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept_name TEXT UNIQUE NOT NULL,
                    concept_type TEXT,
                    definition TEXT,
                    related_concepts TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    source_episodes TEXT,
                    abstraction_level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Procedural memory - skills, patterns, how-to
            conn.execute("""
                CREATE TABLE IF NOT EXISTS procedural_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT UNIQUE NOT NULL,
                    skill_category TEXT,
                    procedure_steps TEXT NOT NULL,
                    preconditions TEXT,
                    success_criteria TEXT,
                    execution_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    avg_execution_time_ms INTEGER,
                    last_executed TIMESTAMP,
                    refinement_history TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Memory transitions - track movement between tiers
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_tier TEXT NOT NULL,
                    target_tier TEXT NOT NULL,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER,
                    transition_reason TEXT,
                    transition_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_working_expires ON working_memory(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_working_context ON working_memory(context_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_time ON episodic_memory(start_time)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_significance ON episodic_memory(significance_score)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_concept ON semantic_memory(concept_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_procedural_skill ON procedural_memory(skill_name)")

            conn.commit()

    # === WORKING MEMORY ===

    def add_to_working_memory(
        self,
        context_key: str,
        content: str,
        priority: int = 5,
        ttl_minutes: int = 60,
        entity_id: Optional[int] = None
    ) -> int:
        """Add item to working memory with TTL."""
        with sqlite3.connect(self.db_path) as conn:
            expires_at = (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat()
            cursor = conn.execute("""
                INSERT INTO working_memory
                (entity_id, context_key, content, priority, ttl_minutes, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (entity_id, context_key, content, priority, ttl_minutes, expires_at))
            conn.commit()
            return cursor.lastrowid

    def get_working_memory(self, context_key: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get items from working memory, optionally filtered by context."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Clean expired items first
            conn.execute("DELETE FROM working_memory WHERE expires_at < ?", (datetime.now().isoformat(),))

            if context_key:
                cursor = conn.execute("""
                    SELECT * FROM working_memory
                    WHERE context_key = ?
                    ORDER BY priority DESC, created_at DESC
                    LIMIT ?
                """, (context_key, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM working_memory
                    ORDER BY priority DESC, created_at DESC
                    LIMIT ?
                """, (limit,))

            # Update access counts
            items = [dict(row) for row in cursor.fetchall()]
            for item in items:
                conn.execute("""
                    UPDATE working_memory
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), item['id']))

            conn.commit()
            return items

    # === EPISODIC MEMORY ===

    def add_episode(
        self,
        event_type: str,
        episode_data: Dict,
        significance_score: float = 0.5,
        emotional_valence: Optional[float] = None,
        tags: List[str] = None,
        entity_id: Optional[int] = None
    ) -> int:
        """Add an episode to episodic memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO episodic_memory
                (entity_id, event_type, episode_data, start_time, significance_score, emotional_valence, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                event_type,
                json.dumps(episode_data),
                datetime.now().isoformat(),
                significance_score,
                emotional_valence,
                json.dumps(tags or [])
            ))
            conn.commit()
            return cursor.lastrowid

    def get_episodes(
        self,
        event_type: Optional[str] = None,
        min_significance: float = 0.0,
        limit: int = 50
    ) -> List[Dict]:
        """Get episodes, optionally filtered."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM episodic_memory
                WHERE significance_score >= ?
            """
            params = [min_significance]

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY significance_score DESC, start_time DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            episodes = []
            for row in cursor.fetchall():
                episode = dict(row)
                episode['episode_data'] = json.loads(episode['episode_data'])
                episode['tags'] = json.loads(episode['tags'] or '[]')
                episodes.append(episode)

            return episodes

    # === SEMANTIC MEMORY ===

    def add_concept(
        self,
        concept_name: str,
        concept_type: str,
        definition: str,
        related_concepts: List[str] = None,
        confidence_score: float = 0.5
    ) -> int:
        """Add or update a concept in semantic memory."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO semantic_memory
                    (concept_name, concept_type, definition, related_concepts, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    concept_name,
                    concept_type,
                    definition,
                    json.dumps(related_concepts or []),
                    confidence_score
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Update existing concept
                conn.execute("""
                    UPDATE semantic_memory
                    SET definition = ?,
                        related_concepts = ?,
                        confidence_score = ?,
                        updated_at = ?
                    WHERE concept_name = ?
                """, (
                    definition,
                    json.dumps(related_concepts or []),
                    confidence_score,
                    datetime.now().isoformat(),
                    concept_name
                ))
                conn.commit()
                cursor = conn.execute("SELECT id FROM semantic_memory WHERE concept_name = ?", (concept_name,))
                return cursor.fetchone()[0]

    def get_concepts(
        self,
        concept_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50
    ) -> List[Dict]:
        """Get concepts from semantic memory."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM semantic_memory WHERE confidence_score >= ?"
            params = [min_confidence]

            if concept_type:
                query += " AND concept_type = ?"
                params.append(concept_type)

            query += " ORDER BY confidence_score DESC, updated_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            concepts = []
            for row in cursor.fetchall():
                concept = dict(row)
                concept['related_concepts'] = json.loads(concept['related_concepts'] or '[]')
                concepts.append(concept)

            return concepts

    # === PROCEDURAL MEMORY ===

    def add_skill(
        self,
        skill_name: str,
        skill_category: str,
        procedure_steps: List[str],
        preconditions: List[str] = None,
        success_criteria: List[str] = None
    ) -> int:
        """Add or update a skill in procedural memory."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                cursor = conn.execute("""
                    INSERT INTO procedural_memory
                    (skill_name, skill_category, procedure_steps, preconditions, success_criteria)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    skill_name,
                    skill_category,
                    json.dumps(procedure_steps),
                    json.dumps(preconditions or []),
                    json.dumps(success_criteria or [])
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Update existing skill
                conn.execute("""
                    UPDATE procedural_memory
                    SET procedure_steps = ?,
                        preconditions = ?,
                        success_criteria = ?,
                        updated_at = ?
                    WHERE skill_name = ?
                """, (
                    json.dumps(procedure_steps),
                    json.dumps(preconditions or []),
                    json.dumps(success_criteria or []),
                    datetime.now().isoformat(),
                    skill_name
                ))
                conn.commit()
                cursor = conn.execute("SELECT id FROM procedural_memory WHERE skill_name = ?", (skill_name,))
                return cursor.fetchone()[0]

    def record_skill_execution(
        self,
        skill_name: str,
        success: bool,
        execution_time_ms: int
    ):
        """Record skill execution for learning."""
        with sqlite3.connect(self.db_path) as conn:
            # Get current stats
            cursor = conn.execute("""
                SELECT execution_count, success_rate, avg_execution_time_ms
                FROM procedural_memory
                WHERE skill_name = ?
            """, (skill_name,))

            row = cursor.fetchone()
            if not row:
                logger.warning(f"Skill '{skill_name}' not found for execution recording")
                return

            exec_count, success_rate, avg_time = row

            # Calculate new stats
            new_count = exec_count + 1
            new_success_rate = ((success_rate * exec_count) + (1.0 if success else 0.0)) / new_count

            if avg_time:
                new_avg_time = int((avg_time * exec_count + execution_time_ms) / new_count)
            else:
                new_avg_time = execution_time_ms

            # Update
            conn.execute("""
                UPDATE procedural_memory
                SET execution_count = ?,
                    success_rate = ?,
                    avg_execution_time_ms = ?,
                    last_executed = ?,
                    updated_at = ?
                WHERE skill_name = ?
            """, (
                new_count,
                new_success_rate,
                new_avg_time,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                skill_name
            ))
            conn.commit()

    def get_skills(
        self,
        skill_category: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50
    ) -> List[Dict]:
        """Get skills from procedural memory."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM procedural_memory WHERE success_rate >= ?"
            params = [min_success_rate]

            if skill_category:
                query += " AND skill_category = ?"
                params.append(skill_category)

            query += " ORDER BY success_rate DESC, execution_count DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            skills = []
            for row in cursor.fetchall():
                skill = dict(row)
                skill['procedure_steps'] = json.loads(skill['procedure_steps'])
                skill['preconditions'] = json.loads(skill['preconditions'] or '[]')
                skill['success_criteria'] = json.loads(skill['success_criteria'] or '[]')
                skills.append(skill)

            return skills

    # === AUTONOMOUS CURATION ===

    async def autonomous_memory_curation(self) -> Dict:
        """
        Autonomous memory curation across tiers.

        Promotions:
        - Working → Episodic: High-access items become episodes
        - Episodic → Semantic: Patterns become concepts
        - Episodic → Procedural: Repeated actions become skills
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = {
                "promoted_to_episodic": 0,
                "promoted_to_semantic": 0,
                "promoted_to_procedural": 0,
                "expired_working": 0
            }

            # 1. Clean expired working memory
            cursor = conn.execute("DELETE FROM working_memory WHERE expires_at < ?", (datetime.now().isoformat(),))
            stats["expired_working"] = cursor.rowcount

            # 2. Promote high-access working memory to episodic
            cursor = conn.execute("""
                SELECT * FROM working_memory
                WHERE access_count >= 5 AND promoted_to IS NULL
            """)
            conn.row_factory = sqlite3.Row

            for row in cursor.fetchall():
                # Create episode from working memory
                episode_id = self.add_episode(
                    event_type="promoted_from_working",
                    episode_data={"content": row['content'], "context": row['context_key']},
                    significance_score=min(row['access_count'] / 10.0, 1.0),
                    entity_id=row['entity_id']
                )

                # Mark as promoted
                conn.execute("UPDATE working_memory SET promoted_to = ? WHERE id = ?", (f"episodic:{episode_id}", row['id']))
                stats["promoted_to_episodic"] += 1

            # 3. Consolidate high-significance episodes into concepts
            cursor = conn.execute("""
                SELECT event_type, episode_data, significance_score, id
                FROM episodic_memory
                WHERE significance_score >= 0.8 AND consolidated_to_semantic = 0
                ORDER BY significance_score DESC
                LIMIT 20
            """)

            episode_groups = defaultdict(list)
            for row in cursor.fetchall():
                episode_groups[row[0]].append(row)

            for event_type, episodes in episode_groups.items():
                if len(episodes) >= 3:  # Need pattern of 3+ episodes
                    concept_id = self.add_concept(
                        concept_name=f"pattern_{event_type}",
                        concept_type="learned_pattern",
                        definition=f"Learned pattern from {len(episodes)} high-significance episodes",
                        confidence_score=sum(e[2] for e in episodes) / len(episodes)
                    )

                    # Mark episodes as consolidated
                    for episode in episodes:
                        conn.execute("UPDATE episodic_memory SET consolidated_to_semantic = 1 WHERE id = ?", (episode[3],))

                    stats["promoted_to_semantic"] += 1

            conn.commit()

            return stats

    async def analyze_memory_usage_patterns(self) -> Dict:
        """Analyze memory usage across all tiers."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            analysis = {
                "working_memory": {},
                "episodic_memory": {},
                "semantic_memory": {},
                "procedural_memory": {},
                "recommendations": []
            }

            # Working memory stats
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(access_count) as avg_access,
                    SUM(CASE WHEN expires_at < datetime('now') THEN 1 ELSE 0 END) as expired
                FROM working_memory
            """)
            row = cursor.fetchone()
            analysis["working_memory"] = dict(row)

            # Episodic memory stats
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(significance_score) as avg_significance,
                    COUNT(DISTINCT event_type) as unique_event_types,
                    SUM(consolidated_to_semantic) as consolidated
                FROM episodic_memory
            """)
            row = cursor.fetchone()
            analysis["episodic_memory"] = dict(row)

            # Semantic memory stats
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT concept_type) as unique_types,
                    AVG(confidence_score) as avg_confidence
                FROM semantic_memory
            """)
            row = cursor.fetchone()
            analysis["semantic_memory"] = dict(row)

            # Procedural memory stats
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(success_rate) as avg_success_rate,
                    AVG(execution_count) as avg_executions,
                    COUNT(DISTINCT skill_category) as unique_categories
                FROM procedural_memory
            """)
            row = cursor.fetchone()
            analysis["procedural_memory"] = dict(row)

            # Generate recommendations
            if analysis["working_memory"]["expired"] > 10:
                analysis["recommendations"].append("High number of expired working memory items - consider running cleanup")

            if analysis["episodic_memory"]["total"] > 1000:
                analysis["recommendations"].append("Large episodic memory - consider consolidating to semantic")

            if analysis["procedural_memory"]["avg_success_rate"] and analysis["procedural_memory"]["avg_success_rate"] < 0.5:
                analysis["recommendations"].append("Low average skill success rate - review and refine procedures")

            return analysis
