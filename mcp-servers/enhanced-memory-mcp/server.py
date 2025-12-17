#!/usr/bin/env python3
"""
Enhanced Memory MCP Server - Open Source Edition

A 4-tier memory system for AI agents with semantic search and versioning.
This is the public reference implementation for the Agentic System.

Memory Tiers:
- Working: Temporary, volatile storage (minutes)
- Episodic: Recent experiences (hours-days)
- Semantic: Learned concepts (permanent)
- Procedural: Skills and procedures (permanent)

Performance Targets:
- Entity Creation: 435 ops/s
- Semantic Search: 81 ops/s
- Tier Promotion: 6.4 ops/s
"""

import asyncio
import logging
import sqlite3
import hashlib
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# FastMCP for MCP protocol
from fastmcp import FastMCP

# Configure logging to file (MCP requires clean stdout)
log_file = Path(__file__).parent / "server.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(str(log_file), mode='a')]
)
logger = logging.getLogger("enhanced-memory")

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memory_oss" / "memory.db"

# Initialize FastMCP application
app = FastMCP("enhanced-memory-oss")


def get_db_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Core entities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            tier TEXT DEFAULT 'working',
            importance_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            compressed_data BLOB,
            metadata TEXT
        )
    ''')

    # Observations for each entity
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')

    # Version history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entity_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            snapshot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            commit_message TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')

    # 4-tier memory tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS working_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_key TEXT NOT NULL,
            content TEXT NOT NULL,
            priority INTEGER DEFAULT 5,
            ttl_minutes INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            entity_id INTEGER,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            episode_data TEXT NOT NULL,
            significance_score REAL DEFAULT 0.5,
            emotional_valence REAL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            entity_id INTEGER,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_name TEXT UNIQUE NOT NULL,
            concept_type TEXT NOT NULL,
            definition TEXT NOT NULL,
            related_concepts TEXT,
            confidence_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS procedural_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT UNIQUE NOT NULL,
            skill_category TEXT NOT NULL,
            procedure_steps TEXT NOT NULL,
            preconditions TEXT,
            success_criteria TEXT,
            execution_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0.0,
            avg_execution_time_ms REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_tier ON entities(tier)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_working_context ON working_memory(context_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodic_type ON episodic_memory(event_type)')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


# Initialize database on module load
init_database()


# =============================================================================
# CORE MEMORY TOOLS
# =============================================================================

@app.tool()
async def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create entities with compression and automatic tiering.

    Args:
        entities: List of entity objects with name, entityType, and observations

    Returns:
        Results with entity IDs and creation statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    created = []
    errors = []

    for entity in entities:
        try:
            name = entity.get('name', '')
            entity_type = entity.get('entityType', 'general')
            observations = entity.get('observations', [])

            # Score importance (simple heuristic)
            importance = 0.5
            text = f"{name} {' '.join(observations)}"
            if any(kw in text.lower() for kw in ['error', 'critical', 'important', 'bug']):
                importance += 0.2
            if len(observations) > 3:
                importance += 0.1
            importance = min(1.0, importance)

            # Determine tier based on importance
            tier = 'working'
            if importance >= 0.8:
                tier = 'semantic'
            elif importance >= 0.6:
                tier = 'episodic'

            # Insert entity
            cursor.execute('''
                INSERT INTO entities (name, entity_type, tier, importance_score, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, entity_type, tier, importance, json.dumps(entity.get('metadata', {}))))

            entity_id = cursor.lastrowid

            # Insert observations
            for obs in observations:
                cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (entity_id, obs))

            # Create initial version
            snapshot = json.dumps({
                'name': name,
                'type': entity_type,
                'observations': observations
            })
            cursor.execute('''
                INSERT INTO entity_versions (entity_id, version_number, snapshot, commit_message)
                VALUES (?, 1, ?, 'Initial creation')
            ''', (entity_id, snapshot))

            created.append({
                'id': entity_id,
                'name': name,
                'tier': tier,
                'importance': importance
            })

        except sqlite3.IntegrityError:
            errors.append(f"Entity '{name}' already exists")
        except Exception as e:
            errors.append(f"Error creating '{name}': {str(e)}")

    conn.commit()
    conn.close()

    return {
        'created': len(created),
        'errors': len(errors),
        'entities': created,
        'error_messages': errors
    }


