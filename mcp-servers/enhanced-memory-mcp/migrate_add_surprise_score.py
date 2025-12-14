#!/usr/bin/env python3
"""
Migration: Add surprise_score column to memory tables

Adds surprise_score column to episodic_memory and semantic_memory tables
to support Titans/MIRAS-inspired surprise-based consolidation.
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser("~/.claude/enhanced_memories/memory.db")


def migrate():
    """Add surprise_score columns to memory tables."""

    if not os.path.exists(DB_PATH):
        logger.warning(f"Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations = []

    # Check and add surprise_score to episodic_memory
    cursor.execute("PRAGMA table_info(episodic_memory)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'surprise_score' not in columns:
        migrations.append("""
            ALTER TABLE episodic_memory
            ADD COLUMN surprise_score REAL DEFAULT 0.5
        """)
        logger.info("Will add surprise_score to episodic_memory")

    if 'content' not in columns:
        # Add content column as alias for episode_data
        migrations.append("""
            ALTER TABLE episodic_memory
            ADD COLUMN content TEXT
        """)
        logger.info("Will add content column to episodic_memory")

    if 'memory_type' not in columns:
        migrations.append("""
            ALTER TABLE episodic_memory
            ADD COLUMN memory_type TEXT DEFAULT 'episodic'
        """)
        logger.info("Will add memory_type column to episodic_memory")

    # Check and add surprise_score to semantic_memory
    cursor.execute("PRAGMA table_info(semantic_memory)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'surprise_score' not in columns:
        migrations.append("""
            ALTER TABLE semantic_memory
            ADD COLUMN surprise_score REAL DEFAULT 0.5
        """)
        logger.info("Will add surprise_score to semantic_memory")

    if 'content' not in columns:
        migrations.append("""
            ALTER TABLE semantic_memory
            ADD COLUMN content TEXT
        """)
        logger.info("Will add content column to semantic_memory")

    if 'memory_type' not in columns:
        migrations.append("""
            ALTER TABLE semantic_memory
            ADD COLUMN memory_type TEXT DEFAULT 'semantic'
        """)
        logger.info("Will add memory_type column to semantic_memory")

    if 'metadata' not in columns:
        migrations.append("""
            ALTER TABLE semantic_memory
            ADD COLUMN metadata TEXT
        """)
        logger.info("Will add metadata column to semantic_memory")

    # Execute migrations
    if migrations:
        for sql in migrations:
            try:
                cursor.execute(sql)
                logger.info(f"Executed: {sql.strip()[:60]}...")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.info(f"Column already exists, skipping")
                else:
                    logger.error(f"Migration failed: {e}")
                    raise

        conn.commit()
        logger.info(f"✅ Applied {len(migrations)} migrations")
    else:
        logger.info("✅ No migrations needed - schema is up to date")

    conn.close()
    return True


def verify_schema():
    """Verify the schema has required columns."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check episodic_memory
    cursor.execute("PRAGMA table_info(episodic_memory)")
    episodic_cols = {col[1] for col in cursor.fetchall()}

    required_episodic = {'id', 'surprise_score', 'created_at'}
    missing_episodic = required_episodic - episodic_cols

    # Check semantic_memory
    cursor.execute("PRAGMA table_info(semantic_memory)")
    semantic_cols = {col[1] for col in cursor.fetchall()}

    required_semantic = {'id', 'surprise_score', 'created_at'}
    missing_semantic = required_semantic - semantic_cols

    conn.close()

    if missing_episodic:
        logger.warning(f"Missing in episodic_memory: {missing_episodic}")
    if missing_semantic:
        logger.warning(f"Missing in semantic_memory: {missing_semantic}")

    if not missing_episodic and not missing_semantic:
        logger.info("✅ Schema verification passed")
        return True
    return False


if __name__ == "__main__":
    print("Surprise-Based Memory Consolidation Schema Migration")
    print("=" * 60)

    if migrate():
        verify_schema()
    else:
        print("Migration failed or database not found")
