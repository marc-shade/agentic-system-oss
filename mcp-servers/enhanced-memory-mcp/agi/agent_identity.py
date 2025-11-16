"""
Agent Identity Management Module

Provides persistent identity across sessions, enabling AGI-level continuity.

Key Features:
- Persistent agent identity with learned skills, traits, and beliefs
- Session linking for context preservation
- Cross-session learning and memory
- Identity evolution over time
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("agent-identity")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class AgentIdentity:
    """Manages persistent agent identity across sessions"""

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id
        self._ensure_identity_exists()

    def _ensure_identity_exists(self):
        """Ensure agent identity record exists"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT OR IGNORE INTO agent_identity (agent_id, created_at)
            VALUES (?, ?)
            ''',
            (self.agent_id, datetime.now().isoformat())
        )

        conn.commit()
        conn.close()

    def get_identity(self) -> Dict[str, Any]:
        """Get complete agent identity"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM agent_identity WHERE agent_id = ?',
            (self.agent_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return self._create_default_identity()

        columns = [desc[0] for desc in cursor.description]
        identity = dict(zip(columns, row))

        # Parse JSON fields
        for field in ['skill_levels', 'personality_traits', 'core_beliefs', 'preferences', 'metadata']:
            if field in identity and identity[field]:
                try:
                    identity[field] = json.loads(identity[field])
                except:
                    identity[field] = {} if field != 'core_beliefs' else []

        return identity

    def update_skills(self, skill_updates: Dict[str, float]):
        """
        Update skill levels (0.0 to 1.0)

        Example: {"coding": 0.85, "research": 0.92}
        """
        identity = self.get_identity()
        current_skills = identity.get('skill_levels', {})

        # Merge updates
        for skill, level in skill_updates.items():
            current_skills[skill] = max(0.0, min(1.0, level))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE agent_identity
            SET skill_levels = ?, last_active_at = ?
            WHERE agent_id = ?
            ''',
            (json.dumps(current_skills), datetime.now().isoformat(), self.agent_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated skills for {self.agent_id}: {skill_updates}")

    def add_belief(self, belief: str):
        """Add a core belief/knowledge to agent identity"""
        identity = self.get_identity()
        beliefs = identity.get('core_beliefs', [])

        if belief not in beliefs:
            beliefs.append(belief)

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute(
                '''
                UPDATE agent_identity
                SET core_beliefs = ?, last_active_at = ?
                WHERE agent_id = ?
                ''',
                (json.dumps(beliefs), datetime.now().isoformat(), self.agent_id)
            )

            conn.commit()
            conn.close()

            logger.info(f"Added belief for {self.agent_id}: {belief}")

    def update_personality(self, trait_updates: Dict[str, float]):
        """
        Update personality traits (0.0 to 1.0)

        Example: {"curiosity": 0.8, "caution": 0.6}
        """
        identity = self.get_identity()
        current_traits = identity.get('personality_traits', {})

        # Merge updates
        for trait, level in trait_updates.items():
            current_traits[trait] = max(0.0, min(1.0, level))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE agent_identity
            SET personality_traits = ?, last_active_at = ?
            WHERE agent_id = ?
            ''',
            (json.dumps(current_traits), datetime.now().isoformat(), self.agent_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated personality for {self.agent_id}: {trait_updates}")

    def set_preference(self, key: str, value: Any):
        """Set a preference"""
        identity = self.get_identity()
        preferences = identity.get('preferences', {})
        preferences[key] = value

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE agent_identity
            SET preferences = ?, last_active_at = ?
            WHERE agent_id = ?
            ''',
            (json.dumps(preferences), datetime.now().isoformat(), self.agent_id)
        )

        conn.commit()
        conn.close()

    def increment_counters(self, sessions=0, actions=0, memories=0):
        """Increment activity counters"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE agent_identity
            SET
                total_sessions = total_sessions + ?,
                total_actions = total_actions + ?,
                total_memories = total_memories + ?,
                last_active_at = ?
            WHERE agent_id = ?
            ''',
            (sessions, actions, memories, datetime.now().isoformat(), self.agent_id)
        )

        conn.commit()
        conn.close()

    def _create_default_identity(self) -> Dict[str, Any]:
        """Create default identity structure"""
        return {
            'agent_id': self.agent_id,
            'created_at': datetime.now().isoformat(),
            'last_active_at': datetime.now().isoformat(),
            'total_sessions': 0,
            'total_actions': 0,
            'total_memories': 0,
            'skill_levels': {},
            'personality_traits': {},
            'core_beliefs': [],
            'preferences': {},
            'last_session_summary': None,
            'metadata': {}
        }


class SessionManager:
    """Manages session continuity and linking"""

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id
        self.agent_identity = AgentIdentity(agent_id)

    def start_session(self, context_summary: Optional[str] = None) -> str:
        """
        Start a new session

        Returns:
            session_id
        """
        from uuid import uuid4

        session_id = str(uuid4())

        # Get previous session
        previous_session = self._get_last_session()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO session_continuity
            (session_id, agent_id, started_at, context_summary, previous_session_id)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                session_id,
                self.agent_id,
                datetime.now().isoformat(),
                context_summary,
                previous_session['session_id'] if previous_session else None
            )
        )

        conn.commit()
        conn.close()

        # Increment session counter
        self.agent_identity.increment_counters(sessions=1)

        logger.info(f"Started session {session_id} for {self.agent_id}")

        return session_id

    def end_session(
        self,
        session_id: str,
        key_learnings: List[str] = None,
        unfinished_work: Dict[str, Any] = None,
        performance_metrics: Dict[str, Any] = None
    ):
        """End a session and record outcomes"""
        now = datetime.now()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get session start time to calculate duration
        cursor.execute(
            'SELECT started_at FROM session_continuity WHERE session_id = ?',
            (session_id,)
        )
        row = cursor.fetchone()

        if row:
            start_time = datetime.fromisoformat(row[0])
            duration = int((now - start_time).total_seconds())
        else:
            duration = 0

        cursor.execute(
            '''
            UPDATE session_continuity
            SET
                ended_at = ?,
                duration_seconds = ?,
                key_learnings = ?,
                unfinished_work = ?,
                performance_metrics = ?
            WHERE session_id = ?
            ''',
            (
                now.isoformat(),
                duration,
                json.dumps(key_learnings or []),
                json.dumps(unfinished_work or {}),
                json.dumps(performance_metrics or {}),
                session_id
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Ended session {session_id} (duration: {duration}s)")

    def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get complete session context"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM session_continuity WHERE session_id = ?',
            (session_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session = dict(row)

        # Parse JSON fields
        for field in ['key_learnings', 'unfinished_work', 'session_type', 'performance_metrics']:
            if field in session and session[field]:
                try:
                    session[field] = json.loads(session[field])
                except:
                    pass

        return session

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM session_continuity
            WHERE agent_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            ''',
            (self.agent_id, limit)
        )

        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            session = dict(row)

            # Parse JSON fields
            for field in ['key_learnings', 'unfinished_work', 'session_type', 'performance_metrics']:
                if field in session and session[field]:
                    try:
                        session[field] = json.loads(session[field])
                    except:
                        pass

            sessions.append(session)

        return sessions

    def _get_last_session(self) -> Optional[Dict[str, Any]]:
        """Get the most recent session"""
        sessions = self.get_recent_sessions(limit=1)
        return sessions[0] if sessions else None

    def get_session_chain(self, session_id: str, depth: int = 5) -> List[Dict[str, Any]]:
        """
        Get chain of linked sessions going backwards

        Returns sessions from most recent to oldest
        """
        chain = []
        current_id = session_id

        for _ in range(depth):
            if not current_id:
                break

            session = self.get_session_context(current_id)
            if not session:
                break

            chain.append(session)
            current_id = session.get('previous_session_id')

        return chain
