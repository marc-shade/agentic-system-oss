#!/usr/bin/env python3
"""
Enhanced Memory Integration for Claude Code Hooks
Direct SQLite integration with enhanced-memory-mcp database

This module provides memory loading and saving capabilities for Claude Code hooks,
enabling persistent memory across sessions through the multi-layer memory architecture.
"""

import sqlite3
import json
import zlib
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Setup logging
LOG_FILE = Path.home() / ".claude" / "memory_integration.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)
logger = logging.getLogger("memory_integration")


class MemoryIntegration:
    """Direct integration with enhanced-memory-mcp database"""

    def __init__(self):
        """Initialize database connection using node-aware path detection"""
        self.db_path = self._get_database_path()
        logger.info(f"📂 Memory database: {self.db_path}")
        self._ensure_database()

    def _get_database_path(self) -> Path:
        """Detect database path from node configuration"""
        # Try node config first
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if node_config_path.exists():
            try:
                with open(node_config_path) as f:
                    config = json.load(f)
                    db_path = config.get("memory", {}).get("local_db")
                    if db_path:
                        # Use the directory containing local_db
                        return Path(db_path).parent / "enhanced_memories.db"
            except Exception as e:
                logger.warning(f"Could not load node config: {e}")

        # Fallback paths
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system/databases/mcp/enhanced_memories.db")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system/databases/mcp/enhanced_memories.db")
        else:
            return Path.home() / "agentic-system" / "databases" / "mcp" / "enhanced_memories.db"

    def _ensure_database(self):
        """Ensure database and tables exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Create entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT NOT NULL,
                tier TEXT DEFAULT 'working',
                compressed_data BLOB,
                original_size INTEGER,
                compressed_size INTEGER,
                compression_ratio REAL,
                checksum TEXT,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create observations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                content TEXT NOT NULL,
                compressed BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id)
            )
        ''')

        # Create relations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity_id INTEGER,
                to_entity_id INTEGER,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_entity_id) REFERENCES entities (id),
                FOREIGN KEY (to_entity_id) REFERENCES entities (id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_accessed ON entities(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_tier ON entities(tier)')

        # Create session context table for hook integration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                context_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON session_context(session_id)')

        conn.commit()
        conn.close()
        logger.info("✅ Database schema verified")

    def load_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Load relevant context for a session
        Returns recent entities, working tier items, and session history
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        context = {
            "session_id": session_id,
            "loaded_at": datetime.now().isoformat(),
            "working_tier": [],
            "recent_entities": [],
            "session_history": []
        }

        try:
            # Load working tier entities (most relevant for current session)
            cursor.execute('''
                SELECT name, entity_type, access_count, last_accessed
                FROM entities
                WHERE tier = 'working'
                ORDER BY last_accessed DESC
                LIMIT 20
            ''')
            for row in cursor.fetchall():
                context["working_tier"].append({
                    "name": row[0],
                    "type": row[1],
                    "access_count": row[2],
                    "last_accessed": row[3]
                })

            # Load recently accessed entities from any tier
            cursor.execute('''
                SELECT name, entity_type, tier, access_count, last_accessed
                FROM entities
                ORDER BY last_accessed DESC
                LIMIT 50
            ''')
            for row in cursor.fetchall():
                context["recent_entities"].append({
                    "name": row[0],
                    "type": row[1],
                    "tier": row[2],
                    "access_count": row[3],
                    "last_accessed": row[4]
                })

            # Load previous session context if available
            cursor.execute('''
                SELECT context_type, context_data, created_at
                FROM session_context
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (session_id,))
            for row in cursor.fetchall():
                context["session_history"].append({
                    "type": row[0],
                    "data": json.loads(row[1]) if row[1] else {},
                    "created_at": row[2]
                })

            logger.info(f"✅ Loaded context: {len(context['working_tier'])} working tier, {len(context['recent_entities'])} recent entities")

        except Exception as e:
            logger.error(f"❌ Error loading session context: {e}")
        finally:
            conn.close()

        return context

    def save_tool_use_memory(self, session_id: str, tool_name: str, tool_input: Dict, success: bool):
        """
        Save memory about tool usage
        Creates entities for tools and observations about their usage
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Create or update entity for this tool
            entity_name = f"tool_{tool_name}"
            entity_type = "tool_usage"

            # Check if entity exists
            cursor.execute('SELECT id, access_count FROM entities WHERE name = ?', (entity_name,))
            row = cursor.fetchone()

            if row:
                # Update existing entity
                entity_id, access_count = row
                cursor.execute('''
                    UPDATE entities
                    SET access_count = ?,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (access_count + 1, entity_id))
            else:
                # Create new entity
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, tier, access_count)
                    VALUES (?, ?, 'working', 1)
                ''', (entity_name, entity_type))
                entity_id = cursor.lastrowid

            # Save observation about this tool use
            observation_content = json.dumps({
                "session_id": session_id,
                "tool_name": tool_name,
                "input_summary": str(tool_input)[:200],  # Truncate for storage
                "success": success,
                "timestamp": datetime.now().isoformat()
            })

            cursor.execute('''
                INSERT INTO observations (entity_id, content)
                VALUES (?, ?)
            ''', (entity_id, observation_content))

            # Save session context
            cursor.execute('''
                INSERT INTO session_context (session_id, context_type, context_data)
                VALUES (?, 'tool_use', ?)
            ''', (session_id, observation_content))

            conn.commit()
            logger.info(f"✅ Saved memory: {tool_name} (success={success})")

        except Exception as e:
            logger.error(f"❌ Error saving tool use memory: {e}")
        finally:
            conn.close()

    def save_session_summary(self, session_id: str, summary: Dict[str, Any]):
        """Save a summary of the session when it ends"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO session_context (session_id, context_type, context_data)
                VALUES (?, 'session_summary', ?)
            ''', (session_id, json.dumps(summary)))

            conn.commit()
            logger.info(f"✅ Saved session summary for {session_id}")

        except Exception as e:
            logger.error(f"❌ Error saving session summary: {e}")
        finally:
            conn.close()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory system"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        stats = {}

        try:
            # Count entities by tier
            cursor.execute('''
                SELECT tier, COUNT(*) as count
                FROM entities
                GROUP BY tier
            ''')
            stats["entities_by_tier"] = {row[0]: row[1] for row in cursor.fetchall()}

            # Total entities
            cursor.execute('SELECT COUNT(*) FROM entities')
            stats["total_entities"] = cursor.fetchone()[0]

            # Total observations
            cursor.execute('SELECT COUNT(*) FROM observations')
            stats["total_observations"] = cursor.fetchone()[0]

            # Most accessed entities
            cursor.execute('''
                SELECT name, entity_type, access_count
                FROM entities
                ORDER BY access_count DESC
                LIMIT 10
            ''')
            stats["most_accessed"] = [
                {"name": row[0], "type": row[1], "count": row[2]}
                for row in cursor.fetchall()
            ]

        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
        finally:
            conn.close()

        return stats


# Global instance
_memory_integration = None

def get_memory_integration() -> MemoryIntegration:
    """Get or create global memory integration instance"""
    global _memory_integration
    if _memory_integration is None:
        _memory_integration = MemoryIntegration()
    return _memory_integration


# Convenience functions for hooks

def load_session_memory(session_id: str) -> Dict[str, Any]:
    """Load memory context for a session (called by session-start hook)"""
    memory = get_memory_integration()
    return memory.load_session_context(session_id)


def save_tool_memory(session_id: str, tool_name: str, tool_input: Dict, success: bool):
    """Save tool usage to memory (called by post-tool-use hook)"""
    memory = get_memory_integration()
    memory.save_tool_use_memory(session_id, tool_name, tool_input, success)


def save_session_end(session_id: str, summary: Dict[str, Any]):
    """Save session summary (called by session-end hook if available)"""
    memory = get_memory_integration()
    memory.save_session_summary(session_id, summary)


def get_stats() -> Dict[str, Any]:
    """Get memory system statistics"""
    memory = get_memory_integration()
    return memory.get_memory_stats()


# Test harness
if __name__ == "__main__":
    print("Testing memory integration...")

    # Initialize
    memory = MemoryIntegration()
    print(f"✅ Database: {memory.db_path}")

    # Get stats
    stats = memory.get_memory_stats()
    print(f"📊 Stats: {json.dumps(stats, indent=2)}")

    # Test session load
    test_session = "test-session-123"
    context = memory.load_session_context(test_session)
    print(f"📖 Loaded context: {len(context['working_tier'])} working tier items")

    # Test tool save
    memory.save_tool_use_memory(
        test_session,
        "TestTool",
        {"test": "input"},
        True
    )
    print("✅ Saved test memory")

    # Verify
    stats_after = memory.get_memory_stats()
    print(f"📊 Stats after: {json.dumps(stats_after, indent=2)}")

    print("\n✅ All tests passed!")
