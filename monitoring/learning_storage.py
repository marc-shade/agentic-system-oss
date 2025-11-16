#!/usr/bin/env python3
"""
Learning Storage Engine for Deep Learning Cycle
Week 5 Phase 6: Long-term Knowledge Persistence

This module unifies learnings from all phases, builds knowledge graphs,
and enables semantic search over accumulated knowledge.
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
LEARNING_DB = Path("/mnt/agentic-system/databases/learning_storage.db")

# Source databases from previous phases
PATTERNS_DB = Path("/mnt/agentic-system/databases/patterns.db")
OPTIMIZATIONS_DB = Path("/mnt/agentic-system/databases/optimizations.db")
SKILL_ENHANCEMENTS_DB = Path("/mnt/agentic-system/databases/skill_enhancements.db")
AGENT_REFINEMENTS_DB = Path("/mnt/agentic-system/databases/agent_refinements.db")
CONFIG_TUNING_DB = Path("/mnt/agentic-system/databases/config_tuning.db")

class EntityType(Enum):
    """Types of learning entities"""
    PATTERN = "pattern"
    OPTIMIZATION = "optimization"
    SKILL_ENHANCEMENT = "skill_enhancement"
    AGENT_REFINEMENT = "agent_refinement"
    CONFIG_TUNING = "config_tuning"

class RelationshipType(Enum):
    """Types of relationships between learnings"""
    CAUSES = "causes"              # Entity A causes need for entity B
    IMPROVES = "improves"          # Entity A improves entity B
    REQUIRES = "requires"          # Entity A requires entity B
    CONFLICTS = "conflicts"        # Entity A conflicts with entity B
    SIMILAR = "similar"            # Entity A similar to entity B
    DERIVED_FROM = "derived_from"  # Entity A derived from entity B

class InsightType(Enum):
    """Types of meta-knowledge insights"""
    TREND = "trend"                    # Recurring pattern over time
    CORRELATION = "correlation"        # Two things happen together
    ANTI_PATTERN = "anti_pattern"      # Pattern that should be avoided
    BEST_PRACTICE = "best_practice"    # Pattern that works well
    EFFICIENCY_GAIN = "efficiency_gain"  # Improvement in efficiency

@dataclass
class LearningEntity:
    """Represents a learning from any phase"""
    entity_id: str
    entity_type: EntityType
    source_phase: int
    source_id: str
    title: str
    description: str
    confidence: float
    effectiveness: float
    created_at: datetime
    applied_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class LearningRelationship:
    """Represents a relationship between learnings"""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    strength: float
    discovered_at: datetime
    evidence: str

@dataclass
class LearningInsight:
    """Represents meta-knowledge discovered"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    supporting_entities: List[str]
    confidence: float
    discovered_at: datetime