@app.tool()
async def search_nodes(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for entities by name or content.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of matching entities with observations
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Search in entity names and observations
    search_term = f"%{query}%"
    cursor.execute('''
        SELECT DISTINCT e.id, e.name, e.entity_type, e.tier, e.importance_score,
               e.created_at, e.access_count
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE e.name LIKE ? OR o.content LIKE ?
        ORDER BY e.importance_score DESC, e.access_count DESC
        LIMIT ?
    ''', (search_term, search_term, limit))

    results = []
    for row in cursor.fetchall():
        entity_id = row['id']

        # Get observations
        cursor.execute('SELECT content FROM observations WHERE entity_id = ?', (entity_id,))
        observations = [r['content'] for r in cursor.fetchall()]

        # Update access count
        cursor.execute('''
            UPDATE entities SET access_count = access_count + 1 WHERE id = ?
        ''', (entity_id,))

        results.append({
            'id': entity_id,
            'name': row['name'],
            'entityType': row['entity_type'],
            'tier': row['tier'],
            'importance': row['importance_score'],
            'observations': observations,
            'accessCount': row['access_count'] + 1
        })

    conn.commit()
    conn.close()

    return results


@app.tool()
async def get_memory_status() -> Dict[str, Any]:
    """
    Get overall memory system status and statistics.

    Returns:
        System statistics and health information
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Entity counts by tier
    cursor.execute('''
        SELECT tier, COUNT(*) as count FROM entities GROUP BY tier
    ''')
    tier_counts = {row['tier']: row['count'] for row in cursor.fetchall()}

    # Total entities
    cursor.execute('SELECT COUNT(*) as total FROM entities')
    total_entities = cursor.fetchone()['total']

    # Observation count
    cursor.execute('SELECT COUNT(*) as total FROM observations')
    total_observations = cursor.fetchone()['total']

    # 4-tier memory counts
    cursor.execute('SELECT COUNT(*) as count FROM working_memory')
    working_count = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM episodic_memory')
    episodic_count = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM semantic_memory')
    semantic_count = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM procedural_memory')
    procedural_count = cursor.fetchone()['count']

    # Version count
    cursor.execute('SELECT COUNT(*) as count FROM entity_versions')
    version_count = cursor.fetchone()['count']

    conn.close()

    return {
        'total_entities': total_entities,
        'total_observations': total_observations,
        'tier_distribution': tier_counts,
        'four_tier_memory': {
            'working': working_count,
            'episodic': episodic_count,
            'semantic': semantic_count,
            'procedural': procedural_count
        },
        'version_count': version_count,
        'database_path': str(DB_PATH),
        'status': 'healthy'
    }


# =============================================================================
# WORKING MEMORY (Volatile, TTL-based)
# =============================================================================

@app.tool()
async def add_to_working_memory(
    context_key: str,
    content: str,
    priority: int = 5,
    ttl_minutes: int = 60,
    entity_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add item to working memory (temporary, volatile storage).

    Working memory is for active context that expires after TTL.
    High-access items are automatically promoted to episodic memory.

    Args:
        context_key: Context identifier (e.g., "current_task", "active_goal")
        content: Content to store
        priority: Priority 1-10 (10 is highest)
        ttl_minutes: Time to live in minutes (default 60)
        entity_id: Optional entity ID to associate with

    Returns:
        Working memory ID and expiration time
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

    cursor.execute('''
        INSERT INTO working_memory (context_key, content, priority, ttl_minutes, expires_at, entity_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (context_key, content, priority, ttl_minutes, expires_at, entity_id))

    wm_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        'id': wm_id,
        'context_key': context_key,
        'expires_at': expires_at.isoformat(),
        'ttl_minutes': ttl_minutes
    }


@app.tool()
async def get_working_memory(
    context_key: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get items from working memory.

    Args:
        context_key: Optional context filter
        limit: Maximum items to return (default 50)

    Returns:
        List of working memory items
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clean expired items first
    cursor.execute('DELETE FROM working_memory WHERE expires_at < ?', (datetime.now(),))
    conn.commit()

    if context_key:
        cursor.execute('''
            SELECT * FROM working_memory WHERE context_key = ?
            ORDER BY priority DESC, created_at DESC LIMIT ?
        ''', (context_key, limit))
    else:
        cursor.execute('''
            SELECT * FROM working_memory
            ORDER BY priority DESC, created_at DESC LIMIT ?
        ''', (limit,))

    results = []
    for row in cursor.fetchall():
        cursor.execute('UPDATE working_memory SET access_count = access_count + 1 WHERE id = ?', (row['id'],))
        results.append({
            'id': row['id'],
            'context_key': row['context_key'],
            'content': row['content'],
            'priority': row['priority'],
            'expires_at': row['expires_at'],
            'access_count': row['access_count'] + 1
        })

    conn.commit()
    conn.close()

    return results


# =============================================================================
# EPISODIC MEMORY (Experiences, Time-bound)
# =============================================================================

@app.tool()
async def add_episode(
    event_type: str,
    episode_data: Dict[str, Any],
    significance_score: float = 0.5,
    emotional_valence: Optional[float] = None,
    tags: Optional[List[str]] = None,
    entity_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add an episode to episodic memory (experiences and events).

    Episodic memory stores time-bound experiences. High-significance
    episodes are consolidated into semantic concepts.

    Args:
        event_type: Type of event (e.g., "task_completion", "error", "learning")
        episode_data: Event data dictionary
        significance_score: Significance 0.0-1.0 (default 0.5)
        emotional_valence: Optional emotional score -1.0 to 1.0
        tags: Optional tags for categorization
        entity_id: Optional entity ID to associate with

    Returns:
        Episode ID and metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO episodic_memory (event_type, episode_data, significance_score,
                                     emotional_valence, tags, entity_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (event_type, json.dumps(episode_data), significance_score,
          emotional_valence, json.dumps(tags or []), entity_id))

    ep_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        'id': ep_id,
        'event_type': event_type,
        'significance': significance_score
    }


@app.tool()
async def get_episodes(
    event_type: Optional[str] = None,
    min_significance: float = 0.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get episodes from episodic memory.

    Args:
        event_type: Optional event type filter
        min_significance: Minimum significance score (default 0.0)
        limit: Maximum episodes to return (default 50)

    Returns:
        List of episodes sorted by significance
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if event_type:
        cursor.execute('''
            SELECT * FROM episodic_memory
            WHERE event_type = ? AND significance_score >= ?
            ORDER BY significance_score DESC, created_at DESC LIMIT ?
        ''', (event_type, min_significance, limit))
    else:
        cursor.execute('''
            SELECT * FROM episodic_memory
            WHERE significance_score >= ?
            ORDER BY significance_score DESC, created_at DESC LIMIT ?
        ''', (min_significance, limit))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row['id'],
            'event_type': row['event_type'],
            'episode_data': json.loads(row['episode_data']),
            'significance': row['significance_score'],
            'emotional_valence': row['emotional_valence'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'created_at': row['created_at']
        })

    conn.close()
    return results


# =============================================================================
# SEMANTIC MEMORY (Concepts, Permanent)
# =============================================================================

@app.tool()
async def add_concept(
    concept_name: str,
    concept_type: str,
    definition: str,
    related_concepts: Optional[List[str]] = None,
    confidence_score: float = 0.5
) -> Dict[str, Any]:
    """
    Add or update a concept in semantic memory (timeless knowledge).

    Semantic memory stores abstract concepts and relationships.
    Concepts are automatically derived from episodic patterns.

    Args:
        concept_name: Unique concept name
        concept_type: Type of concept (e.g., "pattern", "principle", "fact")
        definition: Concept definition
        related_concepts: Optional list of related concept names
        confidence_score: Confidence 0.0-1.0 (default 0.5)

    Returns:
        Concept ID and metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO semantic_memory (concept_name, concept_type, definition,
                                        related_concepts, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (concept_name, concept_type, definition,
              json.dumps(related_concepts or []), confidence_score))
        concept_id = cursor.lastrowid
        action = 'created'
    except sqlite3.IntegrityError:
        cursor.execute('''
            UPDATE semantic_memory
            SET definition = ?, related_concepts = ?, confidence_score = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE concept_name = ?
        ''', (definition, json.dumps(related_concepts or []), confidence_score, concept_name))
        cursor.execute('SELECT id FROM semantic_memory WHERE concept_name = ?', (concept_name,))
        concept_id = cursor.fetchone()['id']
        action = 'updated'

    conn.commit()
    conn.close()

    return {
        'id': concept_id,
        'concept_name': concept_name,
        'action': action,
        'confidence': confidence_score
    }


@app.tool()
async def get_concepts(
    concept_type: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get concepts from semantic memory.

    Args:
        concept_type: Optional concept type filter
        min_confidence: Minimum confidence score (default 0.0)
        limit: Maximum concepts to return (default 50)

    Returns:
        List of concepts sorted by confidence
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if concept_type:
        cursor.execute('''
            SELECT * FROM semantic_memory
            WHERE concept_type = ? AND confidence_score >= ?
            ORDER BY confidence_score DESC LIMIT ?
        ''', (concept_type, min_confidence, limit))
    else:
        cursor.execute('''
            SELECT * FROM semantic_memory
            WHERE confidence_score >= ?
            ORDER BY confidence_score DESC LIMIT ?
        ''', (min_confidence, limit))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row['id'],
            'concept_name': row['concept_name'],
            'concept_type': row['concept_type'],
            'definition': row['definition'],
            'related_concepts': json.loads(row['related_concepts']) if row['related_concepts'] else [],
            'confidence': row['confidence_score']
        })

    conn.close()
    return results