class LearningStorageDatabase:
    """Manages unified learning storage"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize learning storage schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Learning entities - unified knowledge from all phases
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_entities (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                source_phase INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                effectiveness REAL DEFAULT 0.0,
                created_at TIMESTAMP NOT NULL,
                applied_at TIMESTAMP,
                metadata TEXT NOT NULL
            )
        """)

        # Learning relationships - knowledge graph edges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_relationships (
                relationship_id TEXT PRIMARY KEY,
                source_entity_id TEXT NOT NULL,
                target_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL NOT NULL,
                discovered_at TIMESTAMP NOT NULL,
                evidence TEXT NOT NULL,
                FOREIGN KEY (source_entity_id) REFERENCES learning_entities(entity_id),
                FOREIGN KEY (target_entity_id) REFERENCES learning_entities(entity_id)
            )
        """)

        # Learning insights - meta-knowledge
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                insight_id TEXT PRIMARY KEY,
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                supporting_entities TEXT NOT NULL,
                confidence REAL NOT NULL,
                discovered_at TIMESTAMP NOT NULL
            )
        """)

        # Knowledge search index
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_search_index (
                index_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                keywords TEXT NOT NULL,
                last_indexed TIMESTAMP NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES learning_entities(entity_id)
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_type ON learning_entities(entity_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_phase ON learning_entities(source_phase)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship_source ON learning_relationships(source_entity_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_relationship_target ON learning_relationships(target_entity_id)
        """)

        conn.commit()
        conn.close()

    def store_entity(self, entity: LearningEntity):
        """Store a learning entity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO learning_entities
            (entity_id, entity_type, source_phase, source_id, title, description,
             confidence, effectiveness, created_at, applied_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity.entity_id, entity.entity_type.value, entity.source_phase,
            entity.source_id, entity.title, entity.description,
            entity.confidence, entity.effectiveness,
            entity.created_at.isoformat(),
            entity.applied_at.isoformat() if entity.applied_at else None,
            json.dumps(entity.metadata)
        ))

        conn.commit()
        conn.close()

    def store_relationship(self, relationship: LearningRelationship):
        """Store a learning relationship"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO learning_relationships
            (relationship_id, source_entity_id, target_entity_id, relationship_type,
             strength, discovered_at, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            relationship.relationship_id, relationship.source_entity_id,
            relationship.target_entity_id, relationship.relationship_type.value,
            relationship.strength, relationship.discovered_at.isoformat(),
            relationship.evidence
        ))

        conn.commit()
        conn.close()

    def store_insight(self, insight: LearningInsight):
        """Store a learning insight"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO learning_insights
            (insight_id, insight_type, title, description, supporting_entities,
             confidence, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            insight.insight_id, insight.insight_type.value, insight.title,
            insight.description, json.dumps(insight.supporting_entities),
            insight.confidence, insight.discovered_at.isoformat()
        ))

        conn.commit()
        conn.close()

    def get_entities_by_type(self, entity_type: EntityType) -> List[LearningEntity]:
        """Get all entities of a specific type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT entity_id, entity_type, source_phase, source_id, title, description,
                   confidence, effectiveness, created_at, applied_at, metadata
            FROM learning_entities
            WHERE entity_type = ?
            ORDER BY created_at DESC
        """, (entity_type.value,))

        rows = cursor.fetchall()
        conn.close()

        return [LearningEntity(
            entity_id=r[0], entity_type=EntityType(r[1]), source_phase=r[2],
            source_id=r[3], title=r[4], description=r[5],
            confidence=r[6], effectiveness=r[7],
            created_at=datetime.fromisoformat(r[8]),
            applied_at=datetime.fromisoformat(r[9]) if r[9] else None,
            metadata=json.loads(r[10])
        ) for r in rows]

    def get_related_entities(self, entity_id: str) -> List[Tuple[LearningEntity, RelationshipType, float]]:
        """Get entities related to a given entity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get outgoing relationships
        cursor.execute("""
            SELECT e.entity_id, e.entity_type, e.source_phase, e.source_id, e.title,
                   e.description, e.confidence, e.effectiveness, e.created_at, e.applied_at,
                   e.metadata, r.relationship_type, r.strength
            FROM learning_entities e
            JOIN learning_relationships r ON e.entity_id = r.target_entity_id
            WHERE r.source_entity_id = ?
            ORDER BY r.strength DESC
        """, (entity_id,))

        rows = cursor.fetchall()
        conn.close()

        return [(
            LearningEntity(
                entity_id=r[0], entity_type=EntityType(r[1]), source_phase=r[2],
                source_id=r[3], title=r[4], description=r[5],
                confidence=r[6], effectiveness=r[7],
                created_at=datetime.fromisoformat(r[8]),
                applied_at=datetime.fromisoformat(r[9]) if r[9] else None,
                metadata=json.loads(r[10])
            ),
            RelationshipType(r[11]),
            r[12]
        ) for r in rows]

    def search_knowledge(self, query: str, limit: int = 10) -> List[LearningEntity]:
        """Search knowledge base by keywords"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Simple keyword search (can be enhanced with semantic search)
        cursor.execute("""
            SELECT DISTINCT e.entity_id, e.entity_type, e.source_phase, e.source_id, e.title,
                   e.description, e.confidence, e.effectiveness, e.created_at, e.applied_at,
                   e.metadata
            FROM learning_entities e
            WHERE e.title LIKE ? OR e.description LIKE ?
            ORDER BY e.confidence DESC, e.effectiveness DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        rows = cursor.fetchall()
        conn.close()

        return [LearningEntity(
            entity_id=r[0], entity_type=EntityType(r[1]), source_phase=r[2],
            source_id=r[3], title=r[4], description=r[5],
            confidence=r[6], effectiveness=r[7],
            created_at=datetime.fromisoformat(r[8]),
            applied_at=datetime.fromisoformat(r[9]) if r[9] else None,
            metadata=json.loads(r[10])
        ) for r in rows]

class KnowledgeHarvester:
    """Harvests knowledge from all phase databases"""

    def __init__(self, storage_db: LearningStorageDatabase):
        self.storage_db = storage_db

    def harvest_patterns(self) -> int:
        """Harvest patterns from Phase 1"""
        if not PATTERNS_DB.exists():
            return 0

        conn = sqlite3.connect(PATTERNS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pattern_id, pattern_type, description, confidence,
                   detected_at, occurrences
            FROM patterns
            WHERE confidence >= 0.60
        """)

        rows = cursor.fetchall()
        conn.close()

        harvested = 0
        for r in rows:
            entity_id = hashlib.sha256(f"pattern_{r[0]}".encode()).hexdigest()[:16]
            entity = LearningEntity(
                entity_id=entity_id,
                entity_type=EntityType.PATTERN,
                source_phase=1,
                source_id=r[0],
                title=f"{r[1]}: {r[2][:50]}",  # Pattern type + truncated description
                description=r[2],
                confidence=r[3],
                effectiveness=min(r[5] / 10.0, 1.0),  # Normalize occurrences
                created_at=datetime.fromisoformat(r[4]),
                applied_at=None,
                metadata={"pattern_type": r[1], "occurrences": r[5]}
            )
            self.storage_db.store_entity(entity)
            harvested += 1

        return harvested

    def harvest_optimizations(self) -> int:
        """Harvest optimizations from Phase 2"""
        if not OPTIMIZATIONS_DB.exists():
            return 0

        conn = sqlite3.connect(OPTIMIZATIONS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT optimization_id, optimization_type, target_file, description,
                   confidence, status, created_at, applied_at
            FROM optimizations
            WHERE confidence >= 0.70
        """)

        rows = cursor.fetchall()
        conn.close()

        harvested = 0
        for r in rows:
            entity_id = hashlib.sha256(f"optimization_{r[0]}".encode()).hexdigest()[:16]
            entity = LearningEntity(
                entity_id=entity_id,
                entity_type=EntityType.OPTIMIZATION,
                source_phase=2,
                source_id=r[0],
                title=f"{r[1]}: {Path(r[2]).name}",
                description=r[3],
                confidence=r[4],
                effectiveness=0.75,  # Default effectiveness for applied optimizations
                created_at=datetime.fromisoformat(r[6]),
                applied_at=datetime.fromisoformat(r[7]) if r[7] else None,
                metadata={"optimization_type": r[1], "target_file": r[2]}
            )
            self.storage_db.store_entity(entity)
            harvested += 1

        return harvested

    def harvest_skill_enhancements(self) -> int:
        """Harvest skill enhancements from Phase 3"""
        if not SKILL_ENHANCEMENTS_DB.exists():
            return 0

        conn = sqlite3.connect(SKILL_ENHANCEMENTS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT enhancement_id, skill_id, enhancement_type, description,
                   confidence, status, created_at, applied_at, effectiveness
            FROM skill_enhancements
            WHERE confidence >= 0.65
        """)

        rows = cursor.fetchall()
        conn.close()

        harvested = 0
        for r in rows:
            entity_id = hashlib.sha256(f"skill_enhancement_{r[0]}".encode()).hexdigest()[:16]
            entity = LearningEntity(
                entity_id=entity_id,
                entity_type=EntityType.SKILL_ENHANCEMENT,
                source_phase=3,
                source_id=r[0],
                title=f"Skill Enhancement: {r[2]}",
                description=r[3],
                confidence=r[4],
                effectiveness=r[8],
                created_at=datetime.fromisoformat(r[6]),
                applied_at=datetime.fromisoformat(r[7]) if r[7] else None,
                metadata={"skill_id": r[1], "enhancement_type": r[2]}
            )
            self.storage_db.store_entity(entity)
            harvested += 1

        return harvested

    def harvest_agent_refinements(self) -> int:
        """Harvest agent refinements from Phase 4"""
        if not AGENT_REFINEMENTS_DB.exists():
            return 0

        conn = sqlite3.connect(AGENT_REFINEMENTS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT refinement_id, agent_id, refinement_type, description,
                   confidence, status, created_at, applied_at, effectiveness
            FROM agent_refinements
            WHERE confidence >= 0.65
        """)

        rows = cursor.fetchall()
        conn.close()

        harvested = 0
        for r in rows:
            entity_id = hashlib.sha256(f"agent_refinement_{r[0]}".encode()).hexdigest()[:16]
            entity = LearningEntity(
                entity_id=entity_id,
                entity_type=EntityType.AGENT_REFINEMENT,
                source_phase=4,
                source_id=r[0],
                title=f"Agent Refinement: {r[2]}",
                description=r[3],
                confidence=r[4],
                effectiveness=r[8],
                created_at=datetime.fromisoformat(r[6]),
                applied_at=datetime.fromisoformat(r[7]) if r[7] else None,
                metadata={"agent_id": r[1], "refinement_type": r[2]}
            )
            self.storage_db.store_entity(entity)
            harvested += 1

        return harvested

    def harvest_config_tunings(self) -> int:
        """Harvest config tunings from Phase 5"""
        if not CONFIG_TUNING_DB.exists():
            return 0

        conn = sqlite3.connect(CONFIG_TUNING_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tuning_id, file_id, tuning_type, parameter_path, description,
                   confidence, status, created_at, applied_at, effectiveness
            FROM config_tuning
            WHERE confidence >= 0.60
        """)

        rows = cursor.fetchall()
        conn.close()

        harvested = 0
        for r in rows:
            entity_id = hashlib.sha256(f"config_tuning_{r[0]}".encode()).hexdigest()[:16]
            entity = LearningEntity(
                entity_id=entity_id,
                entity_type=EntityType.CONFIG_TUNING,
                source_phase=5,
                source_id=r[0],
                title=f"Config Tuning: {r[3]}",
                description=r[4],
                confidence=r[5],
                effectiveness=r[9],
                created_at=datetime.fromisoformat(r[7]),
                applied_at=datetime.fromisoformat(r[8]) if r[8] else None,
                metadata={"file_id": r[1], "tuning_type": r[2], "parameter_path": r[3]}
            )
            self.storage_db.store_entity(entity)
            harvested += 1

        return harvested

    def harvest_all(self) -> Dict[str, int]:
        """Harvest knowledge from all phases"""
        return {
            "patterns": self.harvest_patterns(),
            "optimizations": self.harvest_optimizations(),
            "skill_enhancements": self.harvest_skill_enhancements(),
            "agent_refinements": self.harvest_agent_refinements(),
            "config_tunings": self.harvest_config_tunings()
        }

class RelationshipDiscoverer:
    """Discovers relationships between learnings"""

    def __init__(self, storage_db: LearningStorageDatabase):
        self.storage_db = storage_db

    def discover_causal_relationships(self) -> int:
        """Discover causal relationships (patterns cause optimizations)"""
        patterns = self.storage_db.get_entities_by_type(EntityType.PATTERN)
        optimizations = self.storage_db.get_entities_by_type(EntityType.OPTIMIZATION)

        discovered = 0
        for pattern in patterns:
            for optimization in optimizations:
                # Check if pattern description mentions optimization type
                if pattern.description.lower() in optimization.description.lower():
                    relationship_id = hashlib.sha256(
                        f"{pattern.entity_id}_{optimization.entity_id}_causes".encode()
                    ).hexdigest()[:16]

                    relationship = LearningRelationship(
                        relationship_id=relationship_id,
                        source_entity_id=pattern.entity_id,
                        target_entity_id=optimization.entity_id,
                        relationship_type=RelationshipType.CAUSES,
                        strength=0.7,
                        discovered_at=datetime.now(),
                        evidence=f"Pattern '{pattern.title}' led to optimization '{optimization.title}'"
                    )
                    self.storage_db.store_relationship(relationship)
                    discovered += 1

        return discovered

    def discover_improvement_relationships(self) -> int:
        """Discover improvement relationships (optimizations improve skills)"""
        optimizations = self.storage_db.get_entities_by_type(EntityType.OPTIMIZATION)
        skills = self.storage_db.get_entities_by_type(EntityType.SKILL_ENHANCEMENT)

        discovered = 0
        for opt in optimizations:
            for skill in skills:
                # Check if they're related by timing (optimization before skill enhancement)
                if opt.applied_at and skill.created_at and opt.applied_at < skill.created_at:
                    time_diff = (skill.created_at - opt.applied_at).total_seconds()
                    if time_diff < 86400:  # Within 24 hours
                        relationship_id = hashlib.sha256(
                            f"{opt.entity_id}_{skill.entity_id}_improves".encode()
                        ).hexdigest()[:16]

                        relationship = LearningRelationship(
                            relationship_id=relationship_id,
                            source_entity_id=opt.entity_id,
                            target_entity_id=skill.entity_id,
                            relationship_type=RelationshipType.IMPROVES,
                            strength=0.6,
                            discovered_at=datetime.now(),
                            evidence=f"Optimization '{opt.title}' followed by skill enhancement '{skill.title}'"
                        )
                        self.storage_db.store_relationship(relationship)
                        discovered += 1

        return discovered