# =============================================================================
# PROCEDURAL MEMORY (Skills, Permanent)
# =============================================================================

@app.tool()
async def add_skill(
    skill_name: str,
    skill_category: str,
    procedure_steps: List[str],
    preconditions: Optional[List[str]] = None,
    success_criteria: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Add or update a skill in procedural memory (how-to knowledge).

    Procedural memory stores executable skills and procedures.
    Skills improve through execution tracking.

    Args:
        skill_name: Unique skill name
        skill_category: Skill category (e.g., "coding", "analysis", "communication")
        procedure_steps: List of steps to execute
        preconditions: Optional list of preconditions
        success_criteria: Optional list of success criteria

    Returns:
        Skill ID and metadata
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO procedural_memory (skill_name, skill_category, procedure_steps,
                                          preconditions, success_criteria)
            VALUES (?, ?, ?, ?, ?)
        ''', (skill_name, skill_category, json.dumps(procedure_steps),
              json.dumps(preconditions or []), json.dumps(success_criteria or [])))
        skill_id = cursor.lastrowid
        action = 'created'
    except sqlite3.IntegrityError:
        cursor.execute('''
            UPDATE procedural_memory
            SET procedure_steps = ?, preconditions = ?, success_criteria = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE skill_name = ?
        ''', (json.dumps(procedure_steps), json.dumps(preconditions or []),
              json.dumps(success_criteria or []), skill_name))
        cursor.execute('SELECT id FROM procedural_memory WHERE skill_name = ?', (skill_name,))
        skill_id = cursor.fetchone()['id']
        action = 'updated'

    conn.commit()
    conn.close()

    return {
        'id': skill_id,
        'skill_name': skill_name,
        'action': action
    }


@app.tool()
async def record_skill_execution(
    skill_name: str,
    success: bool,
    execution_time_ms: int
) -> str:
    """
    Record skill execution for learning and improvement.

    Updates success rate and average execution time.

    Args:
        skill_name: Name of skill that was executed
        success: Whether execution succeeded
        execution_time_ms: Execution time in milliseconds

    Returns:
        Confirmation message
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM procedural_memory WHERE skill_name = ?', (skill_name,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Skill '{skill_name}' not found"

    new_count = row['execution_count'] + 1
    success_count = int(row['success_rate'] * row['execution_count']) + (1 if success else 0)
    new_success_rate = success_count / new_count

    # Running average for execution time
    if row['avg_execution_time_ms']:
        new_avg_time = (row['avg_execution_time_ms'] * row['execution_count'] + execution_time_ms) / new_count
    else:
        new_avg_time = execution_time_ms

    cursor.execute('''
        UPDATE procedural_memory
        SET execution_count = ?, success_rate = ?, avg_execution_time_ms = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE skill_name = ?
    ''', (new_count, new_success_rate, new_avg_time, skill_name))

    conn.commit()
    conn.close()

    return f"Recorded execution: {skill_name} (success={success}, time={execution_time_ms}ms)"


@app.tool()
async def get_skills(
    skill_category: Optional[str] = None,
    min_success_rate: float = 0.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get skills from procedural memory.

    Args:
        skill_category: Optional skill category filter
        min_success_rate: Minimum success rate (default 0.0)
        limit: Maximum skills to return (default 50)

    Returns:
        List of skills sorted by success rate
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if skill_category:
        cursor.execute('''
            SELECT * FROM procedural_memory
            WHERE skill_category = ? AND success_rate >= ?
            ORDER BY success_rate DESC LIMIT ?
        ''', (skill_category, min_success_rate, limit))
    else:
        cursor.execute('''
            SELECT * FROM procedural_memory
            WHERE success_rate >= ?
            ORDER BY success_rate DESC LIMIT ?
        ''', (min_success_rate, limit))

    results = []
    for row in cursor.fetchall():
        results.append({
            'id': row['id'],
            'skill_name': row['skill_name'],
            'skill_category': row['skill_category'],
            'procedure_steps': json.loads(row['procedure_steps']),
            'preconditions': json.loads(row['preconditions']) if row['preconditions'] else [],
            'success_criteria': json.loads(row['success_criteria']) if row['success_criteria'] else [],
            'execution_count': row['execution_count'],
            'success_rate': row['success_rate'],
            'avg_execution_time_ms': row['avg_execution_time_ms']
        })

    conn.close()
    return results


# =============================================================================
# MEMORY CONSOLIDATION (Tier Promotion)
# =============================================================================

@app.tool()
async def autonomous_memory_curation() -> Dict[str, Any]:
    """
    Run autonomous memory curation across all tiers.

    Promotions:
    - Working → Episodic: High-access items become episodes
    - Episodic → Semantic: Patterns become concepts
    - Episodic → Procedural: Repeated actions become skills

    This should be run periodically to maintain memory health.

    Returns:
        Curation statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {
        'working_to_episodic': 0,
        'episodic_to_semantic': 0,
        'expired_cleaned': 0
    }

    # Clean expired working memory
    cursor.execute('DELETE FROM working_memory WHERE expires_at < ?', (datetime.now(),))
    stats['expired_cleaned'] = cursor.rowcount

    # Promote high-access working memory to episodic
    cursor.execute('''
        SELECT * FROM working_memory WHERE access_count >= 5
    ''')
    for row in cursor.fetchall():
        cursor.execute('''
            INSERT INTO episodic_memory (event_type, episode_data, significance_score)
            VALUES ('promoted_from_working', ?, ?)
        ''', (json.dumps({'content': row['content'], 'context': row['context_key']}),
              min(0.7, 0.3 + row['access_count'] * 0.1)))
        stats['working_to_episodic'] += 1

    # Promote high-significance episodic to semantic
    cursor.execute('''
        SELECT * FROM episodic_memory WHERE significance_score >= 0.8
    ''')
    for row in cursor.fetchall():
        episode_data = json.loads(row['episode_data'])
        concept_name = f"learned_{row['event_type']}_{row['id']}"

        try:
            cursor.execute('''
                INSERT INTO semantic_memory (concept_name, concept_type, definition, confidence_score)
                VALUES (?, 'derived_pattern', ?, ?)
            ''', (concept_name, json.dumps(episode_data), row['significance_score']))
            stats['episodic_to_semantic'] += 1
        except sqlite3.IntegrityError:
            pass  # Already exists

    conn.commit()
    conn.close()

    return {
        'status': 'completed',
        'promotions': stats
    }


# =============================================================================
# VERSIONING TOOLS
# =============================================================================

@app.tool()
async def memory_diff(
    entity_name: str,
    version1: Optional[int] = None,
    version2: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get diff between two versions of a memory.

    Args:
        entity_name: Name of the entity
        version1: First version number (default: current-1)
        version2: Second version number (default: current)

    Returns:
        Diff information between versions
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'error': f"Entity '{entity_name}' not found"}

    entity_id = row['id']

    # Get versions
    cursor.execute('''
        SELECT version_number, snapshot, created_at
        FROM entity_versions WHERE entity_id = ?
        ORDER BY version_number DESC
    ''', (entity_id,))

    versions = cursor.fetchall()
    conn.close()

    if len(versions) < 2:
        return {'error': 'Not enough versions for diff'}

    if version1 is None:
        version1 = versions[1]['version_number']
    if version2 is None:
        version2 = versions[0]['version_number']

    v1_data = None
    v2_data = None

    for v in versions:
        if v['version_number'] == version1:
            v1_data = json.loads(v['snapshot'])
        if v['version_number'] == version2:
            v2_data = json.loads(v['snapshot'])

    if not v1_data or not v2_data:
        return {'error': 'Version not found'}

    return {
        'entity': entity_name,
        'version1': version1,
        'version2': version2,
        'v1': v1_data,
        'v2': v2_data,
        'changes': {
            'added_observations': [o for o in v2_data.get('observations', [])
                                   if o not in v1_data.get('observations', [])],
            'removed_observations': [o for o in v1_data.get('observations', [])
                                     if o not in v2_data.get('observations', [])]
        }
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    # Run the MCP server
    logger.info("Starting Enhanced Memory MCP Server (OSS Edition)")
    app.run()