class InsightGenerator:
    """Generates meta-knowledge insights"""

    def __init__(self, storage_db: LearningStorageDatabase):
        self.storage_db = storage_db

    def generate_trend_insights(self) -> int:
        """Generate insights about trends"""
        # Analyze effectiveness trends across entity types
        insights_generated = 0

        for entity_type in EntityType:
            entities = self.storage_db.get_entities_by_type(entity_type)
            if len(entities) >= 5:
                avg_effectiveness = sum(e.effectiveness for e in entities) / len(entities)

                if avg_effectiveness > 0.7:
                    insight_id = hashlib.sha256(
                        f"trend_{entity_type.value}_high_effectiveness".encode()
                    ).hexdigest()[:16]

                    insight = LearningInsight(
                        insight_id=insight_id,
                        insight_type=InsightType.BEST_PRACTICE,
                        title=f"High Effectiveness in {entity_type.value.replace('_', ' ').title()}",
                        description=f"{entity_type.value.replace('_', ' ').title()} showing {avg_effectiveness:.0%} average effectiveness",
                        supporting_entities=[e.entity_id for e in entities],
                        confidence=0.8,
                        discovered_at=datetime.now()
                    )
                    self.storage_db.store_insight(insight)
                    insights_generated += 1

        return insights_generated

def main():
    """Main learning storage runner"""
    print("="*60)
    print("Learning Storage Engine - Week 5 Phase 6")
    print("="*60)
    print()

    db = LearningStorageDatabase(LEARNING_DB)
    print(f"✓ Learning database initialized: {LEARNING_DB}")

    harvester = KnowledgeHarvester(db)
    print(f"✓ Knowledge harvester initialized")
    print()

    print("Harvesting knowledge from all phases...")
    harvested = harvester.harvest_all()
    print(f"  Phase 1 (Patterns): {harvested['patterns']} entities")
    print(f"  Phase 2 (Optimizations): {harvested['optimizations']} entities")
    print(f"  Phase 3 (Skills): {harvested['skill_enhancements']} entities")
    print(f"  Phase 4 (Agents): {harvested['agent_refinements']} entities")
    print(f"  Phase 5 (Configs): {harvested['config_tunings']} entities")
    total_harvested = sum(harvested.values())
    print(f"Total: {total_harvested} entities harvested")
    print()

    discoverer = RelationshipDiscoverer(db)
    print("Discovering relationships...")
    causal = discoverer.discover_causal_relationships()
    improvement = discoverer.discover_improvement_relationships()
    print(f"  Causal relationships: {causal}")
    print(f"  Improvement relationships: {improvement}")
    print(f"Total: {causal + improvement} relationships discovered")
    print()

    generator = InsightGenerator(db)
    print("Generating insights...")
    trends = generator.generate_trend_insights()
    print(f"  Trend insights: {trends}")
    print(f"Total: {trends} insights generated")
    print()

    print("="*60)
    print("LEARNING STORAGE COMPLETE")
    print("="*60)
    print(f"Entities stored: {total_harvested}")
    print(f"Relationships discovered: {causal + improvement}")
    print(f"Insights generated: {trends}")
    print(f"Database: {LEARNING_DB}")
    print()

if __name__ == "__main__":
    main()
